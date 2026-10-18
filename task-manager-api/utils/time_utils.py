from datetime import datetime, timezone


def utcnow():
    """UTC atual sem tzinfo — mesmo formato já gravado no SQLite (substitui datetime.utcnow, deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
