"""Persistência de usuários. O hash da senha nunca sai deste módulo nos serializadores públicos."""

COLUNAS_PUBLICAS = ("id", "nome", "email", "tipo", "criado_em")


def to_public_dict(row):
    return {coluna: row[coluna] for coluna in COLUNAS_PUBLICAS}


class UsuarioModel:
    def __init__(self, get_connection):
        self._conn = get_connection

    def listar(self):
        rows = self._conn().execute("SELECT * FROM usuarios").fetchall()
        return [to_public_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self._conn().execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return to_public_dict(row) if row else None

    def buscar_credenciais_por_email(self, email):
        """Retorna (dados públicos, hash da senha) para autenticação, ou (None, None)."""
        row = self._conn().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if not row:
            return None, None
        return to_public_dict(row), row["senha"]

    def existe(self, usuario_id):
        return self._conn().execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is not None

    def criar(self, nome, email, senha_hash, tipo):
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, senha_hash, tipo),
            )
        return cursor.lastrowid

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
