from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.criterio import Criterio
from app.models.user import Role, User
from app.schemas.criterio import CriterioCreate, CriterioOut, CriterioUpdate
from app.services.auditoria import registrar_cambios

router = APIRouter(prefix="/criterios", tags=["criterios"])


def _criterio_de_mi_org_o_404(db: Session, criterio_id: int, usuario: User) -> Criterio:
    criterio = db.get(Criterio, criterio_id)
    if not criterio or criterio.organization_id != usuario.organization_id:
        raise HTTPException(404, "Criterio no encontrado")
    return criterio


@router.get("", response_model=list[CriterioOut])
def listar_criterios(solo_activos: bool = False, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Criterio).filter(Criterio.organization_id == usuario.organization_id)
    if solo_activos:
        query = query.filter(Criterio.activo.is_(True))
    return query.order_by(Criterio.orden, Criterio.id).all()


@router.post("", response_model=CriterioOut, status_code=201)
def crear_criterio(
    payload: CriterioCreate,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    criterio = Criterio(organization_id=usuario.organization_id, **payload.model_dump())
    db.add(criterio)
    db.commit()
    db.refresh(criterio)
    return criterio


@router.get("/{criterio_id}", response_model=CriterioOut)
def obtener_criterio(criterio_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _criterio_de_mi_org_o_404(db, criterio_id, usuario)


@router.patch("/{criterio_id}", response_model=CriterioOut)
def actualizar_criterio(
    criterio_id: int,
    payload: CriterioUpdate,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    criterio = _criterio_de_mi_org_o_404(db, criterio_id, usuario)
    cambios = payload.model_dump(exclude_unset=True)
    # Los pesos y el estado activo/inactivo cambian el score de TODOS los
    # sectores retroactivamente -- son justo el tipo de cambio silencioso
    # que un audit log tiene que capturar.
    auditable = {
        campo: (getattr(criterio, campo), valor) for campo, valor in cambios.items() if campo in ("peso", "activo")
    }
    for campo, valor in cambios.items():
        setattr(criterio, campo, valor)
    db.commit()
    db.refresh(criterio)
    registrar_cambios(db, usuario.organization_id, usuario.id, "criterio", criterio.id, auditable)
    return criterio


@router.delete("/{criterio_id}", status_code=204)
def eliminar_criterio(
    criterio_id: int,
    usuario: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    criterio = _criterio_de_mi_org_o_404(db, criterio_id, usuario)
    db.delete(criterio)
    db.commit()
