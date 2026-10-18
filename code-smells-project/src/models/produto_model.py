"""Persistência de produtos."""

COLUNAS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def to_dict(row):
    return {coluna: row[coluna] for coluna in COLUNAS}


class ProdutoModel:
    def __init__(self, get_connection):
        self._conn = get_connection

    def listar(self):
        rows = self._conn().execute("SELECT * FROM produtos").fetchall()
        return [to_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self._conn().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return to_dict(row) if row else None

    def buscar_por_ids(self, produto_ids):
        ids = list(set(produto_ids))
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self._conn().execute(f"SELECT * FROM produtos WHERE id IN ({placeholders})", ids).fetchall()
        return {row["id"]: to_dict(row) for row in rows}

    def pesquisar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clausulas, params = ["1=1"], []
        if termo:
            clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clausulas.append("categoria = ?")
            params.append(categoria)
        if preco_min:
            clausulas.append("preco >= ?")
            params.append(preco_min)
        if preco_max:
            clausulas.append("preco <= ?")
            params.append(preco_max)
        sql = "SELECT * FROM produtos WHERE " + " AND ".join(clausulas)
        return [to_dict(row) for row in self._conn().execute(sql, params).fetchall()]

    def criar(self, nome, descricao, preco, estoque, categoria):
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        conn = self._conn()
        with conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def deletar(self, produto_id):
        conn = self._conn()
        with conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
