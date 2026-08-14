import time

from app import app
from app.db import get_db
from flask import request

@app.route("/get-inventory")
def get_items():
    db = get_db()
    
    items = db.execute("SELECT * FROM inventory").fetchall()
    
    return [dict(row) for row in items], 200

@app.route("/add-inventory", methods=["POST"])
def add_item():
    data = request.get_json()
    item = data.get("item")
    count = int(data.get("count"))
    condition = data.get("condition", "new").lower()  # Default to 'new' if not provided
    category = data.get("category", "general").lower()  # Default to 'general' if not provided
    image = data.get("image")

    if len(item) == 0 or count <= 0:
        return {"error": "Invalid input"}, 200
    
    db = get_db()
    
    # Check if item already exists
    exists = db.execute(f"SELECT * FROM inventory WHERE title = ?", (item,)).fetchall()
    
    rows = [dict(row) for row in exists]

    if not len(rows) > 0:
        db.execute("INSERT INTO inventory (title, count, condition, category) VALUES (?, ?, ?, ?)", (item, count, condition, category))
        
        if image:
            db.execute("UPDATE inventory SET image = ? WHERE title = ?", (image, item))
        db.commit()
    else:
        return {"error": "Item already exists"}, 200


    return {"Item successfully added": True}, 201

@app.route("/update-item/<int:id>", methods=["PUT"])
def update_item(id):
    data = request.get_json()
    title = data.get("title")
    count = int(data.get("count"))  # 'count' value may be a string
    category = data.get("category", "general").lower()  # Default to 'general' if not provided

    if not title:
        return {"error": "Invalid input"}, 200

    db = get_db()

    exists = db.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()

    if not exists:
        return {"error": "Item not found"}, 404
    else:
        new_count = count
        db.execute(
            "UPDATE inventory SET count = ?, title = ?, category = ? WHERE id = ?",
            (new_count, title, category, id),
        )
        db.commit()

    return {"Item successfully updated": True}, 200

@app.route("/delete-item/<int:id>", methods=["DELETE"])
def delete_item(id):
    db = get_db()

    exists = db.execute("SELECT id FROM inventory WHERE id = ?", (id,)).fetchone()

    if not exists:
        return {"error": "Item not found"}, 404

    db.execute("DELETE FROM inventory WHERE id = ?", (id,))
    db.commit()

    return {"Item successfully deleted": True}, 200

@app.route("/clear-inventory", methods=["DELETE"])
def clear_inventory():
    try:
        db = get_db()
        db.execute("DELETE FROM inventory")
        db.commit()
        return "db was cleared", 200
    except Exception as e:
        return f"Error {e}", 500