from sqlalchemy import func

from database import PersistenceMixin, db
from utils.time_utils import utcnow

DEFAULT_COLOR = "#000000"


class Category(PersistenceMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Sem cascade de delete: ao remover a categoria, o SQLAlchemy zera category_id das tasks.
    tasks = db.relationship("Task", back_populates="category")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": str(self.created_at),
        }

    @staticmethod
    def get(category_id):
        return db.session.get(Category, category_id)

    @staticmethod
    def count():
        return db.session.scalar(db.select(func.count(Category.id)))

    @staticmethod
    def list_with_task_count():
        """[(categoria, total de tasks)] em uma única query (evita N+1)."""
        from models.task import Task

        query = (
            db.select(Category, func.count(Task.id))
            .outerjoin(Task, Task.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.id)
        )
        return db.session.execute(query).all()
