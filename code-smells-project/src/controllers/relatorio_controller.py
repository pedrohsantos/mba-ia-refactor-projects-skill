"""Relatórios de vendas: regras de desconto e indicadores."""

# (faturamento mínimo exclusivo, taxa de desconto) — avaliadas da maior para a menor faixa
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))


def calcular_desconto(faturamento):
    return next((faturamento * taxa for limite, taxa in FAIXAS_DESCONTO if faturamento > limite), 0)


class RelatorioController:
    def __init__(self, pedidos):
        self._pedidos = pedidos

    def vendas(self):
        resumo = self._pedidos.resumo_vendas()
        faturamento = resumo["faturamento"]
        total_pedidos = resumo["total_pedidos"]
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": resumo["pendentes"],
            "pedidos_aprovados": resumo["aprovados"],
            "pedidos_cancelados": resumo["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
