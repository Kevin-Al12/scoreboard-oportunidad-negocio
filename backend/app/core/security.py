"""Hashing de contraseñas y emisión/verificación de JWT.

Login real con email+contraseña, no un mock. Lo que NO está aquí es un
flujo de OAuth/SSO contra un proveedor real (Google, Microsoft, etc.) --
eso requiere credenciales de una app registrada en ese proveedor que no
existen en este entorno. El modelo User ya tiene columnas
`oauth_provider`/`oauth_subject` listas para conectar uno sin migrar el
esquema; ver README para cómo cablearlo con `authlib` cuando haya
credenciales reales.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def crear_access_token(user_id: int) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expira}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decodificar_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
