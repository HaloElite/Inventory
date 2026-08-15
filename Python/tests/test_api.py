"""Regressionstests fuer die Inventory-API.

Jeder Test deckt ein konkretes Finding aus der Backend-Analyse ab.
"""

import re

import pytest

from app.db import DEFAULT_IMAGE, to_iso_utc

ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ---------------------------------------------------------------------------
#   Finding 1: Fehler kamen mit HTTP 200 zurueck
# ---------------------------------------------------------------------------
def test_duplicate_item_returns_409(add):
    assert add().status_code == 201
    response = add()

    assert response.status_code == 409
    assert response.get_json()["error"] == "Item already exists"


def test_duplicate_detection_is_case_insensitive(add):
    add(item="Spaten")
    assert add(item="SPATEN").status_code == 409


def test_invalid_input_returns_400(add):
    assert add(item="").status_code == 400
    assert add(item="   ").status_code == 400


# ---------------------------------------------------------------------------
#   Finding 2: fehlende/nicht-numerische Felder fuehrten zu 500
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        {"count": 3},  # item fehlt
        {"item": "Spaten"},  # count fehlt
        {"item": "Spaten", "count": None},
        {"item": "Spaten", "count": ""},
        {"item": "Spaten", "count": "abc"},
        {"item": None, "count": 3},
        {"item": 42, "count": 3},
    ],
)
def test_malformed_payload_returns_400_not_500(client, body):
    response = client.post("/add-inventory", json=body)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid input"
    assert response.get_json()["details"]


def test_numeric_string_count_is_coerced(add, client):
    assert add(count="7").status_code == 201
    assert client.get("/get-inventory").get_json()[0]["count"] == 7


def test_non_object_body_returns_400(client):
    assert client.post("/add-inventory", json=[1, 2, 3]).status_code == 400
    assert client.post("/add-inventory", data="not json", content_type="application/json").status_code == 400


def test_unknown_field_is_rejected(add):
    response = add(titel="Tippfehler")

    assert response.status_code == 400
    assert any(detail["field"] == "titel" for detail in response.get_json()["details"])


def test_count_must_be_positive_on_create(add):
    assert add(count=0).status_code == 400
    assert add(count=-5).status_code == 400


# ---------------------------------------------------------------------------
#   Finding 3: ungeprueftes `condition` schlug im CHECK-Constraint fehl (500)
# ---------------------------------------------------------------------------
def test_invalid_condition_returns_400(add):
    response = add(condition="kaputt")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid input"


def test_condition_and_category_are_normalised(add):
    body = add(condition="USED", category="  Tools  ").get_json()

    assert body["condition"] == "used"
    assert body["category"] == "tools"


# ---------------------------------------------------------------------------
#   Finding 4: `image` wurde per Nach-UPDATE gesetzt statt im INSERT
# ---------------------------------------------------------------------------
def test_image_is_written_with_the_insert(add):
    assert add(image="static/images/spaten.svg").get_json()["image"] == "static/images/spaten.svg"


def test_missing_image_falls_back_to_default(add):
    assert add().get_json()["image"] == DEFAULT_IMAGE


@pytest.mark.parametrize("image", ["https://evil.example/x.svg", "/etc/passwd", "../../secret.svg"])
def test_unsafe_image_paths_are_rejected(add, image):
    assert add(image=image).status_code == 400


# ---------------------------------------------------------------------------
#   Finding 6: update erlaubte negative Mengen und kein condition/image
# ---------------------------------------------------------------------------
def test_update_rejects_negative_count(add, client):
    item_id = add().get_json()["id"]

    response = client.put(f"/update-item/{item_id}", json={"title": "Spaten", "count": -1})

    assert response.status_code == 400


def test_update_allows_zero_count(add, client):
    item_id = add().get_json()["id"]

    response = client.put(f"/update-item/{item_id}", json={"title": "Spaten", "count": 0})

    assert response.status_code == 200
    assert response.get_json()["count"] == 0


def test_update_can_change_condition_and_image(add, client):
    item_id = add().get_json()["id"]

    response = client.put(
        f"/update-item/{item_id}",
        json={"title": "Spaten", "count": 2, "condition": "damaged", "image": "static/images/x.svg"},
    )

    assert response.status_code == 200
    assert response.get_json()["condition"] == "damaged"
    assert response.get_json()["image"] == "static/images/x.svg"


