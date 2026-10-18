"""Endpoints institucionais: índice, health check e operações administrativas."""
import logging
import sqlite3

from src.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

ENDPOINTS_PUBLICOS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


class SistemaController:
    def __init__(self, produtos, usuarios, pedidos, admin, versao):
        self._produtos = produtos
        self._usuarios = usuarios
        self._pedidos = pedidos
        self._admin = admin
        self._versao = versao

    def indice(self):
        return {"mensagem": "Bem-vindo à API da Loja", "versao": self._versao, "endpoints": ENDPOINTS_PUBLICOS}

    def health(self):
        return {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self._produtos.contar(),
                "usuarios": self._usuarios.contar(),
                "pedidos": self._pedidos.contar(),
            },
            "versao": self._versao,
        }

    def resetar_banco(self):
        self._admin.resetar_banco()
        logger.warning("Banco de dados resetado via /admin/reset-db")

    def consultar(self, dados):
        sql = (dados or {}).get("sql", "") if isinstance(dados, dict) else ""
        if not sql:
            raise ValidationError("Query não informada")
        if not sql.strip().upper().startswith("SELECT"):
            raise ValidationError("Apenas consultas SELECT são permitidas")
        try:
            return self._admin.consultar_somente_leitura(sql)
        except sqlite3.Error as erro:
            raise ValidationError(f"Query inválida: {erro}")
