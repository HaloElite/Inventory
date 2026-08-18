# Inventory

Inventarverwaltung für Garten und Werkstatt. Flask + SQLite im Backend, Vue 3 im Frontend.
Läuft lokal auf dem Homeserver.

```
Vue (5173) ──/api/*──▶ Vite-Proxy ──▶ Flask (5000) ──▶ SQLite
                       strippt /api                    instance/todos.db
```

## Starten

```sh
# Backend  (http://127.0.0.1:5000)
cd Python
python3 -m venv myvenv && ./myvenv/bin/pip install -r requirements-dev.txt
./myvenv/bin/python run.py    # oder: flask run

# Frontend (http://localhost:5173)
cd Vue && npm install && npm run dev
```

Das Schema wird beim ersten Datenbankzugriff automatisch angelegt und migriert — nach einem
`git pull` ist kein Handgriff nötig. Tests: `cd Python && ./myvenv/bin/python -m pytest tests`

| Variable       | Default                            | Zweck                                                                                           |
| -------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------- |
| `HOST`         | `127.0.0.1`                        | Bind-Adresse. Die API hat **keine Authentifizierung** — `0.0.0.0` gibt sie ins ganze Netz frei. |
| `PORT`         | `5000`                             | Auf macOS oft vom AirPlay-Receiver belegt.                                                      |
| `DATABASE`     | `instance/todos.db`                | Pfad zur SQLite-Datei.                                                                          |
| `CORS_ORIGINS` | `localhost:5173`, `127.0.0.1:5173` | Kommaseparierte Liste erlaubter Origins.                                                        |
| `LOG_LEVEL`    | `INFO`                             |                                                                                                 |
| `SECRET_KEY`   | zufällig pro Prozess               |                                                                                                 |
| `FLASK_DEBUG`  | aus                                |                                                                                                 |

---

# API

Alle Endpunkte sprechen JSON. Im Dev-Betrieb ruft das Frontend sie unter `/api/…` auf; der
Vite-Proxy entfernt das Präfix, das Backend selbst kennt es nicht.

## Konventionen

**Eingaben werden normalisiert.** Strings werden getrimmt, `condition` und `category` in
Kleinschreibung überführt. `"  Tools "` wird zu `"tools"`, `"USED"` zu `"used"`.

**Unbekannte Felder sind ein Fehler**, kein stilles Ignorieren — ein Tippfehler im Feldnamen
liefert 400 statt einer Änderung, die nicht stattfindet.

**Zahlen als String sind erlaubt.** `"count": "250"` wird zu `250`. `"count": "viele"` ist 400.

**Bei PUT gilt für optionale Felder:**

| im Body         | Wirkung                |
| --------------- | ---------------------- |
| Feld fehlt      | bisheriger Wert bleibt |
| Feld ist `null` | Wert wird geleert      |
| Feld hat Wert   | Wert wird gesetzt      |

Das betrifft `condition`, `image` und `location_id` bei Artikeln sowie `parent_id` bei Orten.

## Objekte

**Artikel** — so kommt er aus jedem Artikel-Endpunkt zurück:

```json
{
  "id": 2,
  "title": "Schrauben M4",
  "count": 250,
  "condition": "used",
  "category": "befestigungsmaterial",
  "created_at": "2026-08-18T18:08:58Z",
  "image": "static/images/schrauben.svg",
  "location_id": 3,
  "location_path": "Schuppen / Regal A / Kiste B"
}
```

`created_at` ist ISO-8601 in UTC. `location_id` und `location_path` sind `null`, wenn kein Ort
zugeordnet ist. `location_path` wird serverseitig aufgelöst und ist nur lesbar.

**Ort:**

```json
{
  "id": 3,
  "name": "Kiste B",
  "parent_id": 2,
  "created_at": "2026-08-18T18:08:58Z",
  "path": "Schuppen / Regal A / Kiste B"
}
```

`parent_id` ist `null` bei Orten auf oberster Ebene. `path` ist abgeleitet und nur lesbar.

