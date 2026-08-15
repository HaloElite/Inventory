# Entry point -> importiert die Flask-App aus dem app/-Paket und startet sie.
#
# Achtung: das ist der Werkzeug-Entwicklungsserver. Fuer den produktiven Betrieb
# gehoert ein WSGI-Server davor, z. B.:  gunicorn "app:app" --bind 127.0.0.1:5000
import os

from app import app


def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    # Standardmaessig nur lokal erreichbar. Die API hat keinerlei Authentifizierung -
    # ein Bind auf 0.0.0.0 gibt u. a. /clear-inventory ins gesamte Netz frei.
    host = os.environ.get("HOST", "127.0.0.1")
    # Port 5000 ist auf macOS haeufig vom AirPlay-Receiver belegt.
    port = int(os.environ.get("PORT", "5000"))

    app.run(host=host, port=port, debug=_env_flag("FLASK_DEBUG"))
