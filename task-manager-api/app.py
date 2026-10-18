"""Composition root e ponto de entrada (python app.py)."""
import logging
from datetime import datetime

from flask import Flask
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer

from config.settings import Settings
from controllers.category_controller import CategoryController
from controllers.report_controller import ReportController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import create_category_blueprint
from routes.report_routes import create_report_blueprint
from routes.task_routes import create_task_blueprint
from routes.user_routes import create_user_blueprint
from services.notification_service import NotificationService


def create_app(settings=Settings):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)

    token_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="auth-token")
    notifications = NotificationService.from_settings(settings)

    app.register_blueprint(create_task_blueprint(TaskController(notifications)))
    app.register_blueprint(create_user_blueprint(UserController(token_signer)))
    app.register_blueprint(create_report_blueprint(ReportController()))
    app.register_blueprint(create_category_blueprint(CategoryController()))

    @app.get("/health")
    def health():
        return {"status": "ok", "timestamp": str(datetime.now())}

    @app.get("/")
    def index():
        return {"message": "Task Manager API", "version": settings.APP_VERSION}

    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
