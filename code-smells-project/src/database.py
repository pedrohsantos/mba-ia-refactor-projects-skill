"""Acesso ao SQLite: uma conexão por contexto de aplicação, schema e dados iniciais."""
import logging
import secrets
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

SEED_PRODUTOS = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

SEED_USUARIOS = (
    ("Admin", "admin@loja.com", "admin"),
    ("João Silva", "joao@email.com", "cliente"),
    ("Maria Santos", "maria@email.com", "cliente"),
)

TABLES_IN_DELETE_ORDER = ("itens_pedido", "pedidos", "produtos", "usuarios")


def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_connection(_exception=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(app):
    """Cria o schema e popula os dados de exemplo na primeira execução."""
    app.teardown_appcontext(close_connection)
    with app.app_context():
        connection = get_connection()
        with connection:
            for statement in SCHEMA:
                connection.execute(statement)
            if connection.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
                _seed(connection, app.config.get("SEED_USER_PASSWORD"))


def _seed(connection, seed_password):
    connection.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        SEED_PRODUTOS,
    )
    if not seed_password:
        seed_password = secrets.token_urlsafe(16)
        logger.warning("SEED_USER_PASSWORD não configurada — usuários de exemplo criados com senha aleatória")
    senha_hash = generate_password_hash(seed_password)
    connection.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, senha_hash, tipo) for nome, email, tipo in SEED_USUARIOS],
    )


def reset_all(connection):
    with connection:
        for table in TABLES_IN_DELETE_ORDER:
            connection.execute(f"DELETE FROM {table}")  # nomes vêm de constante, não do usuário
