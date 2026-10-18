from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class PersistenceMixin:
    """Operações de escrita expostas pelos models (controllers não acessam a sessão diretamente)."""

    def save(self):
        db.session.add(self)
        self._commit()
        return self

    def delete(self):
        db.session.delete(self)
        self._commit()

    @staticmethod
    def _commit():
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
