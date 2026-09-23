"""Generación y verificación de API keys para la API pública.

Se guarda solo el hash SHA-256 (una API key ya es un token aleatorio de
alta entropía, a diferencia de una contraseña elegida por una persona, así
que un hash rápido es la práctica estándar aquí — GitHub y Stripe hacen lo
mismo). La clave en texto plano se devuelve una única vez, al crearla.
"""

import hashlib
import secrets

from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.user import User

PREFIJO_VISIBLE = 10


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generar_api_key(db: Session, user: User, nombre: str) -> tuple[str, ApiKey]:
    raw_key = "sbk_" + secrets.token_urlsafe(32)
    registro = ApiKey(
        user_id=user.id,
        nombre=nombre,
        prefijo=raw_key[:PREFIJO_VISIBLE],
        key_hash=_hash(raw_key),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return raw_key, registro


def verificar_api_key(db: Session, raw_key: str) -> User | None:
    registro = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == _hash(raw_key), ApiKey.revocada.is_(False))
        .first()
    )
    if not registro:
        return None

    usuario = db.get(User, registro.user_id)
    # Si desactivaste a alguien, sus API keys tienen que dejar de servir de
    # inmediato -- antes esto no se chequeaba, así que una cuenta
    # desactivada seguía teniendo acceso completo vía su API key.
    if not usuario or not usuario.activo:
        return None

    from datetime import datetime, timezone

    registro.ultimo_uso_en = datetime.now(timezone.utc)
    db.commit()
    return usuario
