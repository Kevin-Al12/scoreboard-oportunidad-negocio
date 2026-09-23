from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.filtro_guardado import FiltroGuardado
from app.models.user import User
from app.schemas.filtro_guardado import FiltroGuardadoCreate, FiltroGuardadoOut

router = APIRouter(prefix="/filtros-guardados", tags=["filtros-guardados"])


@router.get("", response_model=list[FiltroGuardadoOut])
def listar_mis_filtros(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(FiltroGuardado)
        .filter(FiltroGuardado.user_id == usuario.id)
        .order_by(FiltroGuardado.creado_en.desc())
        .all()
    )


@router.post("", response_model=FiltroGuardadoOut, status_code=201)
def guardar_filtro(payload: FiltroGuardadoCreate, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filtro = FiltroGuardado(user_id=usuario.id, nombre=payload.nombre, params=payload.params)
    db.add(filtro)
    db.commit()
    db.refresh(filtro)
    return filtro


@router.delete("/{filtro_id}", status_code=204)
def eliminar_filtro(filtro_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filtro = db.get(FiltroGuardado, filtro_id)
    if not filtro or filtro.user_id != usuario.id:
        raise HTTPException(404, "Filtro no encontrado")
    db.delete(filtro)
    db.commit()
