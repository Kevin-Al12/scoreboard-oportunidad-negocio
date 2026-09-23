from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_access_token
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import Role, User
from app.services.api_keys import verificar_api_key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User:
    """Autentica por JWT de sesión (frontend) o por API key (integraciones).

    Cualquiera de los dos habilita el acceso; sin ninguno, 401.
    """
    if token:
        user_id = decodificar_access_token(token)
        if user_id is None:
            raise HTTPException(401, "Token inválido o expirado")
        user = db.get(User, user_id)
        if not user or not user.activo:
            raise HTTPException(401, "Usuario inválido")
        return user

    if api_key:
        user = verificar_api_key(db, api_key)
        if not user:
            raise HTTPException(401, "API key inválida o revocada")
        return user

    raise HTTPException(401, "No autenticado — falta token o X-API-Key")


def require_role(*roles: Role):
    """Dependencia de permisos: admin siempre pasa; el resto debe estar en `roles`.

    Ej. Depends(require_role(Role.admin, Role.editor)) deja fuera a viewer.
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role == Role.admin:
            return user
        if user.role not in roles:
            raise HTTPException(403, f"Esta acción requiere rol {[r.value for r in roles]}, tienes '{user.role.value}'")
        return user

    return checker
