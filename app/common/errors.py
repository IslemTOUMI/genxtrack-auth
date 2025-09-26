from flask import jsonify, current_app
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

class ApiError(Exception):
    def __init__(self, message, status_code=400, code="bad_request", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

def _json_error(message, status, code, details=None):
    return jsonify({
        "error": {"code": code, "message": message, "details": details or {}}
    }), status

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(e: ApiError):
        return _json_error(e.message, e.status_code, e.code, e.details)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return _json_error("Invalid request body.", 400, "validation_error", e.messages)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        # Ex: 404, 405, 429…
        return _json_error(e.description or "HTTP error", e.code or 500, "http_error")

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        if current_app.debug:
            # En dev, laissez le traceback en console; masquez côté client
            pass
        return _json_error("Internal server error.", 500, "internal_error")
