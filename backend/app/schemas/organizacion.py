import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Solo se aceptan webhooks entrantes reales de Slack. Antes se aceptaba
# cualquier URL, y como el servidor le hace un POST a esa URL cada vez que
# hay una notificación, un admin podía apuntarla a servicios internos
# (http://127.0.0.1:..., la metadata de la nube en 169.254.169.254, etc.):
# un SSRF clásico. Con https + host exacto + path de webhook eso ya no es posible.
_HOST_SLACK = "hooks.slack.com"
_PATH_WEBHOOK = re.compile(r"^/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+$")


def validar_webhook_slack(url: str) -> str:
    url = url.strip()
    partes = urlparse(url)
    if (
        partes.scheme != "https"
        or partes.hostname != _HOST_SLACK
        or partes.port not in (None, 443)
        or partes.username
        or partes.password
        or partes.query
        or partes.fragment
        or not _PATH_WEBHOOK.match(partes.path)
    ):
        raise ValueError("Debe ser un webhook entrante de Slack: https://hooks.slack.com/services/XXX/YYY/ZZZ")
    return url


def enmascarar_webhook(url: str | None) -> str | None:
    """La URL del webhook funciona como contraseña (quien la tenga puede
    publicar en el canal), así que la API nunca la devuelve completa."""
    if not url:
        return None
    return f"https://{_HOST_SLACK}/services/…{url[-4:]}"


class OrganizacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slack_configurado: bool = False
    # Solo para admins, y enmascarada. Nunca la URL completa.
    slack_webhook_mascara: str | None = None
    creado_en: datetime


class OrganizacionUpdate(BaseModel):
    # null -> quita el webhook
    slack_webhook_url: str | None = Field(default=None, max_length=500)

    @field_validator("slack_webhook_url")
    @classmethod
    def _validar(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return validar_webhook_slack(v)
