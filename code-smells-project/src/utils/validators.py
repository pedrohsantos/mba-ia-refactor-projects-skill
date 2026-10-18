"""Validações reutilizáveis pelos controllers."""
from src.utils.exceptions import ValidationError


def require_payload(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    return dados


def require_fields(dados, mensagens_por_campo):
    for campo, mensagem in mensagens_por_campo.items():
        if campo not in dados:
            raise ValidationError(mensagem)


def is_number(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def non_negative_number(valor, mensagem_tipo, mensagem_negativo):
    if not is_number(valor):
        raise ValidationError(mensagem_tipo)
    if valor < 0:
        raise ValidationError(mensagem_negativo)
    return valor


def positive_int(valor, mensagem):
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        raise ValidationError(mensagem)
    return valor


def optional_float(valor, mensagem):
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValidationError(mensagem)
