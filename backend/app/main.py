import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routers import (
    api_keys,
    auditoria,
    auth,
    comentarios,
    contexto_mercado,
    criterios,
    dashboard,
    evaluaciones,
    filtros_guardados,
    importexport,
    invitaciones,
    notificaciones,
    organizacion,
    reportes,
    sectores,
    usuarios,
)
from app.core.config import get_settings, validar_secret_key
from app.core.logging import configurar_logging
from app.core.rate_limit import limitar_por_api_key
from app.db.session import SessionLocal

settings = get_settings()
validar_secret_key(settings)  # falla rápido si SECRET_KEY es la de ejemplo o muy corta
configurar_logging()
_inicio_proceso = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El esquema lo maneja SOLO Alembic (backend/alembic/, ver README).
    # Antes había un create_all() acá "por si acaso" -- con Postgres eso
    # puede crear tablas/columnas por su cuenta y dejar el esquema real
    # desincronizado de lo que las migraciones creen que aplicaron.
    yield


app = FastAPI(
    title="Scoreboard de Oportunidad de Negocio",
    description="Motor de scoring configurable para comparar sectores de negocio.",
    version="0.2.0",
    lifespan=lifespan,
    dependencies=[Depends(limitar_por_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(invitaciones.router)
app.include_router(organizacion.router)
# importexport define rutas literales bajo /sectores (ej. /sectores/exportar.csv)
# que deben registrarse ANTES que /sectores/{sector_id}: FastAPI hace matching
# de rutas en orden de registro y sin mirar el tipo del parámetro a nivel de
# ruteo, así que si {sector_id} queda primero, "exportar.csv" calza ahí y
# revienta con 422 al intentar convertirlo a int.
app.include_router(importexport.router)
app.include_router(sectores.router)
app.include_router(criterios.router)
app.include_router(evaluaciones.router)
app.include_router(dashboard.router)
app.include_router(reportes.router)
app.include_router(auditoria.router)
app.include_router(comentarios.router)
app.include_router(notificaciones.router)
app.include_router(api_keys.router)
app.include_router(filtros_guardados.router)
app.include_router(contexto_mercado.router)


@app.get("/health")
def health():
    """Health check real: además de 'el proceso responde', confirma que
    puede hablar con la base de datos -- lo que de verdad se necesita saber
    antes de marcar la instancia como lista en un load balancer."""
    db_ok = True
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    finally:
        db.close()  # antes no se cerraba si el SELECT 1 fallaba

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "uptime_seconds": round(time.monotonic() - _inicio_proceso, 1),
        "version": app.version,
    }
