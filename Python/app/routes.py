import sqlite3

from flask import current_app, jsonify, request

from app import app
from app.db import DEFAULT_IMAGE, ITEM_QUERY_SQL, LOCATION_TREE_SQL, get_db, serialise_item
from app.errors import ApiError
from app.schemas import ItemCreate, ItemUpdate, LocationCreate, LocationUpdate, format_validation_errors
from pydantic import ValidationError


# ---------------------------------------------------------------------------
#   Helfer
# ---------------------------------------------------------------------------
def _parse_body(model):
    """JSON-Body einlesen und gegen das pydantic-Modell validieren."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)

    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ApiError("Invalid input", 400, details=format_validation_errors(exc)) from exc


def _pagination_args():
    """Optionale ?limit=&offset= Parameter lesen. Ohne limit wird alles geliefert."""
    raw_limit = request.args.get("limit")
    raw_offset = request.args.get("offset", "0")

    if raw_limit is None:
        return None, 0

    try:
        limit = int(raw_limit)
        offset = int(raw_offset)
    except ValueError as exc:
        raise ApiError("'limit' and 'offset' must be integers", 400) from exc

    max_page_size = current_app.config["MAX_PAGE_SIZE"]

    if not 1 <= limit <= max_page_size:
        raise ApiError(f"'limit' must be between 1 and {max_page_size}", 400)
    if offset < 0:
        raise ApiError("'offset' must not be negative", 400)

    return limit, offset


def _fetch_item(db, item_id):
    return db.execute(f"{ITEM_QUERY_SQL} WHERE i.id = ?", (item_id,)).fetchone()


def _require_location(db, location_id):
    if location_id is not None and _fetch_location(db, location_id) is None:
        raise ApiError("Location not found", 404)


def _subtree_ids(db, root_id):
    """Alle Orts-IDs auf und unterhalb von root_id."""
    rows = db.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM locations WHERE id = ?
            UNION ALL
            SELECT l.id FROM locations l JOIN subtree s ON l.parent_id = s.id
        )
        SELECT id FROM subtree
        """,
        (root_id,),
    ).fetchall()

    return [row["id"] for row in rows]


def _find_title_conflict(db, title, exclude_id=None):
    """Titel-Duplikat case-insensitiv suchen (Fallback fuer DBs ohne Unique-Index)."""
    if exclude_id is None:
        sql = "SELECT id FROM inventory WHERE title = ? COLLATE NOCASE"
        params = (title,)
    else:
        sql = "SELECT id FROM inventory WHERE title = ? COLLATE NOCASE AND id != ?"
        params = (title, exclude_id)

    return db.execute(sql, params).fetchone()


# ---------------------------------------------------------------------------
#   Routen
# ---------------------------------------------------------------------------
@app.route("/get-inventory")
def get_items():
    db = get_db()
    limit, offset = _pagination_args()

    sql = ITEM_QUERY_SQL
    params = ()

    raw_location = request.args.get("location_id")

    if raw_location is not None:
        try:
            location_id = int(raw_location)
        except ValueError as exc:
            raise ApiError("'location_id' must be an integer", 400) from exc

        _require_location(db, location_id)

        # Unterorte einschliessen: "was liegt im Schuppen" findet auch, was in
        # einer Kiste in einem Regal darin liegt.
        subtree = _subtree_ids(db, location_id)
        sql += f" WHERE i.location_id IN ({', '.join('?' * len(subtree))})"
        params += tuple(subtree)

    sql += " ORDER BY i.id"

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += (limit, offset)

    items = db.execute(sql, params).fetchall()

    return jsonify([serialise_item(row) for row in items]), 200


