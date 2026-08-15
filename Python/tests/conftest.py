import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from app.db import ensure_schema  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    flask_app.config.update(
        TESTING=True,
        DATABASE=str(tmp_path / "test.db"),
        # TESTING setzt PROPAGATE_EXCEPTIONS implizit auf True; wir wollen aber
        # die registrierten Errorhandler testen.
        PROPAGATE_EXCEPTIONS=False,
    )

    with flask_app.app_context():
        ensure_schema()

    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def location(client):
    def _location(name, **overrides):
        body = {"name": name}
        body.update(overrides)
        response = client.post("/add-location", json=body)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _location


@pytest.fixture()
def add(client):
    def _add(**overrides):
        body = {"item": "Spaten", "count": 3}
        body.update(overrides)
        return client.post("/add-inventory", json=body)

    return _add
