from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.invitacion import Invitacion
from app.models.organization import Organization
from app.models.user import Role, User
from app.schemas.invitacion import InvitacionCreate, InvitacionOut
from app.services.notificaciones import enviar_email_directo

router = APIRouter(prefix="/invitaciones", tags=["invitaciones"])


@router.get("", response_model=list[InvitacionOut])
def listar_invitaciones(admin: User = Depends(require_role(Role.admin)), db: Session = Depends(get_db)):
    return (
        db.query(Invitacion)
        .filter(Invitacion.organization_id == admin.organization_id)
        .order_by(Invitacion.creado_en.desc())
        .all()
    )


@router.post("", response_model=InvitacionOut, status_code=201)
def crear_invitacion(
    payload: InvitacionCreate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(func.lower(User.email) == payload.email).first():
        raise HTTPException(409, "Ya existe una cuenta con ese email")

    invitacion = Invitacion(
        organization_id=admin.organization_id,
        email=payload.email,
        role=payload.role,
        creado_por_id=admin.id,
    )
    db.add(invitacion)
    db.commit()
    db.refresh(invitacion)

    # El link de invitación se muestra siempre en la UI del admin (para que
    # la feature funcione sin SMTP); si hay credenciales configuradas,
    # además se manda por email. Ver notificaciones.py -- mismo patrón que
    # el resto de la app: nunca falla la operación por falta de SMTP.
    org = db.get(Organization, admin.organization_id)
    background_tasks.add_task(
        enviar_email_directo,
        payload.email,
        f"Invitación a {org.nombre} en el Scoreboard de Oportunidad",
        f"{admin.nombre_completo} te invitó a unirte a {org.nombre} en el Scoreboard de Oportunidad de Negocio.\n"
        f"Usa este código al registrarte: {invitacion.token}",
    )

    return invitacion


@router.delete("/{invitacion_id}", status_code=204)
def revocar_invitacion(invitacion_id: int, admin: User = Depends(require_role(Role.admin)), db: Session = Depends(get_db)):
    inv = db.get(Invitacion, invitacion_id)
    if not inv or inv.organization_id != admin.organization_id:
        raise HTTPException(404, "Invitación no encontrada")
    db.delete(inv)
    db.commit()


def _como_utc(dt: datetime) -> datetime:
    """SQLite no guarda de verdad la zona horaria (a diferencia de Postgres
    con TIMESTAMPTZ): un DateTime(timezone=True) vuelve "naive" al releerlo
    ahí. Se asume UTC en ese caso -- es lo único que esta app escribe --
    para que la comparación de abajo no reviente con
    "can't compare offset-naive and offset-aware datetimes"."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def validar_y_consumir_invitacion(db: Session, token: str, email: str) -> Invitacion:
    inv = db.query(Invitacion).filter(Invitacion.token == token).first()
    if not inv:
        raise HTTPException(404, "Código de invitación inválido")
    if inv.usada:
        raise HTTPException(410, "Este código de invitación ya fue usado")
    if _como_utc(inv.expira_en) < datetime.now(timezone.utc):
        raise HTTPException(410, "Este código de invitación expiró")
    if inv.email.lower() != email.lower():
        raise HTTPException(403, "Este código de invitación es para otro email")
    # Sin commit aquí: /auth/registro confirma la invitación usada y el
    # usuario nuevo en una sola transacción (si falla crear el usuario, la
    # invitación sigue disponible).
    inv.usada = True
    return inv
