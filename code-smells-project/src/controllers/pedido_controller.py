"""Regras e fluxo do domínio de pedidos."""
import logging

from src.utils.exceptions import NotFoundError, ValidationError
from src.utils.validators import positive_int

logger = logging.getLogger(__name__)

STATUS_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_CANCELADO = "cancelado"


class PedidoController:
    def __init__(self, pedidos, produtos, notificacoes):
        self._pedidos = pedidos
        self._produtos = produtos
        self._notificacoes = notificacoes

    def criar(self, dados):
        if not isinstance(dados, dict) or not dados:
            raise ValidationError("Dados inválidos")
        usuario_id = dados.get("usuario_id")
        itens = dados.get("itens", [])
        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not isinstance(itens, list) or not itens:
            raise ValidationError("Pedido deve ter pelo menos 1 item")

        for item in itens:
            if not isinstance(item, dict):
                raise ValidationError("Item de pedido inválido")
            positive_int(item.get("produto_id"), "produto_id inválido")
            positive_int(item.get("quantidade"), "Quantidade deve ser um inteiro positivo")

        produtos = self._produtos.buscar_por_ids([item["produto_id"] for item in itens])
        total = 0
        linhas = []
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"])
            total = total + (produto["preco"] * item["quantidade"])
            linhas.append({
                "produto_id": item["produto_id"],
                "quantidade": item["quantidade"],
                "preco_unitario": produto["preco"],
            })

        pedido_id = self._pedidos.criar(usuario_id, total, linhas)
        self._notificacoes.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar(self):
        return self._pedidos.listar()

    def listar_por_usuario(self, usuario_id):
        return self._pedidos.listar_por_usuario(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        dados = dados if isinstance(dados, dict) else {}
        novo_status = dados.get("status", "")
        if novo_status not in STATUS_VALIDOS:
            raise ValidationError("Status inválido")

        status_atual = self._pedidos.buscar_status(pedido_id)
        if status_atual is None:
            raise NotFoundError("Pedido não encontrado")

        devolver_estoque = novo_status == STATUS_CANCELADO and status_atual != STATUS_CANCELADO
        self._pedidos.atualizar_status(pedido_id, novo_status, devolver_estoque=devolver_estoque)
        self._notificacoes.status_alterado(pedido_id, novo_status)
