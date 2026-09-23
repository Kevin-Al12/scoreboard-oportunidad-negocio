from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.criterio import CriterioOut


class CalificacionInput(BaseModel):
    """Una calificación dentro del payload para crear/actualizar una ronda."""

    criterio_id: int
    calificacion: int = Field(ge=1, le=5)
    notas: str = ""


class RondaEvaluacionCreate(BaseModel):
    fecha: date | None = None
    notas: str = ""
    calificaciones: list[CalificacionInput]


class EvaluacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criterio_id: int
    calificacion: int
    notas: str
    criterio: CriterioOut | None = None


class RondaEvaluacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sector_id: int
    fecha: date
    notas: str
    creado_en: datetime
    evaluaciones: list[EvaluacionOut] = []


class DetalleCriterioScore(BaseModel):
    criterio_id: int
    criterio_nombre: str
    valor: int
    peso_normalizado: float
    contribucion: float


class RondaConScore(RondaEvaluacionOut):
    score_1_a_5: float
    score_0_a_100: float
    resumen: str
    detalle: list[DetalleCriterioScore]
