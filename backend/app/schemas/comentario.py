from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComentarioCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class ComentarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sector_id: int
    user_id: int
    autor_nombre: str = ""
    texto: str
    menciones_user_ids: list[int]
    creado_en: datetime
