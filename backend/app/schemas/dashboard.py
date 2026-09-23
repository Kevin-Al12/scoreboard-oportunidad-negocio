from datetime import date

from pydantic import BaseModel

from app.schemas.evaluacion import DetalleCriterioScore


class PuntoHistorico(BaseModel):
    ronda_id: int
    fecha: date
    score_0_a_100: float
    score_1_a_5: float


class HistoricoSector(BaseModel):
    sector_id: int
    sector_nombre: str
    puntos: list[PuntoHistorico]


class RadarSector(BaseModel):
    sector_id: int
    sector_nombre: str
    fecha: date
    detalle: list[DetalleCriterioScore]