def test_update_preserves_omitted_fields(add, client):
    item_id = add(condition="used", image="static/images/x.svg").get_json()["id"]

    body = client.put(f"/update-item/{item_id}", json={"title": "Spaten", "count": 9}).get_json()

    assert body["condition"] == "used"
    assert body["image"] == "static/images/x.svg"


def test_update_missing_item_returns_404(client):
    response = client.put("/update-item/999", json={"title": "Spaten", "count": 1})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Item not found"


def test_update_to_existing_title_returns_409(add, client):
    add(item="Spaten")
    other_id = add(item="Harke").get_json()["id"]

    response = client.put(f"/update-item/{other_id}", json={"title": "spaten", "count": 1})

    assert response.status_code == 409


def test_update_keeping_own_title_is_allowed(add, client):
    item_id = add(item="Spaten").get_json()["id"]

    assert client.put(f"/update-item/{item_id}", json={"title": "Spaten", "count": 4}).status_code == 200


# ---------------------------------------------------------------------------
#   delete / clear
# ---------------------------------------------------------------------------
def test_delete_removes_item(add, client):
    item_id = add().get_json()["id"]

    assert client.delete(f"/delete-item/{item_id}").status_code == 200
    assert client.get("/get-inventory").get_json() == []


def test_delete_missing_item_returns_404(client):
    assert client.delete("/delete-item/999").status_code == 404


def test_clear_reports_number_of_deleted_rows(add, client):
    add(item="Spaten")
    add(item="Harke")

    assert client.delete("/clear-inventory").get_json() == {"deleted": 2}


# ---------------------------------------------------------------------------
#   Finding 12: Sortierung und optionale Paginierung
# ---------------------------------------------------------------------------
def test_inventory_is_ordered_by_id(add, client):
    for title in ("Spaten", "Harke", "Rechen"):
        add(item=title)

    ids = [item["id"] for item in client.get("/get-inventory").get_json()]

    assert ids == sorted(ids)


def test_pagination_slices_the_result(add, client):
    for title in ("Spaten", "Harke", "Rechen"):
        add(item=title)

    page = client.get("/get-inventory?limit=2&offset=1").get_json()

    assert [item["title"] for item in page] == ["Harke", "Rechen"]


@pytest.mark.parametrize("query", ["?limit=abc", "?limit=0", "?limit=99999", "?limit=2&offset=-1"])
def test_invalid_pagination_returns_400(client, query):
    assert client.get(f"/get-inventory{query}").status_code == 400


# ---------------------------------------------------------------------------
#   Finding 8: Fehlerbehandlung leakte Exception-Texte / lieferte HTML
# ---------------------------------------------------------------------------
def test_unknown_route_returns_json(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.is_json


def test_wrong_method_returns_json(client):
    response = client.post("/get-inventory")

    assert response.status_code == 405
    assert response.is_json


def test_oversized_body_is_rejected(client):
    response = client.post("/add-inventory", json={"item": "x" * 200_000, "count": 1})

    assert response.status_code == 413


# ---------------------------------------------------------------------------
#   Neu gefunden: created_at kam ohne Zonenkennung -> Frontend zeigte Ortszeit
# ---------------------------------------------------------------------------
def test_created_at_is_iso_utc(add):
    assert ISO_UTC.match(add().get_json()["created_at"])


def test_created_at_is_iso_utc_in_list(add, client):
    add()
    assert ISO_UTC.match(client.get("/get-inventory").get_json()[0]["created_at"])


def test_legacy_timestamps_are_normalised():
    # Format, das CURRENT_TIMESTAMP in bestehenden Datenbanken hinterlassen hat.
    assert to_iso_utc("2026-08-15 19:26:26") == "2026-08-15T19:26:26Z"


def test_already_normalised_timestamps_are_left_alone():
    assert to_iso_utc("2026-08-15T19:26:26Z") == "2026-08-15T19:26:26Z"


def test_unparsable_timestamp_is_passed_through():
    assert to_iso_utc("irgendwas") == "irgendwas"


def test_unexpected_exception_is_not_leaked(client, monkeypatch):
    def boom():
        raise RuntimeError("connection string with secret")

    monkeypatch.setattr("app.routes.get_db", boom)

    response = client.get("/get-inventory")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
    assert "secret" not in response.get_data(as_text=True)
