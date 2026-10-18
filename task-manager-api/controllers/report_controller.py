"""Relatórios de produtividade."""
from datetime import timedelta

from models.category import Category
from models.task import (
    PRIORITY_LABELS,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    Task,
)
from models.user import User
from utils.exceptions import NotFoundError
from utils.time_utils import utcnow

RECENT_ACTIVITY_DAYS = 7


def _percentage(part, total):
    return round((part / total) * 100, 2) if total > 0 else 0


class ReportController:
    def summary(self):
        now = utcnow()
        by_status = Task.count_by(Task.status)
        by_priority = Task.count_by(Task.priority)
        overdue = Task.list_overdue(now)
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": Task.count(),
                "total_users": User.count(),
                "total_categories": Category.count(),
            },
            "tasks_by_status": {
                status: by_status.get(status, 0)
                for status in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
            },
            "tasks_by_priority": {label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()},
            "overdue": {
                "count": len(overdue),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": (now - task.due_date).days,
                    }
                    for task in overdue
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": Task.count_created_since(since),
                "tasks_completed_last_7_days": Task.count_done_since(since),
            },
            "user_productivity": [
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "total_tasks": total,
                    "completed_tasks": completed,
                    "completion_rate": _percentage(completed, total),
                }
                for user, total, completed in User.list_with_task_stats(STATUS_DONE)
            ],
        }

    def user_report(self, user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado")

        tasks = Task.list_by_user(user_id)
        now = utcnow()
        counts = {status: 0 for status in (STATUS_DONE, STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_CANCELLED)}
        for task in tasks:
            if task.status in counts:
                counts[task.status] += 1

        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": {
                "total_tasks": len(tasks),
                "done": counts[STATUS_DONE],
                "pending": counts[STATUS_PENDING],
                "in_progress": counts[STATUS_IN_PROGRESS],
                "cancelled": counts[STATUS_CANCELLED],
                "overdue": sum(1 for task in tasks if task.is_overdue(now)),
                "high_priority": sum(1 for task in tasks if task.is_high_priority()),
                "completion_rate": _percentage(counts[STATUS_DONE], len(tasks)),
            },
        }
