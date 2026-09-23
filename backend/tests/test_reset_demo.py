"""Cubre reset_demo.py: el ciclo completo de borrar-todo + resembrar, y que
la cuenta viewer de la demo pública sea de verdad de solo lectura."""

from app.models.organization import Organization
from app.models.sector import Sector
from app.models.user import User
from reset_demo import _TABLAS_EN_ORDEN_DE_BORRADO
from seed import NOMBRE_ORG, SECTORES, USUARIOS, sembrar
from tests.conftest import TestingSessionLocal


def _limpiar_todo(db):
    for modelo in _TABLAS_EN_ORDEN_DE_BORRADO:
        db.query(modelo).delete()
    db.commit()


def test_sembrar_dos_veces_seguidas_tras_borrar_no_deja_residuos_ni_choca_con_fks():
    db = TestingSessionLocal()
    try:
        # Todos los tests del proyecto comparten una única base SQLite en
        # memoria sin rollback entre tests (ver conftest.py), así que para
        # poder afirmar conteos absolutos hay que partir de cero acá --
        # otros tests ya habrán dejado sus propias organizaciones (con
        # nombres únicos, no chocan por unique constraint, pero sí
        # arruinarían un `count() == 1`).
        _limpiar_todo(db)

        sembrar(db)
        assert db.query(Organization).count() == 1
        assert db.query(Sector).count() == len(SECTORES)

        # El mismo borrado que hace reset_demo.py, en el mismo orden.
        _limpiar_todo(db)
        assert db.query(Organization).count() == 0
        assert db.query(Sector).count() == 0
        assert db.query(User).count() == 0

        sembrar(db)
        assert db.query(Organization).filter(Organization.nombre == NOMBRE_ORG).count() == 1
        assert db.query(Sector).count() == len(SECTORES)
        assert db.query(User).count() == len(USUARIOS)
    finally:
        db.close()


def test_viewer_demo_no_puede_crear_editar_ni_borrar_nada(client):
    db = TestingSessionLocal()
    try:
        # "Acme Analytics RD" es un nombre fijo (es la demo real), así que
        # no puede sembrarse dos veces sin chocar con el unique constraint
        # si otro test ya lo dejó sembrado.
        _limpiar_todo(db)
        sembrar(db)
    finally:
        db.close()

    r = client.post("/auth/login", json={"email": "viewer@acme-analytics.do", "password": "Viewer123!"})
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    sector_id = client.get("/sectores", headers=headers).json()[0]["id"]
    criterio_id = client.get("/criterios", headers=headers).json()[0]["id"]

    intentos_de_escritura = [
        lambda: client.post("/sectores", json={"nombre": "Intento viewer"}, headers=headers),
        lambda: client.patch(f"/sectores/{sector_id}", json={"notas": "hackeado"}, headers=headers),
        lambda: client.delete(f"/sectores/{sector_id}", headers=headers),
        lambda: client.post("/criterios", json={"nombre": "Intento", "peso": 10}, headers=headers),
        lambda: client.patch(f"/criterios/{criterio_id}", json={"peso": 999}, headers=headers),
        lambda: client.delete(f"/criterios/{criterio_id}", headers=headers),
        lambda: client.post(
            f"/sectores/{sector_id}/rondas",
            json={"calificaciones": [{"criterio_id": criterio_id, "calificacion": 5}]},
            headers=headers,
        ),
        lambda: client.post("/invitaciones", json={"email": "otro@test.com", "role": "admin"}, headers=headers),
        lambda: client.patch("/organizacion", json={"slack_webhook_url": None}, headers=headers),
    ]

    for intento in intentos_de_escritura:
        r = intento()
        assert r.status_code in (403, 404), f"{r.request.method} {r.request.url} devolvió {r.status_code}, esperaba 403"

    # Pero sí puede leer y comentar (esa parte de "solo lectura" es sobre
    # los datos de negocio, no sobre poder participar en absoluto).
    assert client.get("/sectores", headers=headers).status_code == 200
    assert client.get("/dashboard/ranking", headers=headers).status_code == 200
    r = client.post(f"/sectores/{sector_id}/comentarios", json={"texto": "Solo mirando"}, headers=headers)
    assert r.status_code == 201


def test_demo_publica_no_usa_las_contrasenas_de_ejemplo_para_admin_ni_editor(client, monkeypatch):
    """seed.py es público: si la demo usara Admin123!/Editor123!, cualquiera
    podría entrar como admin. Solo el viewer tiene contraseña conocida."""
    import reset_demo

    monkeypatch.setenv("ES_INSTANCIA_DEMO", "si")
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("DEMO_EDITOR_PASSWORD", "clave-editor-de-un-secret-de-github")
    monkeypatch.setattr(reset_demo, "SessionLocal", TestingSessionLocal)
    reset_demo.resetear()

    def login(email, password):
        return client.post("/auth/login", json={"email": email, "password": password}).status_code

    assert login("admin@acme-analytics.do", "Admin123!") == 401
    assert login("editor@acme-analytics.do", "Editor123!") == 401
    assert login("editor@acme-analytics.do", "clave-editor-de-un-secret-de-github") == 200
    assert login("viewer@acme-analytics.do", "Viewer123!") == 200


def test_reset_no_imprime_la_api_key(capsys, monkeypatch):
    """Corre en GitHub Actions: en un repo público, los logs son públicos."""
    import reset_demo

    monkeypatch.setenv("ES_INSTANCIA_DEMO", "si")
    monkeypatch.setattr(reset_demo, "SessionLocal", TestingSessionLocal)
    reset_demo.resetear()
    assert "sbk_" not in capsys.readouterr().out


def test_database_url_de_render_usa_el_driver_instalado():
    from app.core.config import Settings

    for url in ("postgresql://u:p@host:5432/db", "postgres://u:p@host:5432/db"):
        s = Settings(database_url=url)
        assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"
    assert Settings(database_url="sqlite:///./dev.db").database_url == "sqlite:///./dev.db"
