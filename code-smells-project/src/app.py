"""Composition root: cria a aplicação, injeta dependências e registra rotas e middlewares."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.database import get_connection, init_db
from src.middlewares.error_handler import register_error_handlers
from src.models.admin_model import AdminModel
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.usuario_model import UsuarioModel
from src.services.notification_service import NotificationService
from src.views.pedido_routes import create_pedido_blueprint
from src.views.produto_routes import create_produto_blueprint
from src.views.relatorio_routes import create_relatorio_blueprint
from src.views.sistema_routes import create_sistema_blueprint
from src.views.usuario_routes import create_usuario_blueprint


def create_app(settings=Settings):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)

    init_db(app)

    produtos = ProdutoModel(get_connection)
    usuarios = UsuarioModel(get_connection)
    pedidos = PedidoModel(get_connection)
    admin = AdminModel(get_connection)

    app.register_blueprint(create_produto_blueprint(ProdutoController(produtos)))
    app.register_blueprint(create_usuario_blueprint(UsuarioController(usuarios)))
    app.register_blueprint(create_pedido_blueprint(PedidoController(pedidos, produtos, NotificationService())))
    app.register_blueprint(create_relatorio_blueprint(RelatorioController(pedidos)))
    app.register_blueprint(
        create_sistema_blueprint(SistemaController(produtos, usuarios, pedidos, admin, settings.APP_VERSION))
    )

    register_error_handlers(app)
    return app
