from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_es_sqlite = settings.database_url.startswith("sqlite")

if _es_sqlite:
    connect_args = {"check_same_thread": False}
    pool_kwargs = {}
else:
    connect_args = {}
    # Sin pool_pre_ping, la primera petición después de que Postgres se
    # reinicia o hay un corte de red breve falla con una conexión muerta
    # que el pool no sabía que estaba muerta -- pre_ping la prueba (SELECT 1
    # barato) antes de usarla. pool_recycle evita que el servidor cierre
    # conexiones que el pool cree vivas por estar idle demasiado tiempo.
    pool_kwargs = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10, "pool_recycle": 1800}

engine = create_engine(settings.database_url, connect_args=connect_args, **pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
