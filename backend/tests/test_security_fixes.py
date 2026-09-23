"""Un test por cada hallazgo de la revisión de seguridad, para que no se
vuelvan a colar."""

import uuid
from types import SimpleNamespace

from app.core import rate_limit
from tests.conftest import registrar_y_loguear


def _nueva_org_admin(client):
    sufijo = uuid.uuid4().hex[:8]
    header = registrar_y_loguear(client, f"admin-{sufijo}@test.com", f"Org {sufijo}")
    return {"Authorization": header}, sufijo


def _agregar_editor(client, admin_headers, sufijo):
    email = f"editor-{sufijo}@test.com"
    inv = client.post("/invitaciones", json={"email": email, "role": "editor"}, headers=admin_headers)
    r = client.post(
        "/auth/registro",
        json={"email": email, "password": "Password123!", "nombre_completo": "Un Editor", "token": inv.json()["token"]},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_viewer_no_puede_revertir_auditoria(client):
    admin_headers, sufijo = _nueva_org_admin(client)
    email_viewer = f"viewer-{sufijo}@test.com"
    inv = client.post("/invitaciones", json={"email": email_viewer, "role": "viewer"}, headers=admin_headers)
    r = client.post(
        "/auth/registro",
        json={"email": email_viewer, "password": "Password123!", "nombre_completo": "Un Viewer", "token": inv.json()["token"]},
    )
    viewer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post("/criterios", json={"nombre": "Peso crítico", "peso": 20}, headers=admin_headers)
    criterio_id = r.json()["id"]
    client.patch(f"/criterios/{criterio_id}", json={"peso": 90}, headers=admin_headers)

    entrada_id = client.get("/auditoria", headers=admin_headers).json()[0]["id"]

    # Antes: cualquier autenticado podía revertir. Ahora requiere admin/editor.
    r = client.post(f"/auditoria/{entrada_id}/revertir", headers=viewer_headers)
    assert r.status_code == 403

    r = client.get(f"/criterios/{criterio_id}", headers=admin_headers)
    assert r.json()["peso"] == 90  # no se revirtió


def test_no_se_puede_asignar_responsable_de_otra_organizacion(client):
    headers_a, _ = _nueva_org_admin(client)
    headers_b, sufijo_b = _nueva_org_admin(client)
    usuario_b_id = client.get("/auth/me", headers=headers_b).json()["id"]

    r = client.post("/sectores", json={"nombre": "Sector de A"}, headers=headers_a)
    sector_id = r.json()["id"]

    r = client.patch(f"/sectores/{sector_id}", json={"responsable_id": usuario_b_id}, headers=headers_a)
    assert r.status_code == 422

    r = client.post(
        "/sectores", json={"nombre": "Otro sector de A", "responsable_id": usuario_b_id}, headers=headers_a
    )
    assert r.status_code == 422


def test_api_key_de_usuario_desactivado_deja_de_funcionar(client):
    admin_headers, sufijo = _nueva_org_admin(client)
    editor_headers = _agregar_editor(client, admin_headers, sufijo)
    editor_id = client.get("/auth/me", headers=editor_headers).json()["id"]

    r = client.post("/api-keys", json={"nombre": "Key del editor"}, headers=editor_headers)
    raw_key = r.json()["api_key"]
    assert client.get("/sectores", headers={"X-API-Key": raw_key}).status_code == 200

    client.patch(f"/usuarios/{editor_id}", json={"activo": False}, headers=admin_headers)

    r = client.get("/sectores", headers={"X-API-Key": raw_key})
    assert r.status_code == 401


def test_ronda_incompleta_no_se_guarda(client):
    headers, _ = _nueva_org_admin(client)
    c1 = client.post("/criterios", json={"nombre": "Uno", "peso": 50}, headers=headers).json()["id"]
    client.post("/criterios", json={"nombre": "Dos", "peso": 50}, headers=headers)  # segundo criterio activo, sin calificar
    sector_id = client.post("/sectores", json={"nombre": "Sector incompleto"}, headers=headers).json()["id"]

    r = client.post(
        f"/sectores/{sector_id}/rondas",
        json={"calificaciones": [{"criterio_id": c1, "calificacion": 5}]},  # falta "Dos"
        headers=headers,
    )
    assert r.status_code == 422

    # Antes, esta ronda incompleta quedaba guardada como "la última" del
    # sector y lo hacía desaparecer del ranking sin avisar.
    r = client.get(f"/sectores/{sector_id}/rondas", headers=headers)
    assert r.json() == []
    r = client.get(f"/sectores/{sector_id}", headers=headers)
    assert r.json()["score_0_a_100"] is None


def test_admin_no_puede_dejar_la_organizacion_sin_admin(client):
    headers, _ = _nueva_org_admin(client)
    yo = client.get("/auth/me", headers=headers).json()

    r = client.patch(f"/usuarios/{yo['id']}", json={"role": "viewer"}, headers=headers)
    assert r.status_code == 400

    r = client.patch(f"/usuarios/{yo['id']}", json={"activo": False}, headers=headers)
    assert r.status_code == 400


def test_pdf_no_falla_con_caracteres_especiales_en_nombre_de_sector(client):
    headers, _ = _nueva_org_admin(client)
    c1 = client.post("/criterios", json={"nombre": "Uno", "peso": 100}, headers=headers).json()["id"]
    r = client.post("/sectores", json={"nombre": "Ropa <niños> & Cía"}, headers=headers)
    sector_id = r.json()["id"]
    client.post(f"/sectores/{sector_id}/rondas", json={"calificaciones": [{"criterio_id": c1, "calificacion": 5}]}, headers=headers)

    r = client.get("/reportes/top-sectores.pdf", params={"n": 5}, headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_login_tiene_limite_de_intentos(client):
    admin_headers, sufijo = _nueva_org_admin(client)
    email = client.get("/auth/me", headers=admin_headers).json()["email"]

    respuestas = [client.post("/auth/login", json={"email": email, "password": "incorrecta"}) for _ in range(12)]
    assert any(r.status_code == 429 for r in respuestas)


def _request_falsa(client_host, headers):
    return SimpleNamespace(client=SimpleNamespace(host=client_host) if client_host else None, headers=headers)


def test_ip_del_cliente_ignora_x_forwarded_for_sin_proxy_de_confianza(monkeypatch):
    monkeypatch.setattr(rate_limit._settings, "trust_proxy_headers", False)
    req = _request_falsa("10.0.0.5", {"X-Forwarded-For": "1.2.3.4"})
    # Sin confiar en el proxy, cualquiera podría mandar este header para
    # hacerse pasar por otra IP y saltarse el límite -- se ignora.
    assert rate_limit._ip_del_cliente(req) == "10.0.0.5"


def test_ip_del_cliente_usa_el_ultimo_xff_detras_de_proxy_de_confianza(monkeypatch):
    monkeypatch.setattr(rate_limit._settings, "trust_proxy_headers", True)
    # "1.2.3.4" lo pudo mandar el cliente mismo (falso); "9.9.9.9" es lo que
    # el proxy de confianza le agregó a la cadena al recibir la conexión --
    # eso es lo único que no se puede falsificar.
    req = _request_falsa("172.16.0.1", {"X-Forwarded-For": "1.2.3.4, 9.9.9.9"})
    assert rate_limit._ip_del_cliente(req) == "9.9.9.9"


def test_cors_origins_acepta_lista_separada_por_comas_y_json():
    from app.core.config import Settings

    # Formato cómodo para pegar en el panel de env vars de Render/Railway.
    s = Settings(_env_file=None, CORS_ORIGINS="https://a.com, https://b.com")
    assert s.cors_origins == ["https://a.com", "https://b.com"]

    # Formato JSON, el que ya usaba el .env local -- sigue funcionando.
    s = Settings(_env_file=None, CORS_ORIGINS='["https://a.com","https://b.com"]')
    assert s.cors_origins == ["https://a.com", "https://b.com"]
