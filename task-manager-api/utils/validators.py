"""Validações reutilizadas pelos controllers (uma única fonte de verdade por regra)."""
import re
from datetime import datetime

from utils.exceptions import ValidationError

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
DATE_FORMAT = "%Y-%m-%d"
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def require_payload(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError("Dados inválidos")
    return data


def is_valid_email(email):
    return isinstance(email, str) and bool(EMAIL_PATTERN.match(email))


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse_date(value, message):
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(message)


def parse_int_arg(value, message):
    """Converte query string em int; vazio → None."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(message)


def normalize_tags(tags):
    return ",".join(tags) if isinstance(tags, list) else tags


def validate_color(color):
    if not isinstance(color, str) or not HEX_COLOR_PATTERN.match(color):
        raise ValidationError("Cor inválida. Use o formato #RRGGBB")
    return color
