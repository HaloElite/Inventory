"""Tests fuer die hierarchische Lagerort-Verwaltung."""


def test_locations_start_empty(client):
    response = client.get("/get-locations")

    assert response.status_code == 200
    assert response.get_json() == []


# ---------------------------------------------------------------------------
#   Anlegen
# ---------------------------------------------------------------------------
def test_create_root_location(client):
    response = client.post("/add-location", json={"name": "Schuppen"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Schuppen"
    assert body["parent_id"] is None
    assert body["path"] == "Schuppen"


def test_create_nested_location_builds_path(location):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])
    box = location("Kiste B", parent_id=shelf["id"])

    assert box["parent_id"] == shelf["id"]
    assert box["path"] == "Schuppen / Regal 3 / Kiste B"


def test_name_is_trimmed_and_required(client):
    assert client.post("/add-location", json={"name": "   "}).status_code == 400
    assert client.post("/add-location", json={}).status_code == 400


def test_unknown_field_is_rejected(client):
    assert client.post("/add-location", json={"name": "Schuppen", "typo": 1}).status_code == 400


# ---------------------------------------------------------------------------
#   Eindeutigkeit gilt pro Ebene, nicht global
# ---------------------------------------------------------------------------
def test_duplicate_name_under_same_parent_is_rejected(client, location):
    shed = location("Schuppen")
    location("Kiste B", parent_id=shed["id"])

    response = client.post("/add-location", json={"name": "kiste b", "parent_id": shed["id"]})

    assert response.status_code == 409


def test_same_name_under_different_parents_is_allowed(client, location):
    shelf_a = location("Regal A")
    shelf_b = location("Regal B")

    location("Kiste B", parent_id=shelf_a["id"])
    response = client.post("/add-location", json={"name": "Kiste B", "parent_id": shelf_b["id"]})

    assert response.status_code == 201


def test_duplicate_root_name_is_rejected(client, location):
    location("Schuppen")

    assert client.post("/add-location", json={"name": "SCHUPPEN"}).status_code == 409


# ---------------------------------------------------------------------------
#   Elternteil muss existieren
# ---------------------------------------------------------------------------
def test_unknown_parent_is_rejected(client):
    response = client.post("/add-location", json={"name": "Kiste B", "parent_id": 999})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Parent location not found"


# ---------------------------------------------------------------------------
#   Aendern
# ---------------------------------------------------------------------------
def test_rename_updates_paths_of_descendants(client, location):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])

    response = client.put(f"/update-location/{shed['id']}", json={"name": "Gartenhaus"})

    assert response.status_code == 200
    assert response.get_json()["path"] == "Gartenhaus"

    paths = {row["id"]: row["path"] for row in client.get("/get-locations").get_json()}
    assert paths[shelf["id"]] == "Gartenhaus / Regal 3"


def test_reparent_moves_subtree(client, location):
    shed = location("Schuppen")
    garage = location("Garage")
    shelf = location("Regal 3", parent_id=shed["id"])
    box = location("Kiste B", parent_id=shelf["id"])

    assert client.put(f"/update-location/{shelf['id']}", json={"name": "Regal 3", "parent_id": garage["id"]}).status_code == 200

    paths = {row["id"]: row["path"] for row in client.get("/get-locations").get_json()}
    assert paths[shelf["id"]] == "Garage / Regal 3"
    assert paths[box["id"]] == "Garage / Regal 3 / Kiste B"


def test_move_to_root(client, location):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])

    response = client.put(f"/update-location/{shelf['id']}", json={"name": "Regal 3", "parent_id": None})

    assert response.status_code == 200
    assert response.get_json()["path"] == "Regal 3"


def test_update_unknown_location_returns_404(client):
    assert client.put("/update-location/999", json={"name": "X"}).status_code == 404


def test_rename_into_existing_sibling_is_rejected(client, location):
    shed = location("Schuppen")
    location("Kiste A", parent_id=shed["id"])
    box_b = location("Kiste B", parent_id=shed["id"])

    assert client.put(f"/update-location/{box_b['id']}", json={"name": "Kiste A"}).status_code == 409


def test_keeping_own_name_is_allowed(client, location):
    shed = location("Schuppen")

    assert client.put(f"/update-location/{shed['id']}", json={"name": "Schuppen"}).status_code == 200


