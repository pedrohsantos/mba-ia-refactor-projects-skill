"""Regras e fluxo do domínio de produtos."""
import logging

from src.utils.exceptions import NotFoundError, ValidationError
from src.utils.validators import non_negative_number, optional_float, require_fields, require_payload

logger = logging.getLogger(__name__)

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_MIN_LEN = 2
NOME_MAX_LEN = 200

CAMPOS_OBRIGATORIOS = {
    "nome": "Nome é obrigatório",
    "preco": "Preço é obrigatório",
    "estoque": "Estoque é obrigatório",
}


class ProdutoController:
    def __init__(self, produtos):
        self._produtos = produtos

    def listar(self):
        produtos = self._produtos.listar()
        logger.info("Listando %s produtos", len(produtos))
        return produtos

    def obter(self, produto_id):
        produto = self._produtos.buscar_por_id(produto_id)
        if not produto:
            raise NotFoundError("Produto não encontrado")
        return produto

    def pesquisar(self, termo, categoria, preco_min, preco_max):
        return self._produtos.pesquisar(
            termo,
            categoria,
            optional_float(preco_min, "preco_min inválido"),
            optional_float(preco_max, "preco_max inválido"),
        )

    def criar(self, dados):
        produto = self._validar(dados)
        produto_id = self._produtos.criar(**produto)
        logger.info("Produto criado com ID %s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        self.obter(produto_id)
        self._produtos.atualizar(produto_id, **self._validar(dados))

    def deletar(self, produto_id):
        self.obter(produto_id)
        self._produtos.deletar(produto_id)
        logger.info("Produto %s deletado", produto_id)

    @staticmethod
    def _validar(dados):
        require_payload(dados)
        require_fields(dados, CAMPOS_OBRIGATORIOS)

        nome = dados["nome"]
        categoria = dados.get("categoria", CATEGORIA_PADRAO)
        preco = non_negative_number(dados["preco"], "Preço inválido", "Preço não pode ser negativo")
        estoque = non_negative_number(dados["estoque"], "Estoque inválido", "Estoque não pode ser negativo")

        if not isinstance(nome, str):
            raise ValidationError("Nome inválido")
        if len(nome) < NOME_MIN_LEN:
            raise ValidationError("Nome muito curto")
        if len(nome) > NOME_MAX_LEN:
            raise ValidationError("Nome muito longo")
        if categoria not in CATEGORIAS_VALIDAS:
            raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

        return {
            "nome": nome,
            "descricao": dados.get("descricao", ""),
            "preco": preco,
            "estoque": estoque,
            "categoria": categoria,
        }
