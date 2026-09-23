from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.scoring import ScoringError
from app.db.session import get_db
from app.models.evaluacion import Evaluacion, RondaEvaluacion
from app.models.sector import Sector
from app.models.user import User
from app.schemas.dashboard import HistoricoSector, PuntoHistorico, RadarSector
from app.schemas.evaluacion import DetalleCriterioScore
from app.schemas.sector import SectorConScore
from app.services.scoring_service import calcular_score_de_ronda, obtener_criterios_activos, ultima_ronda_de

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/ranking", response_model=list[SectorConScore])
def ranking(
    min_score: float | None = Query(default=None, ge=0, le=100),
    max_score: float | None = Query(default=None, ge=0, le=100),
    criterio_id: int | None = None,
    min_calificacion: int | None = Query(default=None, ge=1, le=5),
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ranking de sectores por score, con filtros opcionales.

    - min_score/max_score: filtran por el score final ponderado (0-100).
    - criterio_id + min_calificacion: filtran a sectores cuya última
      evaluación calificó ese criterio específico con al menos ese valor
      (ej. "solo sectores con capital requerido bajo", si ese criterio
      tiene calificación >= 4 = favorable).
    """
    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    sectores = (
        db.query(Sector)
        .filter(Sector.organization_id == usuario.organization_id)
        .options(joinedload(Sector.rondas_evaluacion).joinedload(RondaEvaluacion.evaluaciones))
        .all()
    )

    resultado: list[SectorConScore] = []
    for sector in sectores:
        ronda = ultima_ronda_de(sector)
        item = SectorConScore.model_validate(sector)
        if ronda is None:
            continue  # sin evaluación no entra al ranking

        if criterio_id is not None:
            calificacion_criterio = next(
                (e.calificacion for e in ronda.evaluaciones if e.criterio_id == criterio_id), None
            )
            if calificacion_criterio is None:
                continue
            if min_calificacion is not None and calificacion_criterio < min_calificacion:
                continue

        try:
            score = calcular_score_de_ronda(ronda, criterios_activos)
        except ScoringError:
            continue

        if min_score is not None and score.score_0_a_100 < min_score:
            continue
        if max_score is not None and score.score_0_a_100 > max_score:
            continue

        item.score_0_a_100 = score.score_0_a_100
        item.score_1_a_5 = score.score_1_a_5
        item.fecha_ultima_evaluacion = ronda.creado_en
        resultado.append(item)

    resultado.sort(key=lambda s: s.score_0_a_100 or 0, reverse=True)
    return resultado


@router.get("/sectores/{sector_id}/radar", response_model=RadarSector)
def radar_de_sector(sector_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Detalle por criterio de la última evaluación de un sector, para graficar en radar."""
    sector = db.get(Sector, sector_id)
    if not sector or sector.organization_id != usuario.organization_id:
        raise HTTPException(404, "Sector no encontrado")

    ronda = ultima_ronda_de(sector)
    if ronda is None:
        raise HTTPException(404, "El sector todavía no tiene ninguna evaluación registrada")

    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    try:
        resultado = calcular_score_de_ronda(ronda, criterios_activos)
    except ScoringError as e:
        raise HTTPException(422, str(e)) from e

    return RadarSector(
        sector_id=sector.id,
        sector_nombre=sector.nombre,
        fecha=ronda.fecha,
        detalle=[DetalleCriterioScore(**d.__dict__) for d in resultado.detalle],
    )


@router.get("/sectores/{sector_id}/historico", response_model=HistoricoSector)
def historico_de_sector(sector_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Evolución del score de un sector a través de sus distintas rondas de evaluación."""
    sector = (
        db.query(Sector)
        .options(joinedload(Sector.rondas_evaluacion).joinedload(RondaEvaluacion.evaluaciones))
        .filter(Sector.id == sector_id)
        .first()
    )
    if not sector or sector.organization_id != usuario.organization_id:
        raise HTTPException(404, "Sector no encontrado")

    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    puntos = []
    for ronda in sorted(sector.rondas_evaluacion, key=lambda r: (r.fecha, r.id)):
        try:
            resultado = calcular_score_de_ronda(ronda, criterios_activos)
        except ScoringError:
            continue
        puntos.append(
            PuntoHistorico(
                ronda_id=ronda.id,
                fecha=ronda.fecha,
                score_0_a_100=resultado.score_0_a_100,
                score_1_a_5=resultado.score_1_a_5,
            )
        )

    return HistoricoSector(sector_id=sector.id, sector_nombre=sector.nombre, puntos=puntos)
