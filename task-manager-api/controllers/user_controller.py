"""Fluxo e regras de usuários e autenticação."""
import logging

from models.task import STATUS_DONE, Task
from models.user import MIN_PASSWORD_LENGTH, ROLE_USER, VALID_ROLES, User
from utils.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from utils.time_utils import utcnow
from utils.validators import is_valid_email, require_payload

logger = logging.getLogger(__name__)

USER_TASK_FIELDS = ("id", "title", "description", "status", "priority", "created_at", "due_date")


def _validate_email(email):
    if not is_valid_email(email):
        raise ValidationError("Email inválido")
    return email


def _validate_role(role):
    if role not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return role


def _ensure_email_available(email, current_user_id=None):
    existing = User.find_by_email(email)
    if existing and existing.id != current_user_id:
        raise ConflictError("Email já cadastrado")


class UserController:
    def __init__(self, token_signer):
        self._token_signer = token_signer

    def list_users(self):
        result = []
        for user, task_count, _completed in User.list_with_task_stats(STATUS_DONE):
            data = user.to_dict()
            data["task_count"] = task_count
            result.append(data)
        return result

    def get_user(self, user_id):
        user = self._get_or_404(user_id)
        data = user.to_dict()
        data["tasks"] = [task.to_dict() for task in Task.list_by_user(user_id)]
        return data

    def create_user(self, data):
        require_payload(data)
        name, email, password = data.get("name"), data.get("email"), data.get("password")
        role = data.get("role", ROLE_USER)

        if not name:
            raise ValidationError("Nome é obrigatório")
        if not email:
            raise ValidationError("Email é obrigatório")
        if not password:
            raise ValidationError("Senha é obrigatória")
        _validate_email(email)
        if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError("Senha deve ter no mínimo 4 caracteres")
        _ensure_email_available(email)
        _validate_role(role)

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        user.save()
        logger.info("Usuário criado: %s", user.id)
        return user.to_dict()

    def update_user(self, user_id, data):
        user = self._get_or_404(user_id)
        require_payload(data)

        if "name" in data and not data["name"]:
            raise ValidationError("Nome é obrigatório")
        if "email" in data:
            _validate_email(data["email"])
            _ensure_email_available(data["email"], current_user_id=user_id)
        if "password" in data and (not isinstance(data["password"], str) or len(data["password"]) < MIN_PASSWORD_LENGTH):
            raise ValidationError("Senha muito curta")
        if "role" in data:
            _validate_role(data["role"])
        if "active" in data and not isinstance(data["active"], bool):
            raise ValidationError("Campo active deve ser booleano")

        for field in ("name", "email", "role", "active"):
            if field in data:
                setattr(user, field, data[field])
        if "password" in data:
            user.set_password(data["password"])
        user.save()
        return user.to_dict()

    def delete_user(self, user_id):
        # As tasks do usuário são removidas pelo cascade do relacionamento User.tasks.
        self._get_or_404(user_id).delete()
        logger.info("Usuário deletado: %s", user_id)

    def list_user_tasks(self, user_id):
        self._get_or_404(user_id)
        now = utcnow()
        result = []
        for task in Task.list_by_user(user_id):
            full = task.to_dict()
            data = {field: full[field] for field in USER_TASK_FIELDS}
            data["overdue"] = task.is_overdue(now)
            result.append(data)
        return result

    def login(self, data):
        require_payload(data)
        email, password = data.get("email"), data.get("password")
        if not email or not password:
            raise ValidationError("Email e senha são obrigatórios")

        user = User.find_by_email(email)
        if not user or not user.check_password(password):
            raise UnauthorizedError("Credenciais inválidas")
        if not user.active:
            raise ForbiddenError("Usuário inativo")

        user.save()  # persiste eventual migração do hash legado
        return {
            "message": "Login realizado com sucesso",
            "user": user.to_dict(),
            "token": self._token_signer.dumps({"user_id": user.id}),
        }

    @staticmethod
    def _get_or_404(user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado")
        return user
