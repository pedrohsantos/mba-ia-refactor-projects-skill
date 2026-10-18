"""Configuração lida de variáveis de ambiente (.env suportado via python-dotenv)."""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    APP_VERSION = "1.0"

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Notificações por e-mail: desabilitadas se SMTP_HOST não estiver configurado.
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


if not os.getenv("SECRET_KEY"):
    logger.warning("SECRET_KEY não configurada — usando chave efêmera (apenas desenvolvimento)")
