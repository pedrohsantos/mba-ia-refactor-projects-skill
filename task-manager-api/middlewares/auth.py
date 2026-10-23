"""Autenticação por token Bearer e autorização por papel."""
from functools import wraps

from flask import current_app, g, request

from models.user import User
from utils.exceptions import ForbiddenError, UnauthorizedError

TOKEN_SERVICE_KEY = "token_service"


def init_auth(app, token_service):
    app.extensions[TOKEN_SERVICE_KEY] = token_service


def load_current_user():
    """Usuário autenticado pelo header Authorization, ou None para chamadas anônimas.

    Um header presente mas inválido/expirado gera 401 (não é tratado como anônimo).
    """
    header = request.headers.get("Authorization", "")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Token inválido ou expirado")

    user_id = current_app.extensions[TOKEN_SERVICE_KEY].verify(token)
    user = User.get(user_id)
    if not user or not user.active:
        raise UnauthorizedError("Token inválido ou expirado")
    return user


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = load_current_user()
        if g.current_user is None:
            raise UnauthorizedError("Autenticação necessária")
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    @wraps(view)
    @require_auth
    def wrapper(*args, **kwargs):
        if not g.current_user.is_admin():
            raise ForbiddenError("Apenas administradores")
        return view(*args, **kwargs)

    return wrapper
