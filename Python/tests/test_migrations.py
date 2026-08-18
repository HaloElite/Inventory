"""Tests fuer die Schema-Migration.

Hintergrund: Die App lief gegen eine Datenbank, die hinter dem Code lag, und
antwortete auf jeden Zugriff mit 500 ("no such column: i.location_id"). Sie
verliess sich darauf, dass jemand nach einem Update `flask init-db` aufruft.
"""

import sqlite3

import pytest

from app import app as flask_app
from app.db import MIGRATIONS

# Datenbank so, wie sie vor den Lagerorten aussah.
LEGACY_SCHEMA = """
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    condition TEXT NOT NULL DEFAULT 'new',
    category TEXT NOT NULL DEFAULT 'general',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    image TEXT DEFAULT 'static/images/ghost.svg'
);
INSERT INTO inventory (title, count) VALUES ('Spaten', 1);
"""

# Zustand, in dem Migration 1 lief und Migration 2 nicht.
HALF_MIGRATED_SCHEMA = (
    LEGACY_SCHEMA
    + """
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES locations(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE UNIQUE INDEX idx_locations_parent_name_nocase
    ON locations (COALESCE(parent_id, 0), name COLLATE NOCASE);
PRAGMA user_version = 1;
"""
)


def _build(path, script):
    connection = sqlite3.connect(path)
    connection.executescript(script)
    connection.commit()
    connection.close()
    return str(path)


@pytest.fixture()
def client_for(tmp_path):
    """Test-Client auf einer Datenbank, die bewusst NICHT vormigriert wurde."""

    def _client_for(script=None, name="db.sqlite"):
        path = tmp_path / name
        if script is not None:
            _build(path, script)
        flask_app.config.update(TESTING=True, DATABASE=str(path), PROPAGATE_EXCEPTIONS=False)
        return flask_app.test_client()

    return _client_for


def _columns(path, table):
    connection = sqlite3.connect(path)
    try:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
    finally:
        connection.close()


def _user_version(path):
    connection = sqlite3.connect(path)
    try:
        return connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()


# ---------------------------------------------------------------------------
#   Der gemeldete Fehler
# ---------------------------------------------------------------------------
def test_serves_database_stuck_between_migrations(client_for):
    """Genau der gemeldete Zustand: locations da, location_id fehlt."""
    client = client_for(HALF_MIGRATED_SCHEMA)

    response = client.get("/get-inventory")

    assert response.status_code == 200
    assert response.get_json()[0]["title"] == "Spaten"
    assert response.get_json()[0]["location_id"] is None


def test_serves_database_from_before_locations(client_for):
    client = client_for(LEGACY_SCHEMA)

    response = client.get("/get-inventory")

    assert response.status_code == 200
    assert response.get_json()[0]["title"] == "Spaten"


def test_serves_empty_database_without_manual_init(client_for):
    """Eine frische Installation soll ohne `flask init-db` laufen."""
    client = client_for()

    assert client.get("/get-inventory").status_code == 200
    assert client.get("/get-locations").status_code == 200


def test_existing_rows_survive_the_migration(client_for, tmp_path):
    client = client_for(LEGACY_SCHEMA)
    client.get("/get-inventory")

    path = str(tmp_path / "db.sqlite")
    assert _user_version(path) == len(MIGRATIONS)
    assert "location_id" in _columns(path, "inventory")

    connection = sqlite3.connect(path)
    assert connection.execute("SELECT title, count FROM inventory").fetchall() == [("Spaten", 1)]
    connection.close()


def test_migration_runs_only_once(client_for, tmp_path):
    client = client_for(LEGACY_SCHEMA)

    for _ in range(3):
        assert client.get("/get-inventory").status_code == 200

    assert _user_version(str(tmp_path / "db.sqlite")) == len(MIGRATIONS)


def test_write_endpoints_work_on_a_stale_database(client_for):
    client = client_for(HALF_MIGRATED_SCHEMA)

    shed = client.post("/add-location", json={"name": "Schuppen"})
    assert shed.status_code == 201

    created = client.post("/add-inventory", json={"item": "Harke", "count": 2, "location_id": shed.get_json()["id"]})
    assert created.status_code == 201
    assert created.get_json()["location_path"] == "Schuppen"


# ---------------------------------------------------------------------------
#   Selbstheilung: eine halb angewandte Migration darf nicht blockieren
# ---------------------------------------------------------------------------
def test_recovers_when_column_exists_but_version_lags(client_for):
    """ALTER TABLE ADD COLUMN ist nicht idempotent - ein Abbruch zwischen DDL
    und Versionsstempel darf die Datenbank nicht dauerhaft unbrauchbar machen."""
    script = HALF_MIGRATED_SCHEMA + "ALTER TABLE inventory ADD COLUMN location_id INTEGER REFERENCES locations(id);"
    client = client_for(script)

    assert client.get("/get-inventory").status_code == 200


# ---------------------------------------------------------------------------
#   reset-db: ohne Zuruecksetzen des Versionsstempels bleibt die neu angelegte
#   Tabelle unvollstaendig, weil die Migrationen nicht erneut laufen.
# ---------------------------------------------------------------------------
def test_reset_leaves_a_complete_schema(client_for, tmp_path):
    from app.db import drop_schema, ensure_schema, get_db

    client = client_for(LEGACY_SCHEMA)
    assert client.get("/get-inventory").status_code == 200

    with flask_app.app_context():
        db = get_db()
        drop_schema(db)
        ensure_schema(db)

    path = str(tmp_path / "db.sqlite")
    assert _user_version(path) == len(MIGRATIONS)
    assert "location_id" in _columns(path, "inventory")

    assert client.get("/get-inventory").get_json() == []
    assert client.post("/add-inventory", json={"item": "Spaten", "count": 1}).status_code == 201
