from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from database import PersistenceMixin, db
from utils.time_utils import utcnow

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_THRESHOLD = 2  # prioridades 1 e 2 são consideradas altas
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200


class Task(PersistenceMixin, db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", back_populates="tasks")
    category = db.relationship("Category", back_populates="tasks")

    # ---- serialização -------------------------------------------------
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(",") if self.tags else [],
        }

    def to_dict_with_overdue(self, now=None):
        data = self.to_dict()
        data["overdue"] = self.is_overdue(now)
        return data

    # ---- regras da entidade -------------------------------------------
    def is_overdue(self, now=None):
        now = now or utcnow()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

    def is_done(self):
        return self.status == STATUS_DONE

    def is_high_priority(self):
        return self.priority <= HIGH_PRIORITY_THRESHOLD

    # ---- consultas ----------------------------------------------------
    @staticmethod
    def get(task_id):
        return db.session.get(Task, task_id)

    @staticmethod
    def list_with_relations():
        query = db.select(Task).options(joinedload(Task.user), joinedload(Task.category)).order_by(Task.id)
        return db.session.execute(query).scalars().all()

    @staticmethod
    def list_by_user(user_id):
        return db.session.execute(db.select(Task).filter_by(user_id=user_id).order_by(Task.id)).scalars().all()

    @staticmethod
    def search(text=None, status=None, priority=None, user_id=None):
        query = db.select(Task)
        if text:
            query = query.where(or_(Task.title.like(f"%{text}%"), Task.description.like(f"%{text}%")))
        if status:
            query = query.where(Task.status == status)
        if priority is not None:
            query = query.where(Task.priority == priority)
        if user_id is not None:
            query = query.where(Task.user_id == user_id)
        return db.session.execute(query.order_by(Task.id)).scalars().all()

    @staticmethod
    def count():
        return db.session.scalar(db.select(func.count(Task.id)))

    @staticmethod
    def count_by(column):
        rows = db.session.execute(db.select(column, func.count(Task.id)).group_by(column)).all()
        return {key: total for key, total in rows}

    @staticmethod
    def list_overdue(now):
        query = db.select(Task).where(
            Task.due_date.is_not(None),
            Task.due_date < now,
            Task.status.not_in(CLOSED_STATUSES),
        ).order_by(Task.id)
        return db.session.execute(query).scalars().all()

    @staticmethod
    def count_created_since(moment):
        return db.session.scalar(db.select(func.count(Task.id)).where(Task.created_at >= moment))

    @staticmethod
    def count_done_since(moment):
        return db.session.scalar(
            db.select(func.count(Task.id)).where(Task.status == STATUS_DONE, Task.updated_at >= moment)
        )
