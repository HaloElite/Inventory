import sqlite3
from datetime import datetime, timezone

import click
from flask import current_app, g

from app.schemas import CONDITIONS

# Einzige Quelle fuer den Bild-Default: wird sowohl im DDL als auch beim INSERT
# benutzt, damit beide nicht auseinanderlaufen.
DEFAULT_IMAGE = "static/images/ghost.svg"

# Spalten in fester Reihenfolge statt SELECT * - so aendert sich die API-Antwort
# nicht versehentlich, wenn das Schema erweitert wird.
ITEM_COLUMNS = "id, title, count, condition, category, created_at, image, location_id"

# Wartezeit, falls eine andere Verbindung gerade schreibt.
SQLITE_TIMEOUT_SECONDS = 5.0

# Trennzeichen im aufgeloesten Ortspfad ("Schuppen / Regal 3 / Kiste B").
PATH_SEPARATOR = " / "

# Baut den vollstaendigen Pfad jedes Ortes in einem Durchlauf auf, statt pro
# Zeile eine eigene Abfrage nach oben laufen zu lassen.
LOCATION_TREE_CTE = f"""
WITH RECURSIVE tree(id, name, parent_id, created_at, path) AS (
    SELECT id, name, parent_id, created_at, name
      FROM locations
     WHERE parent_id IS NULL
    UNION ALL
    SELECT l.id, l.name, l.parent_id, l.created_at, t.path || '{PATH_SEPARATOR}' || l.name
      FROM locations l
      JOIN tree t ON l.parent_id = t.id
)
"""

LOCATION_TREE_SQL = f"{LOCATION_TREE_CTE} SELECT id, name, parent_id, created_at, path FROM tree"

# Artikel samt aufgeloestem Ortspfad. LEFT JOIN, weil ein Artikel keinen Ort
# haben muss - location_path ist dann NULL.
_ITEM_SELECT = ", ".join(f"i.{column}" for column in ITEM_COLUMNS.split(", "))

ITEM_QUERY_SQL = f"""
{LOCATION_TREE_CTE}
SELECT {_ITEM_SELECT}, t.path AS location_path
  FROM inventory i
  LEFT JOIN tree t ON t.id = i.location_id
"""

_CONDITION_LIST = ", ".join(f"'{condition}'" for condition in CONDITIONS)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0 CHECK(count >= 0),
    condition TEXT NOT NULL CHECK(condition IN ({_CONDITION_LIST})) DEFAULT 'new',
    category TEXT NOT NULL DEFAULT 'general',
    -- Explizit UTC mit Zonenkennung: CURRENT_TIMESTAMP liefert zwar UTC, aber
    -- ohne 'Z' - JavaScript interpretiert das dann faelschlich als Ortszeit.
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    image TEXT DEFAULT '{DEFAULT_IMAGE}'
);

-- Erzwingt Eindeutigkeit der Titel unabhaengig von Gross-/Kleinschreibung.
-- Laesst sich auch auf eine bereits bestehende Tabelle nachziehen.
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_title_nocase
    ON inventory (title COLLATE NOCASE);
"""

# ---------------------------------------------------------------------------
#   Migrationen
# ---------------------------------------------------------------------------
# CREATE TABLE IF NOT EXISTS kann einer bereits bestehenden Tabelle keine Spalte
# hinzufuegen. Schemaaenderungen laufen deshalb ueber diese nummerierte Liste:
# PRAGMA user_version haelt fest, wie viele Schritte bereits gelaufen sind, so
# dass jeder Schritt genau einmal ausgefuehrt wird.
MIGRATIONS = [
    # 1 - Lagerorte als eigene, hierarchische Tabelle.
    """
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER REFERENCES locations(id),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );

    -- Namen sind pro Ebene eindeutig, nicht global: zwei "Kiste B" in
    -- verschiedenen Regalen sind erlaubt, zwei im selben nicht. COALESCE ist
    -- noetig, weil SQLite NULL-Werte in Unique-Indizes als verschieden
    -- behandelt - sonst waeren beliebig viele Wurzeln gleichen Namens moeglich.
    CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_parent_name_nocase
        ON locations (COALESCE(parent_id, 0), name COLLATE NOCASE);
    """,
    # 2 - Artikel koennen einem Lagerort zugeordnet werden (optional).
    """
    ALTER TABLE inventory ADD COLUMN location_id INTEGER REFERENCES locations(id);

    CREATE INDEX IF NOT EXISTS idx_inventory_location
        ON inventory (location_id);
    """,
]


def run_migrations():
    """Offene Migrationsschritte der Reihe nach ausfuehren."""
    db = get_db()
    applied = db.execute("PRAGMA user_version").fetchone()[0]

    for version, statements in enumerate(MIGRATIONS[applied:], start=applied + 1):
        db.executescript(statements)
        # PRAGMA erlaubt keine Parameterbindung; version stammt aus enumerate.
        db.execute(f"PRAGMA user_version = {version}")
        db.commit()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=SQLITE_TIMEOUT_SECONDS)
        g.db.row_factory = sqlite3.Row
        # WAL erlaubt parallele Leser waehrend eines Schreibvorgangs.
        g.db.execute("PRAGMA journal_mode = WAL")
        # SQLite ignoriert Fremdschluessel sonst stillschweigend - und zwar
        # pro Verbindung, nicht pro Datenbank.
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    if e:
        current_app.logger.warning("App context torn down with exception: %s", e)
    db = g.pop("db", None)

    if db is not None:
        db.close()


def to_iso_utc(value):
    """created_at als ISO-8601 mit 'Z' ausliefern.

    Alte Zeilen stehen im Format 'YYYY-MM-DD HH:MM:SS' (UTC, aber ohne Zonen-
    kennung). Ohne 'Z' parst JavaScript den Wert als Ortszeit - dadurch war die
    Anzeige im Frontend um den UTC-Offset verschoben.
    """
    if not isinstance(value, str):
        return value

    text = value.strip()

    if text.endswith("Z") or "+" in text:
        return text

    try:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return text  # unbekanntes Format unveraendert durchreichen

    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def serialise_item(row):
    item = dict(row)
    item["created_at"] = to_iso_utc(item["created_at"])
    return item


def ensure_schema():
    """Legt Tabelle und Index an, falls sie fehlen. Idempotent, loescht nichts."""
    db = get_db()
    try:
        db.executescript(SCHEMA)
    except sqlite3.IntegrityError as exc:
        # Tritt auf, wenn eine bestehende DB bereits doppelte Titel enthaelt.
        db.rollback()
        raise RuntimeError(
            "Unique index on 'title' could not be created - the database contains "
            "duplicate titles (case-insensitive). Resolve them and retry."
        ) from exc
    db.commit()
    run_migrations()


def drop_schema():
    db = get_db()
    db.executescript("DROP TABLE IF EXISTS inventory;")
    db.commit()


@click.command("init-db")
def init_db_command():
    """Schema anlegen bzw. fehlende Indizes nachziehen (nicht destruktiv)."""
    ensure_schema()
    click.echo("Schema is up to date.")


@click.command("reset-db")
@click.confirmation_option(prompt="This deletes ALL inventory data. Continue?")
def reset_db_command():
    """Tabelle verwerfen und leer neu anlegen (destruktiv)."""
    drop_schema()
    ensure_schema()
    click.echo("Database was reset.")
