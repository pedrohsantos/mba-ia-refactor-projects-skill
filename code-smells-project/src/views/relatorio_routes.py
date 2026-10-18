from flask import Blueprint, jsonify


def create_relatorio_blueprint(controller):
    bp = Blueprint("relatorios", __name__)

    @bp.get("/relatorios/vendas")
    def relatorio_vendas():
        return jsonify({"dados": controller.vendas(), "sucesso": True}), 200

    return bp
