from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import Role, User
from app.schemas.organizacion import OrganizacionOut, OrganizacionUpdate, enmascarar_webhook

router = APIRouter(prefix="/organizacion", tags=["organizacion"])


def _salida(org: Organization, usuario: User) -> OrganizacionOut:
    """Cualquier miembro ve si Slack está configurado; solo un admin ve la
    versión enmascarada. La URL completa no sale nunca de la API (antes
    cualquier viewer la recibía entera y podía publicar en el canal)."""
    return OrganizacionOut(
        id=org.id,
        nombre=org.nombre,
        creado_en=org.creado_en,
        slack_configurado=bool(org.slack_webhook_url),
        slack_webhook_mascara=enmascarar_webhook(org.slack_webhook_url) if usuario.role == Role.admin else None,
    )


@router.get("", response_model=OrganizacionOut)
def obtener_mi_organizacion(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _salida(db.get(Organization, usuario.organization_id), usuario)


@router.patch("", response_model=OrganizacionOut)
def actualizar_mi_organizacion(
    payload: OrganizacionUpdate, admin: User = Depends(require_role(Role.admin)), db: Session = Depends(get_db)
):
    org = db.get(Organization, admin.organization_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(org, campo, valor)
    db.commit()
    db.refresh(org)
    return _salida(org, admin)
