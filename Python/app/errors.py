"""Einheitliche JSON-Fehlerantworten fuer die gesamte API."""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Erwarteter Client-Fehler mit passendem HTTP-Status."""

    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details

    def to_response(self):
        payload = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return jsonify(payload), self.status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _handle_api_error(exc):
        return exc.to_response()

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc):
        # 404/405/415 usw. als JSON statt als HTML-Fehlerseite ausliefern.
        return jsonify({"error": exc.description}), exc.code

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):
        # Details ins Log, nach aussen nur eine generische Meldung.
        app.logger.exception("Unhandled error: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
