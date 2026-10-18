import hashlib
import hmac

from sqlalchemy import case, func
from werkzeug.security import check_password_hash, generate_password_hash

from database import PersistenceMixin, db
from utils.time_utils import utcnow

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
MIN_PASSWORD_LENGTH = 4

_MODERN_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


class User(PersistenceMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        """Representação pública — nunca inclui o hash da senha."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if self.password.startswith(_MODERN_HASH_PREFIXES):
            return check_password_hash(self.password, raw_password)
        # Hash MD5 legado: valida uma vez e migra para o algoritmo atual.
        legacy_hash = hashlib.md5(raw_password.encode()).hexdigest()
        if hmac.compare_digest(self.password, legacy_hash):
            self.set_password(raw_password)
            return True
        return False

    def is_admin(self):
        return self.role == ROLE_ADMIN

    @staticmethod
    def get(user_id):
        return db.session.get(User, user_id)

    @staticmethod
    def find_by_email(email):
        return db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

    @staticmethod
    def list_all():
        return db.session.execute(db.select(User).order_by(User.id)).scalars().all()

    @staticmethod
    def count():
        return db.session.scalar(db.select(func.count(User.id)))

    @staticmethod
    def list_with_task_stats(done_status):
        """[(user, total de tasks, tasks concluídas)] em uma única query (evita N+1)."""
        from models.task import Task

        query = (
            db.select(
                User,
                func.count(Task.id),
                func.coalesce(func.sum(case((Task.status == done_status, 1), else_=0)), 0),
            )
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
        )
        return db.session.execute(query).all()
