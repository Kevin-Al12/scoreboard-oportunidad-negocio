"""Fixtures compartidos: base SQLite en memoria + cliente de test + helper de auth.

Usa SQLite en memoria en vez de Postgres para no depender de un servidor de
base de datos al correr los tests. La lógica de negocio es la misma
(SQLAlchemy Core/ORM es agnóstico del motor); Postgres se sigue usando en
desarrollo/producción vía DATABASE_URL.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"
# app.main ahora se niega a arrancar con la SECRET_KEY de ejemplo (ver
# app/core/config.py::validar_secret_key) -- los tests necesitan una propia,
# distinta del placeholder y de al menos 32 caracteres.
os.environ.setdefault("SECRET_KEY", "clave-de-pruebas-solo-para-pytest-nunca-usar-en-produccion")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import rate_limit
from app.db import session as db_session
from app.db.session import Base, get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# app.services.notificaciones abre su PROPIA sesión (vía db_session.SessionLocal())
# para el envío en background, en vez de depender de get_db -- sin este
# parche apuntaría a la base sqlite:// real de la app (vacía, sin tablas)
# en vez de a la base de pruebas de arriba.
db_session.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def _crear_tablas():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _resetear_rate_limits():
    """El TestClient manda todas las requests desde el mismo host falso
    ('testclient'), así que sin esto los ~15 registros/logins de la suite
    completa compartirían un solo contador de /auth/login y empezarían a
    dar 429 a mitad de la corrida."""
    rate_limit._contador_api_key.clear()
    rate_limit._contador_ip.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def registrar_y_loguear(client: TestClient, email: str, organizacion: str, nombre: str = "Test User") -> str:
    """Registra un usuario (admin si la organización es nueva) y devuelve su header de Authorization."""
    r = client.post(
        "/auth/registro",
        json={"email": email, "password": "Password123!", "nombre_completo": nombre, "organizacion_nombre": organizacion},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return f"Bearer {token}"


@pytest.fixture
def auth_headers(client):
    """Un admin recién registrado en una organización nueva y única por test."""
    import uuid

    sufijo = uuid.uuid4().hex[:8]
    header = registrar_y_loguear(client, f"admin-{sufijo}@test.com", f"Org Test {sufijo}")
    return {"Authorization": header}
