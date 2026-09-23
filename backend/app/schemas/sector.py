from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Los max_length calzan con las columnas String(200) del modelo -- sin
# esto, Pydantic dejaba pasar un nombre de 10 000 caracteres y Postgres
# tiraba un 500 crudo al intentar guardarlo (SQLite es más permisivo y no
# lo hubiera notado, así que esto solo se veía en producción).
class SectorBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(default="", max_length=4000)
    notas: str = Field(default="", max_length=4000)
    fuentes_informacion: str = Field(default="", max_length=2000)


class SectorCreate(SectorBase):
    responsable_id: int | None = None


class SectorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=4000)
    notas: str | None = Field(default=None, max_length=4000)
    fuentes_informacion: str | None = Field(default=None, max_length=2000)
    responsable_id: int | None = None


class SectorOut(SectorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    creado_por_id: int | None
    responsable_id: int | None
    fecha_creacion: datetime


class SectorConScore(SectorOut):
    """Sector + score de su última ronda de evaluación (o None si nunca fue evaluado)."""

    score_0_a_100: float | None = None
    score_1_a_5: float | None = None
    fecha_ultima_evaluacion: datetime | None = None
    responsable_nombre: str | None = None
