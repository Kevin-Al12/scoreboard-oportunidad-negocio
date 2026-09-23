from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role

# Emails siempre en minúsculas: sin esto, "a@x.com" y "A@x.com" eran dos
# cuentas distintas (y un login con otra capitalización fallaba).
EmailNormalizado = Annotated[EmailStr, AfterValidator(lambda v: v.strip().lower())]


class RegistroInput(BaseModel):
    email: EmailNormalizado
    password: str = Field(min_length=8, max_length=72)
    nombre_completo: str = Field(min_length=1, max_length=200)
    # Para crear una organización nueva (quedas de admin): manda organizacion_nombre.
    # Para unirte a una que ya existe: manda el token que te dio un admin de esa
    # organización (ver POST /invitaciones) -- ya no basta con saber su nombre.
    organizacion_nombre: str | None = Field(default=None, min_length=1, max_length=200)
    token: str | None = None


class LoginInput(BaseModel):
    email: EmailNormalizado
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre_completo: str
    role: Role
    organization_id: int
    activo: bool
    creado_en: datetime


class UsuarioUpdate(BaseModel):
    role: Role | None = None
    activo: bool | None = None
