from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import Role
from app.schemas.auth import EmailNormalizado


class InvitacionCreate(BaseModel):
    email: EmailNormalizado
    role: Role = Role.viewer


class InvitacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    token: str
    usada: bool
    creado_en: datetime
    expira_en: datetime
