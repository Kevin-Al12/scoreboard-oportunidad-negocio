import logging
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.sector import Sector
from app.models.user import Role, User

router = APIRouter(prefix="/sectores", tags=["import-export"])
logger = logging.getLogger("scoreboard.importexport")

COLUMNAS = ["nombre", "descripcion", "notas", "fuentes_informacion", "responsable_email"]
MAX_BYTES_IMPORTACION = 5 * 1024 * 1024  # 5 MB alcanza de sobra para miles de filas de texto

# Excel/Sheets ejecuta como fórmula cualquier celda que empiece con estos
# caracteres al abrir el archivo -- si un sector se llamara p.ej.
# "=cmd|'/c calc'!A1", exportarlo tal cual sería inyección de fórmulas.
# Anteponer un apóstrofe lo neutraliza (se ve como texto literal).
_PREFIJOS_PELIGROSOS = ("=", "+", "-", "@")


def _celda_segura(valor) -> str:
    texto = "" if valor is None else str(valor)
    if texto.startswith(_PREFIJOS_PELIGROSOS):
        return "'" + texto
    return texto


def _sectores_a_dataframe(db: Session, organization_id: int) -> pd.DataFrame:
    sectores = db.query(Sector).filter(Sector.organization_id == organization_id).all()
    usuarios_por_id = {u.id: u.email for u in db.query(User).filter(User.organization_id == organization_id)}
    filas = [
        {
            "nombre": _celda_segura(s.nombre),
            "descripcion": _celda_segura(s.descripcion),
            "notas": _celda_segura(s.notas),
            "fuentes_informacion": _celda_segura(s.fuentes_informacion),
            "responsable_email": _celda_segura(usuarios_por_id.get(s.responsable_id, "")),
        }
        for s in sectores
    ]
    return pd.DataFrame(filas, columns=COLUMNAS)


@router.get("/exportar.csv")
def exportar_csv(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    df = _sectores_a_dataframe(db, usuario.organization_id)
    return Response(
        content=df.to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sectores.csv"},
    )


@router.get("/exportar.xlsx")
def exportar_excel(usuario: User = Depends(get_current_user), db: Session = Depends(get_db)):
    df = _sectores_a_dataframe(db, usuario.organization_id)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sectores")
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sectores.xlsx"},
    )


@router.post("/importar")
async def importar_sectores(
    archivo: UploadFile,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    """Crea o actualiza sectores masivamente desde un CSV/XLSX con las
    columnas: nombre, descripcion, notas, fuentes_informacion, responsable_email.

    Upsert por nombre dentro de la organización -- si ya existe un sector
    con ese nombre, se actualiza en vez de duplicarlo.
    """
    if not archivo.filename:
        raise HTTPException(422, "El archivo no trae nombre; debe terminar en .csv o .xlsx")

    contenido = await archivo.read(MAX_BYTES_IMPORTACION + 1)
    if len(contenido) > MAX_BYTES_IMPORTACION:
        raise HTTPException(413, f"El archivo supera el límite de {MAX_BYTES_IMPORTACION // (1024 * 1024)} MB")

    try:
        if archivo.filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(contenido))
        else:
            df = pd.read_excel(BytesIO(contenido))
    except Exception:
        # El detalle real (a veces incluye rutas/versiones de librería) va
        # al log del servidor, no a quien llama a la API.
        logger.warning("No se pudo leer el archivo importado '%s'", archivo.filename, exc_info=True)
        raise HTTPException(422, "No se pudo leer el archivo. Verificá que sea un CSV o Excel válido.")

    faltantes = set(["nombre"]) - set(df.columns)
    if faltantes:
        raise HTTPException(422, f"Faltan columnas requeridas: {sorted(faltantes)}")

    df = df.where(pd.notna(df), None)
    usuarios_por_email = {u.email.lower(): u.id for u in db.query(User).filter(User.organization_id == usuario.organization_id)}
    existentes_por_nombre = {
        s.nombre: s for s in db.query(Sector).filter(Sector.organization_id == usuario.organization_id)
    }

    creados, actualizados = 0, 0
    for _, fila in df.iterrows():
        nombre = str(fila.get("nombre") or "").strip()[:200]
        if not nombre:
            continue
        email_resp = str(fila.get("responsable_email") or "").strip().lower()
        responsable_id = usuarios_por_email.get(email_resp) if email_resp else None
        datos = dict(
            descripcion=str(fila.get("descripcion") or "")[:4000],
            notas=str(fila.get("notas") or "")[:4000],
            fuentes_informacion=str(fila.get("fuentes_informacion") or "")[:2000],
            responsable_id=responsable_id,
        )
        if nombre in existentes_por_nombre:
            for k, v in datos.items():
                setattr(existentes_por_nombre[nombre], k, v)
            actualizados += 1
        else:
            nuevo = Sector(organization_id=usuario.organization_id, creado_por_id=usuario.id, nombre=nombre, **datos)
            db.add(nuevo)
            # Se registra en el diccionario: si el MISMO archivo trae otra fila
            # con este nombre, se actualiza este sector en vez de crear un
            # duplicado (antes "Dup" dos veces en el CSV = dos sectores "Dup").
            existentes_por_nombre[nombre] = nuevo
            creados += 1

    db.commit()
    return {"creados": creados, "actualizados": actualizados}
