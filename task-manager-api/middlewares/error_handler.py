"""Tratamento centralizado de erros: exceções de domínio → JSON {"error": ...} + status HTTP."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db
from utils.exceptions import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        logger.exception("Erro não tratado")
        return jsonify({"error": "Erro interno"}), 500
