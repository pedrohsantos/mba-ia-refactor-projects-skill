"""Proteção das rotas administrativas por token configurado no ambiente."""
import hmac
from functools import wraps

from flask import current_app, request

from src.utils.exceptions import ForbiddenError, UnauthorizedError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        esperado = current_app.config.get("ADMIN_TOKEN")
        if not esperado:
            raise ForbiddenError("Rotas administrativas desabilitadas (ADMIN_TOKEN não configurado)")
        recebido = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(recebido, esperado):
            raise UnauthorizedError("Token administrativo inválido")
        return view(*args, **kwargs)

    return wrapper
