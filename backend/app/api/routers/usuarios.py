from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.auth import UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Miembros de mi organización — para asignar responsables o @mencionar en comentarios."""
    return db.query(User).filter(User.organization_id == usuario.organization_id).order_by(User.nombre_completo).all()


def _dejaria_la_organizacion_sin_admin(db: Session, admin_actual: User, objetivo: User, payload: UsuarioUpdate) -> bool:
    """True si este cambio bajaría a 0 el conteo de admins ACTIVOS de la organización.

    Cubre tanto degradar de rol como desactivar la cuenta -- las dos formas
    de dejar una organización sin nadie que pueda gestionarla.
    """
    quedaria_admin = (payload.role if payload.role is not None else objetivo.role) == Role.admin
    quedaria_activo = payload.activo if payload.activo is not None else objetivo.activo
    if quedaria_admin and quedaria_activo:
        return False  # objetivo sigue siendo admin activo, no hay problema

    if objetivo.role != Role.admin or not objetivo.activo:
        return False  # objetivo ya no contaba como admin activo de todos modos

    otros_admins_activos = (
        db.query(User)
        .filter(User.organization_id == admin_actual.organization_id, User.role == Role.admin, User.activo.is_(True), User.id != objetivo.id)
        .count()
    )
    return otros_admins_activos == 0


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    admin: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    """Promover/degradar rol o desactivar un usuario — solo admins de la misma organización."""
    objetivo = db.get(User, usuario_id)
    if not objetivo or objetivo.organization_id != admin.organization_id:
        raise HTTPException(404, "Usuario no encontrado en tu organización")

    if _dejaria_la_organizacion_sin_admin(db, admin, objetivo, payload):
        raise HTTPException(400, "Esto dejaría la organización sin ningún admin activo. Asigná otro admin primero.")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(objetivo, campo, valor)
    db.commit()
    db.refresh(objetivo)
    return objetivo
