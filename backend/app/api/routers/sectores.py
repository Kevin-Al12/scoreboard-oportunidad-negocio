from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_role
from app.core.scoring import ScoringError
from app.db.session import get_db
from app.models.criterio import Criterio
from app.models.sector import Sector
from app.models.user import Role, User
from app.schemas.sector import SectorConScore, SectorCreate, SectorOut, SectorUpdate
from app.services.auditoria import registrar_cambios
from app.services.scoring_service import calcular_score_de_ronda, obtener_criterios_activos, ultima_ronda_de

router = APIRouter(prefix="/sectores", tags=["sectores"])


def _sector_con_score(
    sector: Sector, criterios_activos: list[Criterio], usuarios_por_id: dict[int, str] | None = None
) -> SectorConScore:
    base = SectorConScore.model_validate(sector)
    if usuarios_por_id and sector.responsable_id:
        base.responsable_nombre = usuarios_por_id.get(sector.responsable_id)
    ronda = ultima_ronda_de(sector)
    if ronda is None:
        return base
    try:
        resultado = calcular_score_de_ronda(ronda, criterios_activos)
        base.score_0_a_100 = resultado.score_0_a_100
        base.score_1_a_5 = resultado.score_1_a_5
    except ScoringError:
        # Ronda incompleta respecto a los criterios activos actuales
        # (ej. se agregó un criterio nuevo después de evaluar el sector).
        # No se calcula el score, pero el sector se sigue listando.
        pass
    base.fecha_ultima_evaluacion = ronda.creado_en
    return base


def _sector_de_mi_org_o_404(db: Session, sector_id: int, usuario: User) -> Sector:
    sector = db.get(Sector, sector_id)
    if not sector or sector.organization_id != usuario.organization_id:
        raise HTTPException(404, "Sector no encontrado")
    return sector


def _validar_responsable_de_mi_org(db: Session, organization_id: int, responsable_id: int | None) -> None:
    """Sin esto, PATCH /sectores permitía apuntar responsable_id a un
    usuario de OTRA organización -- esa persona terminaba recibiendo
    notificaciones (y viendo, si además tuviera acceso al sector) datos que
    no le correspondían."""
    if responsable_id is None:
        return
    responsable = db.get(User, responsable_id)
    if not responsable or responsable.organization_id != organization_id:
        raise HTTPException(422, "El responsable debe ser un usuario de tu misma organización")


@router.get("", response_model=list[SectorConScore])
def listar_sectores(
    response: Response,
    responsable_id: int | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sin `limit`, devuelve todos los sectores de la organización (cómodo
    para los ~10-50 sectores de un uso típico). Con `limit`/`offset` pagina
    de verdad -- necesario cuando la lista crece a cientos -- y expone el
    total en el header `X-Total-Count` para que el frontend arme controles
    de página sin pedir todo de una vez.
    """
    query = db.query(Sector).filter(Sector.organization_id == usuario.organization_id)
    if responsable_id is not None:
        query = query.filter(Sector.responsable_id == responsable_id)

    response.headers["X-Total-Count"] = str(query.count())

    query = query.options(joinedload(Sector.rondas_evaluacion)).order_by(Sector.nombre).offset(offset)
    if limit is not None:
        query = query.limit(limit)

    sectores = query.all()
    # Se consulta UNA vez para toda la lista -- antes _sector_con_score volvía
    # a pedir los criterios activos por cada sector (N+1: 50 sectores = 50
    # queries idénticas).
    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    usuarios_por_id = {u.id: u.nombre_completo for u in db.query(User).filter(User.organization_id == usuario.organization_id)}
    return [_sector_con_score(s, criterios_activos, usuarios_por_id) for s in sectores]


@router.post("", response_model=SectorOut, status_code=201)
def crear_sector(
    payload: SectorCreate,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    _validar_responsable_de_mi_org(db, usuario.organization_id, payload.responsable_id)
    sector = Sector(organization_id=usuario.organization_id, creado_por_id=usuario.id, **payload.model_dump())
    db.add(sector)
    db.commit()
    db.refresh(sector)
    return sector


@router.get("/{sector_id}", response_model=SectorConScore)
def obtener_sector(sector_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sector = _sector_de_mi_org_o_404(db, sector_id, usuario)
    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    usuarios_por_id = {u.id: u.nombre_completo for u in db.query(User).filter(User.organization_id == usuario.organization_id)}
    return _sector_con_score(sector, criterios_activos, usuarios_por_id)


@router.patch("/{sector_id}", response_model=SectorOut)
def actualizar_sector(
    sector_id: int,
    payload: SectorUpdate,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    sector = _sector_de_mi_org_o_404(db, sector_id, usuario)
    cambios = payload.model_dump(exclude_unset=True)
    if "responsable_id" in cambios:
        _validar_responsable_de_mi_org(db, usuario.organization_id, cambios["responsable_id"])
    auditable = {
        campo: (getattr(sector, campo), valor)
        for campo, valor in cambios.items()
        if campo in ("responsable_id",)  # texto libre (notas, descripción) no se audita campo a campo
    }
    for campo, valor in cambios.items():
        setattr(sector, campo, valor)
    db.commit()
    db.refresh(sector)
    registrar_cambios(db, usuario.organization_id, usuario.id, "sector", sector.id, auditable)
    return sector


@router.delete("/{sector_id}", status_code=204)
def eliminar_sector(
    sector_id: int,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    sector = _sector_de_mi_org_o_404(db, sector_id, usuario)
    db.delete(sector)
    db.commit()
