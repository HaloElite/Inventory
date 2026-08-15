import logging
import os

from flask import Flask
from flask_cors import CORS

from app.db import close_db, init_db_command, reset_db_command
from app.errors import register_error_handlers
from config import Config

app = Flask(__name__, instance_relative_config=True, static_folder="static", static_url_path="/static")

app.config.from_object(Config)

# Ohne Debug-Modus loggt Flask sonst erst ab WARNING - unerwartete Fehler
# wuerden damit unsichtbar bleiben. Ein unbekanntes LOG_LEVEL faellt auf INFO
# zurueck, statt den Start der App zu verhindern.
_log_level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)
logging.basicConfig(level=_log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app.logger.setLevel(_log_level)

# CORS nur fuer die konfigurierten Origins (siehe CORS_ORIGINS in config.py).
CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

register_error_handlers(app)

app.teardown_appcontext(close_db)
app.cli.add_command(init_db_command)
app.cli.add_command(reset_db_command)

from app import routes  # noqa: E402  (zirkulaerer Import: Routen brauchen `app`)

# Wann laeuft `flask init-db`?
# ✅ Einmal beim Aufsetzen des Projekts.
# 🔁 Erneut, wenn:
#    - die Datenbankdatei geloescht wurde
#    - das Schema erweitert wurde (neue Tabelle/Index)
#    - eine neue Umgebung eingerichtet wird
# Der Befehl ist idempotent und loescht keine Daten.
# Zum bewussten Leeren gibt es `flask reset-db` (fragt vorher nach).
