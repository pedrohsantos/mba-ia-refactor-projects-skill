"""Tratamento centralizado de erros: exceções de domínio → JSON + status HTTP."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.utils.exceptions import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(erro):
        return jsonify({"erro": erro.message, "sucesso": False}), erro.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(erro):
        return jsonify({"erro": erro.description, "sucesso": False}), erro.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(erro):
        logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
