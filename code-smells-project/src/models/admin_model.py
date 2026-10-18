"""Operações administrativas sobre o banco."""
from src.database import reset_all


class AdminModel:
    def __init__(self, get_connection):
        self._conn = get_connection

    def resetar_banco(self):
        reset_all(self._conn())

    def consultar_somente_leitura(self, sql):
        """Executa um SELECT com a conexão em modo query_only (qualquer escrita é rejeitada pelo SQLite)."""
        conn = self._conn()
        conn.execute("PRAGMA query_only = ON")
        try:
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.execute("PRAGMA query_only = OFF")
