from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreado, ApiKeyCreate, ApiKeyOut
from app.services.api_keys import generar_api_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def listar_mis_api_keys(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ApiKey).filter(ApiKey.user_id == usuario.id).order_by(ApiKey.creado_en.desc()).all()


@router.post("", response_model=ApiKeyCreado, status_code=201)
def crear_api_key(payload: ApiKeyCreate, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw_key, registro = generar_api_key(db, usuario, payload.nombre)
    return ApiKeyCreado(id=registro.id, nombre=registro.nombre, api_key=raw_key, prefijo=registro.prefijo)


@router.delete("/{api_key_id}", status_code=204)
def revocar_api_key(api_key_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    registro = db.get(ApiKey, api_key_id)
    if not registro or registro.user_id != usuario.id:
        raise HTTPException(404, "API key no encontrada")
    registro.revocada = True
    db.commit()
