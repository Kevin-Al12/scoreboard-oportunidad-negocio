from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routers.invitaciones import validar_y_consumir_invitacion
from app.core.rate_limit import limitar_por_ip
from app.core.security import crear_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import Role, User
from app.schemas.auth import LoginInput, RegistroInput, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=TokenOut, status_code=201, dependencies=[Depends(limitar_por_ip)])
def registrar(payload: RegistroInput, db: Session = Depends(get_db)):
    """Dos caminos, sin punto medio ambiguo:

    1. `token` de una invitación real -> te unes a ESA organización con el
       rol que el admin te asignó.
    2. `organizacion_nombre` de una organización que NO existe todavía ->
       la crea y quedas de admin.

    Ya NO existe un tercer camino de "escribe el nombre de una organización
    que ya existe y entras como viewer" -- eso permitía que cualquiera que
    supiera el nombre de una empresa viera sus sectores, notas y
    comentarios con solo registrarse.
    """
    # func.lower: por si quedan cuentas viejas guardadas con mayúsculas.
    if db.query(User).filter(func.lower(User.email) == payload.email).first():
        raise HTTPException(409, "Ya existe una cuenta con ese email")

    if payload.token:
        invitacion = validar_y_consumir_invitacion(db, payload.token, payload.email)
        organization_id = invitacion.organization_id
        role = invitacion.role
    else:
        if not payload.organizacion_nombre:
            raise HTTPException(422, "Falta organizacion_nombre (para crear una) o token (para unirte a una existente)")
        if db.query(Organization).filter(Organization.nombre == payload.organizacion_nombre).first():
            raise HTTPException(
                409,
                "Ya existe una organización con ese nombre. Pide una invitación a un administrador de esa "
                "organización en vez de registrarte con su nombre.",
            )
        org = Organization(nombre=payload.organizacion_nombre)
        db.add(org)
        db.flush()  # obtiene org.id sin confirmar todavía: org + usuario se guardan juntos o nada
        organization_id = org.id
        role = Role.admin

    usuario = User(
        organization_id=organization_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nombre_completo=payload.nombre_completo,
        role=role,
    )
    db.add(usuario)
    try:
        # UN solo commit para todo: organización nueva o invitación marcada
        # como usada + el usuario. Antes la invitación se marcaba como usada
        # (commit) ANTES de crear el usuario; si eso fallaba, el código
        # quedaba quemado sin cuenta creada.
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una cuenta con ese email o una organización con ese nombre")
    db.refresh(usuario)

    return TokenOut(access_token=crear_access_token(usuario.id))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limitar_por_ip)])
def login(payload: LoginInput, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(func.lower(User.email) == payload.email).first()
    if not usuario or not verify_password(payload.password, usuario.hashed_password):
        raise HTTPException(401, "Email o contraseña incorrectos")
    if not usuario.activo:
        raise HTTPException(403, "Esta cuenta está desactivada")
    return TokenOut(access_token=crear_access_token(usuario.id))


@router.get("/me", response_model=UsuarioOut)
def me(usuario: User = Depends(get_current_user)):
    return usuario
