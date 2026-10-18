"""Notificações (e-mail/SMS/push). Implementação atual apenas registra em log."""
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("Notificação de e-mail/SMS/push: pedido %s criado para usuário %s", pedido_id, usuario_id)

    def status_alterado(self, pedido_id, novo_status):
        logger.info("Notificação: pedido %s mudou para '%s'", pedido_id, novo_status)
