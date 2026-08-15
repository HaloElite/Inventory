import sqlite3

from flask import current_app, jsonify, request

from app import app
from app.db import DEFAULT_IMAGE, ITEM_COLUMNS, get_db, serialise_item
from app.errors import ApiError
from app.schemas import ItemCreate, ItemUpdate, format_validation_errors
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
    return db.execute(f"SELECT {ITEM_COLUMNS} FROM inventory WHERE id = ?", (item_id,)).fetchone()


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

    sql = f"SELECT {ITEM_COLUMNS} FROM inventory ORDER BY id"
    params = ()

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = (limit, offset)

    items = db.execute(sql, params).fetchall()

    return jsonify([serialise_item(row) for row in items]), 200


@app.route("/add-inventory", methods=["POST"])
def add_item():
    payload = _parse_body(ItemCreate)
    db = get_db()

    if _find_title_conflict(db, payload.item) is not None:
        raise ApiError("Item already exists", 409)

    try:
        cursor = db.execute(
            "INSERT INTO inventory (title, count, condition, category, image) VALUES (?, ?, ?, ?, ?)",
            (payload.item, payload.count, payload.condition, payload.category, payload.image or DEFAULT_IMAGE),
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

    try:
        db.execute(
            "UPDATE inventory SET title = ?, count = ?, category = ?, condition = ?, image = ? WHERE id = ?",
            (payload.title, payload.count, payload.category, condition, image, item_id),
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


@app.route("/clear-inventory", methods=["DELETE"])
def clear_inventory():
    db = get_db()

    cursor = db.execute("DELETE FROM inventory")
    db.commit()

    return jsonify({"deleted": cursor.rowcount}), 200
