from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_role
from app.core.scoring import ScoringError
from app.db.session import get_db
from app.models.criterio import Criterio
from app.models.evaluacion import Evaluacion, RondaEvaluacion
from app.models.sector import Sector
from app.models.user import Role, User
from app.schemas.evaluacion import DetalleCriterioScore, RondaConScore, RondaEvaluacionCreate, RondaEvaluacionOut
from app.services.notificaciones import despachar_canales_externos, notificar
from app.services.scoring_service import calcular_score_de_ronda, obtener_criterios_activos, ultima_ronda_de

router = APIRouter(prefix="/sectores/{sector_id}/rondas", tags=["evaluaciones"])

UMBRAL_OPORTUNIDAD = 70


def _get_sector_o_404(sector_id: int, usuario: User, db: Session) -> Sector:
    sector = db.get(Sector, sector_id)
    if not sector or sector.organization_id != usuario.organization_id:
        raise HTTPException(404, "Sector no encontrado")
    return sector


def _resultado_de(ronda: RondaEvaluacion, criterios_activos: list[Criterio]):
    """Sin tocar la DB -- calcular_score_de_ronda solo lee la lista en
    memoria `ronda.evaluaciones`, así que esto sirve tanto para VALIDAR
    antes de guardar como para responder después de guardar."""
    return calcular_score_de_ronda(ronda, criterios_activos)


def _ronda_con_score(ronda: RondaEvaluacion, organization_id: int, db: Session) -> RondaConScore:
    criterios_activos = obtener_criterios_activos(db, organization_id)
    try:
        resultado = _resultado_de(ronda, criterios_activos)
    except ScoringError as e:
        raise HTTPException(422, str(e)) from e

    return RondaConScore(
        **RondaEvaluacionOut.model_validate(ronda).model_dump(),
        score_1_a_5=resultado.score_1_a_5,
        score_0_a_100=resultado.score_0_a_100,
        resumen=resultado.resumen_texto(),
        detalle=[DetalleCriterioScore(**d.__dict__) for d in resultado.detalle],
    )


@router.get("", response_model=list[RondaEvaluacionOut])
def listar_rondas(sector_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_sector_o_404(sector_id, usuario, db)
    return (
        db.query(RondaEvaluacion)
        .options(joinedload(RondaEvaluacion.evaluaciones).joinedload(Evaluacion.criterio))
        .filter(RondaEvaluacion.sector_id == sector_id)
        .order_by(RondaEvaluacion.fecha.desc(), RondaEvaluacion.id.desc())
        .all()
    )


@router.post("", response_model=RondaConScore, status_code=201)
def crear_ronda(
    sector_id: int,
    payload: RondaEvaluacionCreate,
    background_tasks: BackgroundTasks,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    """Registra una nueva evaluación completa del sector en una fecha.

    Crear una ronda nueva (en vez de sobrescribir la anterior) es lo que
    permite el histórico: comparar cómo cambió el score de un sector entre
    una evaluación y otra.
    """
    sector = _get_sector_o_404(sector_id, usuario, db)
    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)

    score_previo = None
    ronda_previa = ultima_ronda_de(sector)
    if ronda_previa is not None:
        try:
            score_previo = _resultado_de(ronda_previa, criterios_activos).score_0_a_100
        except ScoringError:
            pass

    ids_criterios = {c.criterio_id for c in payload.calificaciones}
    if len(ids_criterios) != len(payload.calificaciones):
        raise HTTPException(422, "Hay calificaciones duplicadas para el mismo criterio en el payload")

    criterios_existentes = (
        db.query(Criterio.id)
        .filter(Criterio.id.in_(ids_criterios), Criterio.organization_id == usuario.organization_id)
        .all()
    )
    ids_existentes = {c.id for c in criterios_existentes}
    ids_desconocidos = ids_criterios - ids_existentes
    if ids_desconocidos:
        raise HTTPException(422, f"Criterios inexistentes: {sorted(ids_desconocidos)}")

    ronda = RondaEvaluacion(
        sector_id=sector_id,
        fecha=payload.fecha or date.today(),
        notas=payload.notas,
        creado_por_id=usuario.id,
    )
    for c in payload.calificaciones:
        ronda.evaluaciones.append(
            Evaluacion(criterio_id=c.criterio_id, calificacion=c.calificacion, notas=c.notas)
        )

    # VALIDAR antes de guardar nada: calcular_score_de_ronda solo lee la
    # lista en memoria de arriba, no hace falta tocar la DB para saber si
    # la ronda queda completa respecto a los criterios activos. Antes esto
    # se validaba DESPUÉS del commit -- una ronda incompleta (422) igual
    # quedaba guardada como "la última" del sector, que por lo tanto
    # desaparecía del ranking sin ningún aviso.
    try:
        resultado = _resultado_de(ronda, criterios_activos)
    except ScoringError as e:
        raise HTTPException(422, str(e)) from e

    db.add(ronda)
    db.commit()
    db.refresh(ronda)

    # Notificación real disparada por evento: si el sector ACABA de cruzar
    # el umbral de oportunidad (no lo cumplía antes y ahora sí), se avisa a
    # su responsable. El registro in-app se crea ya mismo; email/Slack se
    # despachan en background (ver notificaciones.py) para no bloquear esta
    # respuesta con el timeout de un SMTP lento.
    cruzo_umbral_ahora = (
        resultado.score_0_a_100 >= UMBRAL_OPORTUNIDAD and (score_previo is None or score_previo < UMBRAL_OPORTUNIDAD)
    )
    if cruzo_umbral_ahora and sector.responsable_id:
        responsable = db.get(User, sector.responsable_id)
        if responsable:
            mensaje = f"'{sector.nombre}' alcanzó {resultado.score_0_a_100:.1f}/100 — cruzó el umbral de oportunidad"
            registro = notificar(
                db, user_id=responsable.id, tipo="umbral_oportunidad", mensaje=mensaje, entidad_ref=f"sector:{sector.id}"
            )
            background_tasks.add_task(
                despachar_canales_externos,
                registro.id,
                usuario.organization_id,
                responsable.email,
                "umbral_oportunidad",
                mensaje,
            )

    return RondaConScore(
        **RondaEvaluacionOut.model_validate(ronda).model_dump(),
        score_1_a_5=resultado.score_1_a_5,
        score_0_a_100=resultado.score_0_a_100,
        resumen=resultado.resumen_texto(),
        detalle=[DetalleCriterioScore(**d.__dict__) for d in resultado.detalle],
    )


@router.get("/{ronda_id}", response_model=RondaConScore)
def obtener_ronda(sector_id: int, ronda_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_sector_o_404(sector_id, usuario, db)
    ronda = (
        db.query(RondaEvaluacion)
        .options(joinedload(RondaEvaluacion.evaluaciones).joinedload(Evaluacion.criterio))
        .filter(RondaEvaluacion.id == ronda_id, RondaEvaluacion.sector_id == sector_id)
        .first()
    )
    if not ronda:
        raise HTTPException(404, "Ronda de evaluación no encontrada")
    return _ronda_con_score(ronda, usuario.organization_id, db)


@router.delete("/{ronda_id}", status_code=204)
def eliminar_ronda(
    sector_id: int,
    ronda_id: int,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    _get_sector_o_404(sector_id, usuario, db)
    ronda = db.query(RondaEvaluacion).filter(
        RondaEvaluacion.id == ronda_id, RondaEvaluacion.sector_id == sector_id
    ).first()
    if not ronda:
        raise HTTPException(404, "Ronda de evaluación no encontrada")
    db.delete(ronda)
    db.commit()
