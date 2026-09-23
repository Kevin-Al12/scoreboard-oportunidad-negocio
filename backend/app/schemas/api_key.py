from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class ApiKeyCreado(BaseModel):
    """Única vez que se devuelve la clave en texto plano."""

    id: int
    nombre: str
    api_key: str
    prefijo: str


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    prefijo: str
    revocada: bool
    creado_en: datetime
    ultimo_uso_en: datetime | None
