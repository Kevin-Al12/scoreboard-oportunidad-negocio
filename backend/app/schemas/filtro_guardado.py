import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Un filtro guardado son unos pocos parámetros de query (min_score,
# criterio_id...). Sin tope se aceptaba un `params` de varios MB por
# petición, que se guardaba tal cual en la base.
MAX_BYTES_PARAMS = 4 * 1024
MAX_CLAVES_PARAMS = 30


class FiltroGuardadoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    params: dict

    @field_validator("params")
    @classmethod
    def _limitar_tamano(cls, v: dict) -> dict:
        if len(v) > MAX_CLAVES_PARAMS:
            raise ValueError(f"Máximo {MAX_CLAVES_PARAMS} parámetros por filtro")
        if len(json.dumps(v, ensure_ascii=False).encode("utf-8")) > MAX_BYTES_PARAMS:
            raise ValueError(f"Los parámetros del filtro no pueden superar {MAX_BYTES_PARAMS // 1024} KB")
        return v


class FiltroGuardadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    params: dict
    creado_en: datetime
