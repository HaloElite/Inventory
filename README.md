# Inventory

Inventarverwaltung für Garten und Werkstatt. Flask + SQLite im Backend, Vue 3 im Frontend.
Läuft lokal auf dem Homeserver.

## Starten

```sh
# Backend  (http://127.0.0.1:5000)
cd Python
python3 -m venv myvenv && ./myvenv/bin/pip install -r requirements-dev.txt
./myvenv/bin/python -m flask init-db     # idempotent, löscht nichts
./myvenv/bin/python run.py / flask run

# Frontend (http://localhost:5173, proxied /api -> :5000)
cd Vue && npm install && npm run dev
```

Tests: `cd Python && ./myvenv/bin/python -m pytest tests`

Umgebungsvariablen: `HOST`, `PORT`, `DATABASE`, `CORS_ORIGINS`, `LOG_LEVEL`, `SECRET_KEY`, `FLASK_DEBUG`.
Auf macOS ist Port 5000 oft vom AirPlay-Receiver belegt — dann `PORT=5055`.

---

## Backend-Änderungen

**Fehlerbehandlung**

- Fehler kamen mit HTTP 200 zurück, jetzt 400 / 404 / 409 / 413. Alle Antworten sind JSON, auch 404 und 405.
- Exception-Texte landen nur noch im Log, nicht in der Antwort.

**Validierung** (`app/schemas.py`, pydantic)

- Fehlende oder nicht-numerische Felder ergaben 500, jetzt 400 mit `details`.
- `condition` wird geprüft, `category`/`condition` case-insensitiv normalisiert, Bildpfade auf relative Pfade beschränkt, Bodies auf 64 KB gedeckelt. Unbekannte Felder werden abgelehnt.

**Datenintegrität**

- Titel sind case-insensitiv eindeutig (Unique-Index), Race beim Anlegen abgefangen.
- `image` wandert in den INSERT statt in ein Nach-UPDATE über den Titel.
- `update` erlaubt keine negativen Mengen mehr und kann `condition` und `image` ändern.
- `created_at` kommt als ISO-8601 mit `Z`. Vorher UTC ohne Zonenkennung — **die Anzeige im Frontend war dadurch um den UTC-Offset verschoben** (+2 h im Sommer).
- `SELECT *` ersetzt durch feste Spalten, `ORDER BY id`, optional `?limit=&offset=`.

**Lagerorte (neu)**

- Eigene Tabelle `locations`, hierarchisch über `parent_id`: Schuppen → Regal 3 → Kiste B.
- Namen sind pro Ebene eindeutig, nicht global.
- Artikel tragen ein optionales `location_id` plus aufgelösten `location_path`.
- Zyklusschutz beim Umhängen; Löschen eines belegten Ortes gibt 409 mit Zählern.

**Betrieb**

- `init-db` ist idempotent und nicht destruktiv; das `DROP TABLE` liegt jetzt in `reset-db` mit Rückfrage.
- Schemaänderungen laufen über nummerierte Migrationen (`PRAGMA user_version`).
- CORS auf konfigurierte Origins beschränkt, Bind standardmäßig auf `127.0.0.1` (die API hat **keine Authentifizierung**).
- Logging konfiguriert, WAL + Busy-Timeout, `PRAGMA foreign_keys = ON`, kein fixes Secret im Repo.
- 75 Tests unter `Python/tests/`.

### API

| Methode | Pfad                    | Zweck                                                         |
| ------- | ----------------------- | ------------------------------------------------------------- |
| GET     | `/get-inventory`        | Artikel; `?location_id=` (inkl. Unterorte), `?limit=&offset=` |
| POST    | `/add-inventory`        | `{item, count, condition?, category?, image?, location_id?}`  |
| PUT     | `/update-item/<id>`     | `{title, count, category?, condition?, image?, location_id?}` |
| DELETE  | `/delete-item/<id>`     |                                                               |
| DELETE  | `/clear-inventory`      |                                                               |
| GET     | `/get-locations`        | alle Orte mit `path`, nach Pfad sortiert                      |
| POST    | `/add-location`         | `{name, parent_id?}`                                          |
| PUT     | `/update-location/<id>` | umbenennen und/oder umhängen                                  |
| DELETE  | `/delete-location/<id>` | nur wenn leer                                                 |

Bei `update-item` und `update-location` gilt: Feld weggelassen = unverändert, `null` = leeren.

---

## Frontend: offene Punkte

Das Frontend wurde nicht angepasst. Die API ist abwärtskompatibel — alle neuen Felder sind optional.

### Muss

- **`composables/useInventory.ts`** — nur `addItemMutation` prüft `response.ok`. `update`, `delete` und `clear` schlucken 404 und 409 stillschweigend; einziges Feedback ist `console.error`. Das fällt jetzt stärker ins Gewicht, weil das Backend diese Codes tatsächlich sendet.
- **Zeitanzeige prüfen** — durch das korrigierte `created_at` verschieben sich alle Zeitstempel um den UTC-Offset. Das ist die Korrektur, sieht aber wie eine Änderung aus.
- Aufräumen: ungenutzter `useTemplateRef`-Import und verwaistes `ref="target"` in `ModalEditItem.vue`, totes CSS `.inventory-list__row-trigger` in `InventoryList.vue:282`.

### Kann

- **Lagerorte anbinden** — komplett ungenutzt: Orte anlegen und verwalten, Artikel zuordnen, Baum als Filter. `?location_id=` schließt Unterorte ein, „was liegt im Schuppen" findet also auch den Inhalt der Kiste im Regal.
- **Zustand bearbeitbar machen** — `condition` lässt sich jetzt per `update-item` ändern, im Edit-Dialog fehlt das Bedienelement.
- **Bild-Upload** — Backend und Datenbank unterstützen `image`, das Frontend sendet es nie. Halbfertiges Feature.
- **Fehlermeldungen anzeigen** — die API liefert `{error, details:[{field, message}]}`. Aktuell wird nur eine rote Umrandung gesetzt, der Text bleibt ungenutzt.
- **Paginierung** — `?limit=&offset=` steht bereit, die Liste lädt bisher immer alles.
