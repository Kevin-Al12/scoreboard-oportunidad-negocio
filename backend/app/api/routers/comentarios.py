import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.comentario import Comentario
from app.models.sector import Sector
from app.models.user import User
from app.schemas.comentario import ComentarioCreate, ComentarioOut
from app.services.notificaciones import despachar_canales_externos, notificar

router = APIRouter(prefix="/sectores/{sector_id}/comentarios", tags=["comentarios"])

PATRON_MENCION = re.compile(r"@([\w.\-]+@[\w.\-]+|\w+)")


def _sector_de_mi_org(db: Session, sector_id: int, usuario: User) -> Sector:
    sector = db.get(Sector, sector_id)
    if not sector or sector.organization_id != usuario.organization_id:
        raise HTTPException(404, "Sector no encontrado")
    return sector


def _extraer_menciones(db: Session, texto: str, organization_id: int) -> list[int]:
    """Convierte @email o @nombre en ids de usuarios de la misma organización."""
    candidatos = PATRON_MENCION.findall(texto)
    if not candidatos:
        return []
    compañeros = db.query(User).filter(User.organization_id == organization_id).all()
    ids = set()
    for c in candidatos:
        for u in compañeros:
            if u.email.lower() == c.lower() or u.nombre_completo.split(" ")[0].lower() == c.lower():
                ids.add(u.id)
    return sorted(ids)


def _con_autor(db: Session, c: Comentario) -> ComentarioOut:
    autor = db.get(User, c.user_id)
    salida = ComentarioOut.model_validate(c)
    salida.autor_nombre = autor.nombre_completo if autor else "—"
    return salida


@router.get("", response_model=list[ComentarioOut])
def listar_comentarios(sector_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _sector_de_mi_org(db, sector_id, usuario)
    filas = (
        db.query(Comentario)
        .filter(Comentario.sector_id == sector_id)
        .order_by(Comentario.creado_en.asc())
        .all()
    )
    return [_con_autor(db, c) for c in filas]


@router.post("", response_model=ComentarioOut, status_code=201)
def crear_comentario(
    sector_id: int,
    payload: ComentarioCreate,
    background_tasks: BackgroundTasks,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sector = _sector_de_mi_org(db, sector_id, usuario)
    menciones = _extraer_menciones(db, payload.texto, usuario.organization_id)

    comentario = Comentario(
        sector_id=sector_id, user_id=usuario.id, texto=payload.texto, menciones_user_ids=menciones
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)

    for mencionado_id in menciones:
        if mencionado_id == usuario.id:
            continue
        mencionado = db.get(User, mencionado_id)
        if not mencionado:
            continue
        registro = notificar(
            db,
            user_id=mencionado_id,
            tipo="mencion",
            mensaje=f"{usuario.nombre_completo} te mencionó en un comentario sobre '{sector.nombre}'",
            entidad_ref=f"sector:{sector_id}",
        )
        # Email/Slack se despachan DESPUÉS de responder -- antes se llamaban
        # en línea con hasta 5s de timeout cada uno, así que 3 menciones en
        # un comentario podían dejar al usuario esperando ~30s.
        background_tasks.add_task(
            despachar_canales_externos,
            registro.id,
            usuario.organization_id,
            mencionado.email,
            "mencion",
            registro.mensaje,
        )

    return _con_autor(db, comentario)


@router.delete("/{comentario_id}", status_code=204)
def eliminar_comentario(
    sector_id: int, comentario_id: int, usuario: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _sector_de_mi_org(db, sector_id, usuario)
    comentario = db.get(Comentario, comentario_id)
    if not comentario or comentario.sector_id != sector_id:
        raise HTTPException(404, "Comentario no encontrado")
    if comentario.user_id != usuario.id and usuario.role.value != "admin":
        raise HTTPException(403, "Solo el autor o un admin puede borrar este comentario")
    db.delete(comentario)
    db.commit()