# ---------------------------------------------------------------------------
#   Zyklusschutz: ein Ort darf nicht unter sich selbst haengen
# ---------------------------------------------------------------------------
def test_location_cannot_become_its_own_parent(client, location):
    shed = location("Schuppen")

    response = client.put(f"/update-location/{shed['id']}", json={"name": "Schuppen", "parent_id": shed["id"]})

    assert response.status_code == 409
    assert response.get_json()["error"] == "A location cannot be moved into its own subtree"


def test_location_cannot_move_into_its_own_descendant(client, location):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])
    box = location("Kiste B", parent_id=shelf["id"])

    response = client.put(f"/update-location/{shed['id']}", json={"name": "Schuppen", "parent_id": box["id"]})

    assert response.status_code == 409


# ---------------------------------------------------------------------------
#   Loeschen
# ---------------------------------------------------------------------------
def test_delete_empty_location(client, location):
    shed = location("Schuppen")

    assert client.delete(f"/delete-location/{shed['id']}").status_code == 200
    assert client.get("/get-locations").get_json() == []


def test_delete_unknown_location_returns_404(client):
    assert client.delete("/delete-location/999").status_code == 404


def test_delete_location_with_children_is_rejected(client, location):
    shed = location("Schuppen")
    location("Regal 3", parent_id=shed["id"])

    response = client.delete(f"/delete-location/{shed['id']}")

    assert response.status_code == 409
    assert response.get_json()["child_locations"] == 1


def test_delete_location_holding_items_is_rejected(client, location, add):
    shed = location("Schuppen")
    add(item="Spaten", location_id=shed["id"])

    response = client.delete(f"/delete-location/{shed['id']}")

    assert response.status_code == 409
    assert response.get_json()["items"] == 1


# ---------------------------------------------------------------------------
#   Verknuepfung mit dem Inventar
# ---------------------------------------------------------------------------
def test_item_without_location(add):
    body = add().get_json()

    assert body["location_id"] is None
    assert body["location_path"] is None


def test_item_carries_resolved_location_path(location, add):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])

    body = add(location_id=shelf["id"]).get_json()

    assert body["location_id"] == shelf["id"]
    assert body["location_path"] == "Schuppen / Regal 3"


def test_unknown_location_on_item_is_rejected(add):
    response = add(location_id=999)

    assert response.status_code == 404
    assert response.get_json()["error"] == "Location not found"


def test_update_can_assign_and_clear_location(client, location, add):
    shed = location("Schuppen")
    item_id = add().get_json()["id"]

    assigned = client.put(
        f"/update-item/{item_id}",
        json={"title": "Spaten", "count": 1, "location_id": shed["id"]},
    )
    assert assigned.get_json()["location_path"] == "Schuppen"

    cleared = client.put(
        f"/update-item/{item_id}",
        json={"title": "Spaten", "count": 1, "location_id": None},
    )
    assert cleared.get_json()["location_id"] is None


def test_update_without_location_field_keeps_it(client, location, add):
    shed = location("Schuppen")
    item_id = add(location_id=shed["id"]).get_json()["id"]

    body = client.put(f"/update-item/{item_id}", json={"title": "Spaten", "count": 2}).get_json()

    assert body["location_id"] == shed["id"]


# ---------------------------------------------------------------------------
#   Der eigentliche Ertrag der Hierarchie: Filtern schliesst Unterorte ein
# ---------------------------------------------------------------------------
def test_filter_by_location_includes_descendants(client, location, add):
    shed = location("Schuppen")
    shelf = location("Regal 3", parent_id=shed["id"])
    box = location("Kiste B", parent_id=shelf["id"])
    garage = location("Garage")

    add(item="Spaten", location_id=shed["id"])
    add(item="Schrauben", location_id=box["id"])
    add(item="Wagenheber", location_id=garage["id"])
    add(item="Ortlos")

    titles = [row["title"] for row in client.get(f"/get-inventory?location_id={shed['id']}").get_json()]

    assert sorted(titles) == ["Schrauben", "Spaten"]


def test_filter_by_leaf_location(client, location, add):
    shed = location("Schuppen")
    box = location("Kiste B", parent_id=shed["id"])

    add(item="Spaten", location_id=shed["id"])
    add(item="Schrauben", location_id=box["id"])

    titles = [row["title"] for row in client.get(f"/get-inventory?location_id={box['id']}").get_json()]

    assert titles == ["Schrauben"]


def test_filter_by_unknown_location_returns_404(client):
    assert client.get("/get-inventory?location_id=999").status_code == 404