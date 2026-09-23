from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    mensaje: str
    entidad_ref: str | None
    leido: bool
    enviado_email: bool
    enviado_slack: bool
    creado_en: datetime
