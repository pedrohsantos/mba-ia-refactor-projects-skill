"""Fluxo e regras de tasks."""
import logging

from models.category import Category
from models.task import (
    DEFAULT_PRIORITY,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    VALID_STATUSES,
    Task,
)
from models.user import User
from utils.exceptions import NotFoundError, ValidationError
from utils.time_utils import utcnow
from utils.validators import is_int, normalize_tags, parse_date, parse_int_arg, require_payload

logger = logging.getLogger(__name__)

CREATE_DATE_ERROR = "Formato de data inválido. Use YYYY-MM-DD"
UPDATE_DATE_ERROR = "Formato de data inválido"


def _validate_title(title):
    if not isinstance(title, str):
        raise ValidationError("Título inválido")
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return title


def _validate_status(status):
    if status not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return status


def _validate_priority(priority):
    if not is_int(priority) or not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError("Prioridade deve ser entre 1 e 5")
    return priority


def _ensure_user(user_id):
    if user_id and not User.get(user_id):
        raise NotFoundError("Usuário não encontrado")
    return user_id


def _ensure_category(category_id):
    if category_id and not Category.get(category_id):
        raise NotFoundError("Categoria não encontrada")
    return category_id


class TaskController:
    def __init__(self, notifications):
        self._notifications = notifications

    def list_tasks(self):
        now = utcnow()
        result = []
        for task in Task.list_with_relations():
            data = task.to_dict_with_overdue(now)
            data["user_name"] = task.user.name if task.user else None
            data["category_name"] = task.category.name if task.category else None
            result.append(data)
        return result

    def get_task(self, task_id):
        return self._get_or_404(task_id).to_dict_with_overdue()

    def create_task(self, data):
        require_payload(data)
        title = data.get("title")
        if not title:
            raise ValidationError("Título é obrigatório")

        task = Task(
            title=_validate_title(title),
            description=data.get("description", ""),
            status=_validate_status(data.get("status", STATUS_PENDING)),
            priority=_validate_priority(data.get("priority", DEFAULT_PRIORITY)),
            user_id=_ensure_user(data.get("user_id")),
            category_id=_ensure_category(data.get("category_id")),
        )
        if data.get("due_date"):
            task.due_date = parse_date(data["due_date"], CREATE_DATE_ERROR)
        if data.get("tags"):
            task.tags = normalize_tags(data["tags"])

        task.save()
        logger.info("Task criada: %s", task.id)
        self._notify_assignment(task)
        return task.to_dict()

    def update_task(self, task_id, data):
        task = self._get_or_404(task_id)
        require_payload(data)

        changes = {}
        if "title" in data:
            changes["title"] = _validate_title(data["title"])
        if "description" in data:
            changes["description"] = data["description"]
        if "status" in data:
            changes["status"] = _validate_status(data["status"])
        if "priority" in data:
            changes["priority"] = _validate_priority(data["priority"])
        if "user_id" in data:
            changes["user_id"] = _ensure_user(data["user_id"])
        if "category_id" in data:
            changes["category_id"] = _ensure_category(data["category_id"])
        if "due_date" in data:
            changes["due_date"] = parse_date(data["due_date"], UPDATE_DATE_ERROR) if data["due_date"] else None
        if "tags" in data:
            changes["tags"] = normalize_tags(data["tags"])

        assigned_to_new_user = "user_id" in changes and changes["user_id"] and changes["user_id"] != task.user_id
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = utcnow()
        task.save()
        logger.info("Task atualizada: %s", task.id)
        if assigned_to_new_user:
            self._notify_assignment(task)
        return task.to_dict()

    def delete_task(self, task_id):
        task = self._get_or_404(task_id)
        task.delete()
        logger.info("Task deletada: %s", task_id)

    def search_tasks(self, text, status, priority, user_id):
        tasks = Task.search(
            text=text,
            status=status,
            priority=parse_int_arg(priority, "Prioridade inválida"),
            user_id=parse_int_arg(user_id, "user_id inválido"),
        )
        return [task.to_dict() for task in tasks]

    def stats(self):
        by_status = Task.count_by(Task.status)
        total = Task.count()
        done = by_status.get(STATUS_DONE, 0)
        return {
            "total": total,
            "pending": by_status.get(STATUS_PENDING, 0),
            "in_progress": by_status.get(STATUS_IN_PROGRESS, 0),
            "done": done,
            "cancelled": by_status.get(STATUS_CANCELLED, 0),
            "overdue": len(Task.list_overdue(utcnow())),
            "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
        }

    @staticmethod
    def _get_or_404(task_id):
        task = Task.get(task_id)
        if not task:
            raise NotFoundError("Task não encontrada")
        return task

    def _notify_assignment(self, task):
        if task.user:
            self._notifications.notify_task_assigned(task.user, task)
