"""Configuração da aplicação lida exclusivamente de variáveis de ambiente (.env suportado)."""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    APP_VERSION = "1.0.0"

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")

    # Rotas /admin/* ficam desabilitadas (403) quando o token não está configurado.
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

    # Senha dos usuários de exemplo criados no primeiro boot; aleatória se ausente.
    SEED_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD")


if not os.getenv("SECRET_KEY"):
    logger.warning("SECRET_KEY não configurada — usando chave efêmera (apenas desenvolvimento)")
