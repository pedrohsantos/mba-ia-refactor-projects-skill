"""Script para popular o banco com dados iniciais (python seed.py)."""
import logging
import os
import secrets
from datetime import timedelta

from app import app
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.time_utils import utcnow

logger = logging.getLogger(__name__)

USERS = (
    ("João Silva", "joao@email.com", "admin"),
    ("Maria Santos", "maria@email.com", "user"),
    ("Pedro Oliveira", "pedro@email.com", "manager"),
)

CATEGORIES = (
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
)


def _task_rows(users, categories, now):
    joao, maria, pedro = users
    backend, frontend, devops, bug = categories
    return [
        {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT", "status": "pending", "priority": 1, "user": joao, "category": backend, "due_date": now - timedelta(days=3)},
        {"title": "Criar tela de login", "description": "Tela de login responsiva", "status": "in_progress", "priority": 2, "user": maria, "category": frontend, "due_date": now + timedelta(days=5)},
        {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions", "status": "done", "priority": 2, "user": pedro, "category": devops, "tags": "devops,ci,github"},
        {"title": "Corrigir bug no filtro de busca", "description": "Filtro não funciona com caracteres especiais", "status": "pending", "priority": 1, "user": joao, "category": bug, "due_date": now - timedelta(days=1)},
        {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros", "status": "pending", "priority": 3, "user": joao, "category": backend, "due_date": now + timedelta(days=10)},
        {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%", "status": "pending", "priority": 2, "user": maria, "category": backend},
        {"title": "Documentar API com Swagger", "description": "Gerar documentação automática", "status": "cancelled", "priority": 4, "user": pedro, "category": backend},
        {"title": "Refatorar models", "description": "Melhorar organização dos models", "status": "in_progress", "priority": 3, "user": maria, "category": backend, "tags": "refactor,tech-debt"},
        {"title": "Configurar monitoramento", "description": "Prometheus + Grafana", "status": "pending", "priority": 4, "user": pedro, "category": devops, "due_date": now + timedelta(days=20)},
        {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic", "status": "pending", "priority": 3, "user": joao, "category": backend, "tags": "improvement,validation"},
    ]


def seed_data():
    password = os.getenv("SEED_USER_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(16)
        logger.warning("SEED_USER_PASSWORD não configurada — usuários de exemplo criados com senha aleatória")

    with app.app_context():
        db.session.execute(db.delete(Task))
        db.session.execute(db.delete(User))
        db.session.execute(db.delete(Category))

        users = []
        for name, email, role in USERS:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            users.append(user)
        categories = [Category(name=name, description=description, color=color) for name, description, color in CATEGORIES]
        db.session.add_all(users + categories)
        db.session.flush()

        db.session.add_all(Task(**row) for row in _task_rows(users, categories, utcnow()))
        db.session.commit()

        logger.info(
            "Seed concluído: %s usuários, %s categorias, %s tasks", User.count(), Category.count(), Task.count()
        )


if __name__ == "__main__":
    seed_data()