---

## Artikel

### `GET /get-inventory`

Liefert alle Artikel als Array, aufsteigend nach `id`.

| Query         | Pflicht | Bedeutung                                                     |
| ------------- | ------- | ------------------------------------------------------------- |
| `location_id` | nein    | Nur Artikel an diesem Ort **einschließlich aller Unterorte**. |
| `limit`       | nein    | 1–500. Ohne Angabe wird alles geliefert.                      |
| `offset`      | nein    | ≥ 0, nur zusammen mit `limit` sinnvoll.                       |

```sh
curl 'localhost:5000/get-inventory?location_id=1'
```

`location_id=1` („Schuppen") findet auch, was in einer Kiste in einem Regal darin liegt — das ist
der eigentliche Zweck der Ortshierarchie.

**200** → Array von Artikel-Objekten (leeres Array, wenn nichts passt)
**400** → `location_id`, `limit` oder `offset` nicht ganzzahlig bzw. außerhalb des Bereichs
**404** → `location_id` verweist auf einen Ort, den es nicht gibt

---

### `POST /add-inventory`

Legt einen Artikel an. Titel sind case-insensitiv eindeutig.

| Feld          | Typ    | Pflicht | Default                   | Regeln                                                                      |
| ------------- | ------ | ------- | ------------------------- | --------------------------------------------------------------------------- |
| `item`        | string | **ja**  | —                         | 1–120 Zeichen nach Trimmen                                                  |
| `count`       | int    | **ja**  | —                         | 1 – 1 000 000                                                               |
| `condition`   | string | nein    | `"new"`                   | `new`, `used` oder `damaged`                                                |
| `category`    | string | nein    | `"general"`               | 1–60 Zeichen                                                                |
| `image`       | string | nein    | `static/images/ghost.svg` | relativer Pfad, max. 255 Zeichen, kein `://`, kein führender `/`, kein `..` |
| `location_id` | int    | nein    | `null`                    | muss existieren                                                             |

```sh
curl -X POST localhost:5000/add-inventory -H 'Content-Type: application/json' \
  -d '{"item":"Schrauben M4","count":250,"category":"fasteners","location_id":3}'
```

**201** → das angelegte Artikel-Objekt (inklusive vergebener `id`)
**400** → Validierungsfehler, mit `details` je betroffenem Feld
**404** → `location_id` existiert nicht
**409** → Titel gibt es bereits (`"Item already exists"`)
**413** → Body größer als 64 KB

---

### `PUT /update-item/<id>`

Ändert einen Artikel. `title` und `count` sind immer anzugeben, der Rest folgt der
Keep-vs-Clear-Regel oben.

| Feld          | Typ    | Pflicht | Regeln                                                                  |
| ------------- | ------ | ------- | ----------------------------------------------------------------------- |
| `title`       | string | **ja**  | 1–120 Zeichen, case-insensitiv eindeutig                                |
| `count`       | int    | **ja**  | **0** – 1 000 000 — anders als beim Anlegen ist 0 erlaubt (ausverkauft) |
| `category`    | string | nein    | 1–60 Zeichen                                                            |
| `condition`   | string | nein    | `new`, `used`, `damaged`                                                |
| `image`       | string | nein    | wie beim Anlegen; `null` setzt zurück                                   |
| `location_id` | int    | nein    | muss existieren; `null` entfernt die Zuordnung                          |

```sh
curl -X PUT localhost:5000/update-item/1 -H 'Content-Type: application/json' \
  -d '{"title":"Spaten","count":0,"condition":"damaged","location_id":2}'
```

**200** → das aktualisierte Artikel-Objekt
**400** → Validierungsfehler · **404** → Artikel oder Ort nicht gefunden · **409** → Titel bereits vergeben

---

### `DELETE /delete-item/<id>`

Löscht einen Artikel. **200** → `{"deleted": 1}` · **404** → `{"error": "Item not found"}`

### `DELETE /clear-inventory`

Löscht **alle** Artikel. Orte bleiben bestehen. Keine Rückfrage, keine Authentifizierung.

**200** → `{"deleted": 12}` (Anzahl der entfernten Zeilen)

---

## Lagerorte

Orte bilden einen Baum: `Schuppen → Regal 3 → Kiste B`. Namen sind **pro Ebene** eindeutig, nicht
global — zwei „Kiste B" in verschiedenen Regalen sind zulässig.

### `GET /get-locations`

Alle Orte als flaches Array, sortiert nach `path` (dadurch in Baumreihenfolge). Die Hierarchie
steckt in `parent_id`, den lesbaren Pfad liefert `path` gleich mit.

**200** → Array von Ort-Objekten

### `POST /add-location`

| Feld        | Typ    | Pflicht | Default | Regeln                                  |
| ----------- | ------ | ------- | ------- | --------------------------------------- |
| `name`      | string | **ja**  | —       | 1–80 Zeichen nach Trimmen               |
| `parent_id` | int    | nein    | `null`  | muss existieren; `null` = oberste Ebene |

```sh
curl -X POST localhost:5000/add-location -H 'Content-Type: application/json' \
  -d '{"name":"Regal 3","parent_id":1}'
```

**201** → das angelegte Ort-Objekt
**400** → Validierungsfehler · **404** → `{"error": "Parent location not found"}`
**409** → `{"error": "Location already exists at this level"}`

### `PUT /update-location/<id>`

Benennt um und/oder hängt um. Ein Umhängen verschiebt den gesamten Teilbaum samt Inhalt; alle
`path`-Werte darunter ändern sich sofort mit.

| Feld        | Typ    | Pflicht | Regeln                                                                   |
| ----------- | ------ | ------- | ------------------------------------------------------------------------ |
| `name`      | string | **ja**  | 1–80 Zeichen                                                             |
| `parent_id` | int    | nein    | fehlt = bleibt · `null` = auf oberste Ebene · Wert = dorthin verschieben |

**200** → das aktualisierte Ort-Objekt
**404** → Ort oder neues Elternteil nicht gefunden
**409** → Name auf dieser Ebene vergeben, **oder** `{"error": "A location cannot be moved into its own subtree"}`

Der Teilbaum-Schutz verhindert Zyklen: ohne ihn könnte „Schuppen" zum Kind seiner eigenen Kiste
werden und die rekursive Pfadauflösung liefe endlos.

### `DELETE /delete-location/<id>`

Löscht einen Ort, aber nur wenn er leer ist — weder Unterorte noch Artikel. Andernfalls 409 mit
Zählern, statt Artikel still verwaisen zu lassen.

**200** → `{"deleted": 1}`
**404** → `{"error": "Location not found"}`
**409** →

```json
{ "error": "Location is not empty", "child_locations": 1, "items": 0 }
```

---

## Fehler

Jeder Fehler ist JSON, auch 404 und 405.

```json
{ "error": "Item already exists" }
```

Validierungsfehler führen zusätzlich `details`:

```json
{
  "error": "Invalid input",
  "details": [
    { "field": "item", "message": "String should have at least 1 character" },
    {
      "field": "count",
      "message": "Input should be a valid integer, unable to parse string as an integer"
    },
    {
      "field": "condition",
      "message": "Input should be 'new', 'used' or 'damaged'"
    }
  ]
}
```

| Status | Bedeutung                                                                                       |
| ------ | ----------------------------------------------------------------------------------------------- |
| 400    | Body kein JSON-Objekt, Validierung fehlgeschlagen, Query-Parameter ungültig                     |
| 404    | Artikel, Ort oder Route nicht gefunden                                                          |
| 405    | Methode für diesen Pfad nicht erlaubt                                                           |
| 409    | Konflikt: Titel/Ortsname vergeben, Ort nicht leer, Zyklus im Ortsbaum                           |
| 413    | Body größer als 64 KB                                                                           |
| 500    | Unerwarteter Fehler. Nach außen immer `{"error": "Internal server error"}`, Details nur im Log. |

---

# Backend-Änderungen

**Fehlerbehandlung** — Fehler kamen mit HTTP 200 zurück, jetzt 400/404/409/413. Alle Antworten sind
JSON. Exception-Texte landen nur noch im Log.

**Validierung** (`app/schemas.py`, pydantic) — fehlende oder nicht-numerische Felder ergaben 500,
jetzt 400 mit `details`. `condition` wird geprüft, Bildpfade beschränkt, Bodies gedeckelt,
unbekannte Felder abgelehnt.

**Datenintegrität**

- Titel case-insensitiv eindeutig (Unique-Index), Race beim Anlegen abgefangen.
- `image` wandert in den INSERT statt in ein Nach-UPDATE über den Titel.
- `update` erlaubt keine negativen Mengen mehr und kann `condition` und `image` ändern.
- `created_at` kommt als ISO-8601 mit `Z`. Vorher UTC ohne Zonenkennung — **die Anzeige im Frontend
  war dadurch um den UTC-Offset verschoben** (+2 h im Sommer).
- `SELECT *` ersetzt durch feste Spalten, `ORDER BY id`, optional `?limit=&offset=`.

**Lagerorte** — neue Tabelle `locations`, hierarchisch über `parent_id`; Namen pro Ebene eindeutig;
Artikel tragen optionales `location_id` plus aufgelösten `location_path`; Zyklusschutz beim
Umhängen; Löschen eines belegten Ortes gibt 409.

**Betrieb**

- Schemaänderungen laufen über nummerierte Migrationen (`PRAGMA user_version`) und werden **beim
  Verbindungsaufbau automatisch angewandt**. Schritt und Versionsstempel liegen in einer
  Transaktion, ein Abbruch hinterlässt keinen Zwischenstand. Jeder Schritt ist wiederholbar.
- `flask init-db` zieht dasselbe von Hand nach, `flask reset-db` leert die Datenbank nach Rückfrage.
- CORS auf konfigurierte Origins beschränkt, Bind standardmäßig auf `127.0.0.1`.
- Logging konfiguriert, WAL + Busy-Timeout, `PRAGMA foreign_keys = ON`, kein fixes Secret im Repo.
- 83 Tests unter `Python/tests/`.

# Frontend: offene Punkte

Das Frontend wurde nicht angepasst. Die API ist abwärtskompatibel — alle neuen Felder sind optional.

## Muss

- **`composables/useInventory.ts`** — nur `addItemMutation` prüft `response.ok`. `update`, `delete`
  und `clear` schlucken 404 und 409 stillschweigend; einziges Feedback ist `console.error`. Das
  fällt jetzt stärker ins Gewicht, weil das Backend diese Codes tatsächlich sendet.
- **Zeitanzeige prüfen** — durch das korrigierte `created_at` verschieben sich alle Zeitstempel um
  den UTC-Offset. Das ist die Korrektur, sieht aber wie eine Änderung aus.
- Aufräumen: ungenutzter `useTemplateRef`-Import und verwaistes `ref="target"` in
  `ModalEditItem.vue`, totes CSS `.inventory-list__row-trigger` in `InventoryList.vue:282`.

## Kann

- **Lagerorte anbinden** — komplett ungenutzt: Orte anlegen und verwalten, Artikel zuordnen, Baum
  als Filter.
- **Zustand bearbeitbar machen** — `condition` lässt sich per `update-item` ändern, im Edit-Dialog
  fehlt das Bedienelement.
- **Bild-Upload** — Backend und Datenbank unterstützen `image`, das Frontend sendet es nie.
- **Fehlermeldungen anzeigen** — die API liefert `details` je Feld, genutzt wird nur eine rote
  Umrandung.
- **Paginierung** — `?limit=&offset=` steht bereit, die Liste lädt bisher immer alles.
