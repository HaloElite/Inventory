# config.py
import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))

# Der Vite-Dev-Server laeuft auf 5173 und proxied /api hierher.
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def _csv_env(name, default):
    raw = os.environ.get(name) or default
    return [value.strip() for value in raw.split(",") if value.strip()]


class Config:
    # Kein fixes Secret im Repo: ohne gesetzte Env wird pro Prozess eines erzeugt.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    DATABASE = os.environ.get("DATABASE") or os.path.join(basedir, "instance", "todos.db")

    # Nur diese Origins duerfen die API cross-origin aufrufen.
    CORS_ORIGINS = _csv_env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)

    # Obergrenze fuer ?limit= auf /get-inventory
    MAX_PAGE_SIZE = 500

    # Deckelt die Groesse eingehender Request-Bodies (Flask antwortet sonst 413).
    MAX_CONTENT_LENGTH = 64 * 1024

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
