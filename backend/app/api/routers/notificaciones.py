from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notificacion import Notificacion
from app.models.user import User
from app.schemas.notificacion import NotificacionOut

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("", response_model=list[NotificacionOut])
def listar_mis_notificaciones(
    solo_no_leidas: bool = False, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    query = db.query(Notificacion).filter(Notificacion.user_id == usuario.id)
    if solo_no_leidas:
        query = query.filter(Notificacion.leido.is_(False))
    return query.order_by(Notificacion.creado_en.desc()).limit(100).all()


@router.post("/{notificacion_id}/leer", response_model=NotificacionOut)
def marcar_leida(notificacion_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notificacion, notificacion_id)
    if not n or n.user_id != usuario.id:
        raise HTTPException(404, "Notificación no encontrada")
    n.leido = True
    db.commit()
    db.refresh(n)
    return n


@router.post("/leer-todas", status_code=204)
def marcar_todas_leidas(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notificacion).filter(Notificacion.user_id == usuario.id, Notificacion.leido.is_(False)).update(
        {"leido": True}
    )
    db.commit()
