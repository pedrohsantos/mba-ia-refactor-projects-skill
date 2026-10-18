"""Persistência de pedidos e itens, com escrita transacional."""
from src.utils.exceptions import ValidationError

_SELECT_PEDIDOS_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario,
           pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    {where}
    ORDER BY p.id, i.id
"""


def _agrupar_pedidos(rows):
    pedidos = {}
    for row in rows:
        pedido = pedidos.setdefault(row["id"], {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


class PedidoModel:
    def __init__(self, get_connection):
        self._conn = get_connection

    def listar(self):
        rows = self._conn().execute(_SELECT_PEDIDOS_COM_ITENS.format(where="")).fetchall()
        return _agrupar_pedidos(rows)

    def listar_por_usuario(self, usuario_id):
        sql = _SELECT_PEDIDOS_COM_ITENS.format(where="WHERE p.usuario_id = ?")
        return _agrupar_pedidos(self._conn().execute(sql, (usuario_id,)).fetchall())

    def buscar_status(self, pedido_id):
        row = self._conn().execute("SELECT status FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        return row["status"] if row else None

    def criar(self, usuario_id, total, itens):
        """itens: lista de dicts com produto_id, quantidade e preco_unitario.

        Insere pedido + itens e baixa o estoque numa única transação; a baixa só ocorre
        se ainda houver estoque (protege contra concorrência entre validação e escrita).
        """
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
                (usuario_id, total),
            )
            pedido_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                [(pedido_id, i["produto_id"], i["quantidade"], i["preco_unitario"]) for i in itens],
            )
            for item in itens:
                baixa = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if baixa.rowcount == 0:
                    raise ValidationError(f"Estoque insuficiente para o produto {item['produto_id']}")
        return pedido_id

    def atualizar_status(self, pedido_id, novo_status, devolver_estoque=False):
        conn = self._conn()
        with conn:
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
            if devolver_estoque:
                conn.execute(
                    """
                    UPDATE produtos
                    SET estoque = estoque + (
                        SELECT SUM(quantidade) FROM itens_pedido
                        WHERE itens_pedido.pedido_id = ? AND itens_pedido.produto_id = produtos.id
                    )
                    WHERE id IN (SELECT produto_id FROM itens_pedido WHERE pedido_id = ?)
                    """,
                    (pedido_id, pedido_id),
                )

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

    def resumo_vendas(self):
        row = self._conn().execute(
            """
            SELECT COUNT(*) AS total_pedidos,
                   COALESCE(SUM(total), 0) AS faturamento,
                   COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS pendentes,
                   COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados,
                   COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
            FROM pedidos
            """
        ).fetchone()
        return dict(row)