@app.route("/add-inventory", methods=["POST"])
def add_item():
    payload = _parse_body(ItemCreate)
    db = get_db()

    if _find_title_conflict(db, payload.item) is not None:
        raise ApiError("Item already exists", 409)

    _require_location(db, payload.location_id)

    try:
        cursor = db.execute(
            "INSERT INTO inventory (title, count, condition, category, image, location_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                payload.item,
                payload.count,
                payload.condition,
                payload.category,
                payload.image or DEFAULT_IMAGE,
                payload.location_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        # Faengt den Race zwischen Pruefung und INSERT ab.
        db.rollback()
        raise ApiError("Item already exists", 409) from exc

    return jsonify(serialise_item(_fetch_item(db, cursor.lastrowid))), 201


@app.route("/update-item/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    payload = _parse_body(ItemUpdate)
    db = get_db()

    existing = _fetch_item(db, item_id)

    if existing is None:
        raise ApiError("Item not found", 404)

    if _find_title_conflict(db, payload.title, exclude_id=item_id) is not None:
        raise ApiError("Item already exists", 409)

    # Nicht mitgeschickte Felder behalten ihren bisherigen Wert.
    condition = payload.condition or existing["condition"]
    image = payload.image if payload.image is not None else existing["image"]

    # Weggelassen laesst den Ort stehen, explizites null entfernt ihn.
    if "location_id" in payload.model_fields_set:
        location_id = payload.location_id
    else:
        location_id = existing["location_id"]

    _require_location(db, location_id)

    try:
        db.execute(
            "UPDATE inventory SET title = ?, count = ?, category = ?, condition = ?, image = ?, location_id = ? "
            "WHERE id = ?",
            (payload.title, payload.count, payload.category, condition, image, location_id, item_id),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise ApiError("Item already exists", 409) from exc

    return jsonify(serialise_item(_fetch_item(db, item_id))), 200


@app.route("/delete-item/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    db = get_db()

    cursor = db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    db.commit()

    if cursor.rowcount == 0:
        raise ApiError("Item not found", 404)

    return jsonify({"deleted": item_id}), 200


# ---------------------------------------------------------------------------
#   Lagerorte
# ---------------------------------------------------------------------------
def _fetch_location(db, location_id):
    return db.execute(f"{LOCATION_TREE_SQL} WHERE id = ?", (location_id,)).fetchone()


def _require_parent(db, parent_id):
    if parent_id is not None and _fetch_location(db, parent_id) is None:
        raise ApiError("Parent location not found", 404)


def _is_in_subtree(db, root_id, candidate_id):
    """Liegt candidate_id auf oder unterhalb von root_id?

    Verhindert Zyklen beim Umhaengen - ohne diese Pruefung koennte ein Ort zum
    Kind seiner eigenen Kiste werden und die rekursiven Abfragen liefen endlos.
    """
    row = db.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM locations WHERE id = ?
            UNION ALL
            SELECT l.id FROM locations l JOIN subtree s ON l.parent_id = s.id
        )
        SELECT 1 FROM subtree WHERE id = ?
        """,
        (root_id, candidate_id),
    ).fetchone()

    return row is not None


@app.route("/get-locations")
def get_locations():
    db = get_db()

    rows = db.execute(f"{LOCATION_TREE_SQL} ORDER BY path").fetchall()

    return jsonify([dict(row) for row in rows]), 200


@app.route("/add-location", methods=["POST"])
def add_location():
    payload = _parse_body(LocationCreate)
    db = get_db()

    _require_parent(db, payload.parent_id)

    try:
        cursor = db.execute(
            "INSERT INTO locations (name, parent_id) VALUES (?, ?)",
            (payload.name, payload.parent_id),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise ApiError("Location already exists at this level", 409) from exc

    return jsonify(dict(_fetch_location(db, cursor.lastrowid))), 201


@app.route("/update-location/<int:location_id>", methods=["PUT"])
def update_location(location_id):
    payload = _parse_body(LocationUpdate)
    db = get_db()

    existing = _fetch_location(db, location_id)

    if existing is None:
        raise ApiError("Location not found", 404)

    # Weggelassenes parent_id laesst den Ort stehen, explizites null hebt ihn
    # auf die oberste Ebene.
    if "parent_id" in payload.model_fields_set:
        new_parent_id = payload.parent_id
    else:
        new_parent_id = existing["parent_id"]

    _require_parent(db, new_parent_id)

    if new_parent_id is not None and _is_in_subtree(db, location_id, new_parent_id):
        raise ApiError("A location cannot be moved into its own subtree", 409)

    try:
        db.execute(
            "UPDATE locations SET name = ?, parent_id = ? WHERE id = ?",
            (payload.name, new_parent_id, location_id),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise ApiError("Location already exists at this level", 409) from exc

    return jsonify(dict(_fetch_location(db, location_id))), 200


@app.route("/delete-location/<int:location_id>", methods=["DELETE"])
def delete_location(location_id):
    db = get_db()

    if _fetch_location(db, location_id) is None:
        raise ApiError("Location not found", 404)

    children = db.execute("SELECT COUNT(*) FROM locations WHERE parent_id = ?", (location_id,)).fetchone()[0]
    items = db.execute("SELECT COUNT(*) FROM inventory WHERE location_id = ?", (location_id,)).fetchone()[0]

    if children or items:
        # Lieber blockieren als Artikel still verwaisen lassen.
        raise ApiError(
            "Location is not empty",
            409,
            extra={"child_locations": children, "items": items},
        )

    db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    db.commit()

    return jsonify({"deleted": location_id}), 200


@app.route("/clear-inventory", methods=["DELETE"])
def clear_inventory():
    db = get_db()

    cursor = db.execute("DELETE FROM inventory")
    db.commit()

    return jsonify({"deleted": cursor.rowcount}), 200
