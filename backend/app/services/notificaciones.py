"""Notificaciones multi-canal.

El registro in-app SIEMPRE se crea de inmediato (eso es lo que alimenta la
campanita en el frontend). Los canales externos (email, Slack) se despachan
en un BackgroundTask *después* de responder la petición -- antes se llamaban
en línea con hasta 5s de timeout cada uno, así que un comentario con 3
@menciones podía dejar al usuario esperando ~30s si el SMTP no respondía.

Los canales externos son adaptadores opcionales que se activan solo si sus
credenciales están configuradas:

- Email: requiere SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM en .env
  (global -- un solo mailbox del operador, no mezcla organizaciones porque
  cada email va a un destinatario específico, no a un canal compartido).
- Slack: requiere que la ORGANIZACIÓN tenga configurado su propio
  `slack_webhook_url` (ver PATCH /organizacion) -- un webhook global
  mandaría las notificaciones de todas las organizaciones al mismo canal.

Sin credenciales, los adaptadores no hacen nada (y lo dejan en el log) en
vez de fallar la operación que disparó la notificación.
"""

import logging
import smtplib
from email.message import EmailMessage

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import session as db_session
from app.models.notificacion import Notificacion
from app.models.organization import Organization
from app.schemas.organizacion import validar_webhook_slack

logger = logging.getLogger("scoreboard.notificaciones")
settings = get_settings()


def enviar_email_directo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.smtp_from):
        logger.info("Email no enviado (SMTP no configurado): %s -> %s", asunto, destinatario)
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = asunto
        msg["From"] = settings.smtp_from
        msg["To"] = destinatario
        msg.set_content(cuerpo)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Fallo enviando email a %s", destinatario)
        return False


def _enviar_slack(webhook_url: str, mensaje: str) -> bool:
    # Se re-valida justo antes de enviar: una URL guardada ANTES de que
    # existiera la validación (o escrita directo en la base) no debe poder
    # usarse para que el servidor haga peticiones a direcciones internas.
    try:
        validar_webhook_slack(webhook_url)
    except ValueError:
        logger.warning("Slack no enviado: el webhook guardado no es una URL válida de hooks.slack.com")
        return False
    try:
        # follow_redirects=False (explícito): una redirección desde Slack
        # no debe poder llevar la petición a otro host.
        r = httpx.post(webhook_url, json={"text": mensaje}, timeout=5, follow_redirects=False)
        r.raise_for_status()
        return True
    except Exception:
        logger.exception("Fallo enviando notificación a Slack")
        return False


def notificar(
    db: Session,
    user_id: int,
    tipo: str,
    mensaje: str,
    entidad_ref: str | None = None,
) -> Notificacion:
    """Crea el registro in-app de inmediato (rápido, local). No manda nada
    externo por sí sola -- para eso, encolar despachar_canales_externos()
    en un BackgroundTask desde el endpoint (ver evaluaciones.py/comentarios.py)."""
    registro = Notificacion(user_id=user_id, tipo=tipo, mensaje=mensaje, entidad_ref=entidad_ref)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def despachar_canales_externos(
    notificacion_id: int,
    organization_id: int,
    email_destinatario: str | None,
    asunto: str,
    mensaje: str,
) -> None:
    """Pensado para correr en un BackgroundTask, DESPUÉS de responder la
    petición. Abre su propia sesión de DB porque la del request ya se cerró
    para cuando esto corre. Se accede como `db_session.SessionLocal()` (en
    vez de un `from ... import SessionLocal` de nivel de módulo) para que
    los tests puedan sustituirla por la base de pruebas -- un test client
    ejecuta los BackgroundTasks dentro de la misma petición, así que si
    esto usara la sesión real de la app apuntaría a una base SQLite
    completamente distinta a la que usan los demás asserts del test."""
    db = db_session.SessionLocal()
    try:
        enviado_email = enviar_email_directo(email_destinatario, asunto, mensaje) if email_destinatario else False

        enviado_slack = False
        org = db.get(Organization, organization_id)
        if org and org.slack_webhook_url:
            enviado_slack = _enviar_slack(org.slack_webhook_url, f"[{asunto}] {mensaje}")
        elif org:
            logger.info("Slack no enviado (la organización %s no configuró slack_webhook_url)", org.nombre)

        notificacion = db.get(Notificacion, notificacion_id)
        if notificacion:
            notificacion.enviado_email = enviado_email
            notificacion.enviado_slack = enviado_slack
            db.commit()
    finally:
        db.close()
