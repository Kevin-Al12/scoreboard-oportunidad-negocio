"""Segunda ronda de la revisión de seguridad: un test por hallazgo."""

import uuid
from unittest.mock import patch

from app.services import notificaciones
from tests.conftest import registrar_y_loguear

WEBHOOK_OK = "https://hooks.slack.com/services/T000AAA/B000BBB/abcdef123456"


def _admin(client):
    sufijo = uuid.uuid4().hex[:8]
    return {"Authorization": registrar_y_loguear(client, f"admin-{sufijo}@test.com", f"Org {sufijo}")}, sufijo


def _invitar_y_registrar(client, admin_headers, email, role="viewer"):
    inv = client.post("/invitaciones", json={"email": email, "role": role}, headers=admin_headers).json()
    r = client.post(
        "/auth/registro",
        json={"email": email, "password": "Password123!", "nombre_completo": "Otra Persona", "token": inv["token"]},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# 1. SSRF por el webhook de Slack
def test_webhook_slack_rechaza_urls_que_no_son_de_slack(client):
    admin, _ = _admin(client)
    for url in [
        "http://127.0.0.1:9911/interno",
        "http://169.254.169.254/latest/meta-data/",
        "http://hooks.slack.com/services/T0/B0/abc",  # sin https
        "https://hooks.slack.com.evil.com/services/T0/B0/abc",
        "https://evil.com@hooks.slack.com/services/T0/B0/abc",
        "https://hooks.slack.com/otra-cosa",
        "https://hooks.slack.com:8443/services/T0/B0/abc",
    ]:
        r = client.patch("/organizacion", json={"slack_webhook_url": url}, headers=admin)
        assert r.status_code == 422, url

    assert client.patch("/organizacion", json={"slack_webhook_url": WEBHOOK_OK}, headers=admin).status_code == 200
    # null lo quita
    r = client.patch("/organizacion", json={"slack_webhook_url": None}, headers=admin)
    assert r.json()["slack_configurado"] is False


def test_envio_slack_revalida_urls_viejas_guardadas_en_la_base():
    """Una URL interna que ya estuviera en la base (de antes del fix) no se usa."""
    with patch.object(notificaciones.httpx, "post") as post:
        assert notificaciones._enviar_slack("http://127.0.0.1:9911/interno", "hola") is False
        post.assert_not_called()


# 2. La URL del webhook no se expone
def test_webhook_nunca_se_devuelve_completo(client):
    admin, sufijo = _admin(client)
    client.patch("/organizacion", json={"slack_webhook_url": WEBHOOK_OK}, headers=admin)
    viewer = _invitar_y_registrar(client, admin, f"viewer-{sufijo}@test.com")

    vista_viewer = client.get("/organizacion", headers=viewer).json()
    assert vista_viewer["slack_configurado"] is True
    assert vista_viewer["slack_webhook_mascara"] is None
    assert "slack_webhook_url" not in vista_viewer

    vista_admin = client.get("/organizacion", headers=admin).json()
    assert vista_admin["slack_webhook_mascara"].endswith("3456")
    assert WEBHOOK_OK not in str(vista_admin)


# 3. Emails sin distinguir mayúsculas
def test_email_con_otras_mayusculas_no_crea_otra_cuenta(client):
    sufijo = uuid.uuid4().hex[:8]
    registrar_y_loguear(client, f"Kevin-{sufijo}@Test.com", f"Org A {sufijo}")
    r = client.post(
        "/auth/registro",
        json={"email": f"kevin-{sufijo}@test.com", "password": "Password123!", "nombre_completo": "X",
              "organizacion_nombre": f"Org B {sufijo}"},
    )
    assert r.status_code == 409
    login = client.post("/auth/login", json={"email": f"KEVIN-{sufijo}@TEST.COM", "password": "Password123!"})
    assert login.status_code == 200


def test_invitacion_no_se_quema_si_falla_el_registro(client):
    from fastapi.testclient import TestClient

    from app.api.routers import auth as auth_router
    from app.main import app

    admin, sufijo = _admin(client)
    email = f"nuevo-{sufijo}@test.com"
    token = client.post("/invitaciones", json={"email": email}, headers=admin).json()["token"]
    datos = {"email": email, "password": "Password123!", "nombre_completo": "N", "token": token}

    # Falla DESPUÉS de validar la invitación (al crear el usuario)
    with patch.object(auth_router, "hash_password", side_effect=RuntimeError("fallo simulado")):
        r = TestClient(app, raise_server_exceptions=False).post("/auth/registro", json=datos)
    assert r.status_code == 500

    # El mismo código sigue sirviendo
    r = client.post("/auth/registro", json=datos)
    assert r.status_code == 201, r.text


# 4. `orden` fuera de rango
def test_orden_de_criterio_fuera_de_rango_es_422_no_500(client):
    admin, _ = _admin(client)
    r = client.post("/criterios", json={"nombre": "c", "peso": 1, "orden": 10**12}, headers=admin)
    assert r.status_code == 422
    crit = client.post("/criterios", json={"nombre": "c", "peso": 1}, headers=admin).json()
    assert client.patch(f"/criterios/{crit['id']}", json={"orden": -5}, headers=admin).status_code == 422


# 5. Tamaño de filtros guardados
def test_filtro_guardado_con_params_gigantes_es_rechazado(client):
    admin, _ = _admin(client)
    r = client.post("/filtros-guardados", json={"nombre": "f", "params": {"x": "y" * 100_000}}, headers=admin)
    assert r.status_code == 422
    r = client.post("/filtros-guardados", json={"nombre": "f", "params": {"min_score": 70}}, headers=admin)
    assert r.status_code == 201


# 6. Duplicados dentro del mismo archivo importado
def test_importar_con_nombre_repetido_en_el_archivo_no_duplica(client):
    admin, _ = _admin(client)
    csv = b"nombre,descripcion\nDup,primera\nDup,segunda\n"
    r = client.post("/sectores/importar", files={"archivo": ("s.csv", csv)}, headers=admin)
    assert r.json() == {"creados": 1, "actualizados": 1}
    sectores = [s for s in client.get("/sectores", headers=admin).json() if s["nombre"] == "Dup"]
    assert len(sectores) == 1
    assert sectores[0]["descripcion"] == "segunda"
