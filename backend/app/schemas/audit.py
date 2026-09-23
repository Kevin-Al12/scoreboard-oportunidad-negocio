from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    entidad: str
    entidad_id: int
    campo: str
    valor_anterior: str | None
    valor_nuevo: str | None
    revertido: bool
    creado_en: datetime
    revertible: bool = False
    usuario_nombre: str | None = None
