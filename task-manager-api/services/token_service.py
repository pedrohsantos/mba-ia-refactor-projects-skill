"""Emissão e verificação de tokens de autenticação assinados e com expiração."""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from utils.exceptions import UnauthorizedError

TOKEN_SALT = "auth-token"


class TokenService:
    def __init__(self, secret_key, max_age_seconds):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._max_age = max_age_seconds

    def issue(self, user):
        return self._serializer.dumps({"user_id": user.id})

    def verify(self, token):
        """Retorna o user_id do token; lança UnauthorizedError se for inválido ou expirado."""
        try:
            payload = self._serializer.loads(token, max_age=self._max_age)
        except (BadSignature, SignatureExpired):
            raise UnauthorizedError("Token inválido ou expirado")
        if not isinstance(payload, dict) or "user_id" not in payload:
            raise UnauthorizedError("Token inválido ou expirado")
        return payload["user_id"]
