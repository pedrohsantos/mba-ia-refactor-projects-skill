"""Regras e fluxo do domínio de usuários (cadastro e autenticação)."""
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from src.utils.exceptions import NotFoundError, UnauthorizedError, ValidationError

logger = logging.getLogger(__name__)

TIPO_PADRAO = "cliente"


class UsuarioController:
    def __init__(self, usuarios):
        self._usuarios = usuarios

    def listar(self):
        return self._usuarios.listar()

    def obter(self, usuario_id):
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if not usuario:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        if not isinstance(dados, dict) or not dados:
            raise ValidationError("Dados inválidos")
        nome = dados.get("nome", "")
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        if not nome or not email or not senha:
            raise ValidationError("Nome, email e senha são obrigatórios")

        usuario_id = self._usuarios.criar(nome, email, generate_password_hash(senha), TIPO_PADRAO)
        logger.info("Usuário criado: id=%s", usuario_id)
        return usuario_id

    def login(self, dados):
        dados = dados if isinstance(dados, dict) else {}
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        if not email or not senha:
            raise ValidationError("Email e senha são obrigatórios")

        usuario, senha_hash = self._usuarios.buscar_credenciais_por_email(email)
        if not usuario or not check_password_hash(senha_hash, senha):
            logger.info("Falha de login")
            raise UnauthorizedError("Email ou senha inválidos")

        logger.info("Login bem-sucedido: id=%s", usuario["id"])
        return {chave: usuario[chave] for chave in ("id", "nome", "email", "tipo")}
