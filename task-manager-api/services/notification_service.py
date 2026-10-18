"""Envio de notificações por e-mail. Configurado por injeção; desabilitado se não houver SMTP configurado."""
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, host=None, port=587, user=None, password=None):
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    @classmethod
    def from_settings(cls, settings):
        return cls(settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASSWORD)

    @property
    def enabled(self):
        return bool(self._host and self._user and self._password)

    def send_email(self, to, subject, body):
        if not self.enabled:
            logger.info("SMTP não configurado — e-mail para %s não enviado (%s)", to, subject)
            return False
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self._user, to, subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.send_message(message)
            logger.info("E-mail enviado para %s", to)
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception("Falha ao enviar e-mail para %s", to)
            return False

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        return self.send_email(user.email, subject, body)

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        return self.send_email(user.email, subject, body)
