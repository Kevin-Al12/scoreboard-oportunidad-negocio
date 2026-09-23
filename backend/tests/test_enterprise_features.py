"""Cubre las features 'corporativas': roles/permisos, multi-tenancy, auditoría
con reversión, comentarios con @mención -> notificación, y API keys.
"""

import uuid

from tests.conftest import registrar_y_loguear


def _nueva_org_admin(client):
    sufijo = uuid.uuid4().hex[:8]
    header = registrar_y_loguear(client, f"admin-{sufijo}@test.com", f"Org {sufijo}")
    return {"Authorization": header}, sufijo


def test_segundo_usuario_se_une_solo_con_invitacion_valida(client):
    sufijo = uuid.uuid4().hex[:8]
    org = f"Org Compartida {sufijo}"
    admin_header = registrar_y_loguear(client, f"admin-{sufijo}@test.com", org)
    admin_headers = {"Authorization": admin_header}
    email_segundo = f"segundo-{sufijo}@test.com"

    # Sin invitación, ni siquiera escribiendo el nombre exacto de la
    # organización se puede entrar -- esto es justo el hueco que se cerró.
    r = client.post(
        "/auth/registro",
        json={"email": email_segundo, "password": "Password123!", "nombre_completo": "Segundo Usuario", "organizacion_nombre": org},
    )
    assert r.status_code == 409

    r = client.post("/invitaciones", json={"email": email_segundo, "role": "viewer"}, headers=admin_headers)
    assert r.status_code == 201
    token_invitacion = r.json()["token"]

    # Un token para OTRO email no sirve.
    r = client.post(
        "/auth/registro",
        json={"email": "otro@test.com", "password": "Password123!", "nombre_completo": "Otro", "token": token_invitacion},
    )
    assert r.status_code == 403

    r = client.post(
        "/auth/registro",
        json={"email": email_segundo, "password": "Password123!", "nombre_completo": "Segundo Usuario", "token": token_invitacion},
    )
    assert r.status_code == 201
    token_segundo = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token_segundo}"})
    assert me.json()["role"] == "viewer"
    assert me.json()["organization_id"] == client.get("/auth/me", headers=admin_headers).json()["organization_id"]

    # El viewer no puede crear sectores.
    r = client.post(
        "/sectores", json={"nombre": "Intento de viewer"}, headers={"Authorization": f"Bearer {token_segundo}"}
    )
    assert r.status_code == 403

    # El token ya se usó -- no se puede reutilizar.
    r = client.post(
        "/auth/registro",
        json={"email": f"tercero-{sufijo}@test.com", "password": "Password123!", "nombre_completo": "Tercero", "token": token_invitacion},
    )
    assert r.status_code == 410

    # Pero el admin de esa misma org sí puede crear sectores.
    r = client.post("/sectores", json={"nombre": "Sector del admin"}, headers=admin_headers)
    assert r.status_code == 201


def test_multi_tenancy_aisla_datos_entre_organizaciones(client):
    headers_a, _ = _nueva_org_admin(client)
    headers_b, _ = _nueva_org_admin(client)

    r = client.post("/sectores", json={"nombre": "Solo de A"}, headers=headers_a)
    sector_id_de_a = r.json()["id"]

    # La organización B no puede ver el sector de la organización A.
    r = client.get(f"/sectores/{sector_id_de_a}", headers=headers_b)
    assert r.status_code == 404

    r = client.get("/sectores", headers=headers_b)
    assert r.json() == []


def test_auditoria_registra_cambio_de_peso_y_permite_revertirlo(client):
    headers, _ = _nueva_org_admin(client)
    r = client.post("/criterios", json={"nombre": "Tamaño de mercado", "peso": 20}, headers=headers)
    criterio_id = r.json()["id"]

    r = client.patch(f"/criterios/{criterio_id}", json={"peso": 35}, headers=headers)
    assert r.status_code == 200
    assert r.json()["peso"] == 35

    r = client.get("/auditoria", params={"entidad": "criterio", "entidad_id": criterio_id}, headers=headers)
    entradas = r.json()
    assert len(entradas) == 1
    assert entradas[0]["campo"] == "peso"
    assert entradas[0]["valor_anterior"] == "20.0"
    assert entradas[0]["valor_nuevo"] == "35.0"
    assert entradas[0]["revertible"] is True

    r = client.post(f"/auditoria/{entradas[0]['id']}/revertir", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/criterios/{criterio_id}", headers=headers)
    assert r.json()["peso"] == 20.0


def test_comentario_con_mencion_genera_notificacion(client):
    sufijo = uuid.uuid4().hex[:8]
    org = f"Org Mencion {sufijo}"
    admin_header = registrar_y_loguear(client, f"admin-{sufijo}@test.com", org)
    admin_headers = {"Authorization": admin_header}
    email_eddy = f"eddy-{sufijo}@test.com"

    inv = client.post("/invitaciones", json={"email": email_eddy, "role": "editor"}, headers=admin_headers)
    r = client.post(
        "/auth/registro",
        json={"email": email_eddy, "password": "Password123!", "nombre_completo": "Eddy Editor", "token": inv.json()["token"]},
    )
    eddy_token = r.json()["access_token"]
    eddy_headers = {"Authorization": f"Bearer {eddy_token}"}

    r = client.post("/sectores", json={"nombre": "Sector comentado"}, headers=admin_headers)
    sector_id = r.json()["id"]

    r = client.post(
        f"/sectores/{sector_id}/comentarios", json={"texto": "@Eddy revisa esto por favor"}, headers=admin_headers
    )
    assert r.status_code == 201
    assert r.json()["menciones_user_ids"] != []

    r = client.get("/notificaciones", headers=eddy_headers)
    notifs = r.json()
    assert any(n["tipo"] == "mencion" for n in notifs)


def test_api_key_autentica_como_alternativa_al_jwt(client):
    headers, _ = _nueva_org_admin(client)
    r = client.post("/api-keys", json={"nombre": "Integración de prueba"}, headers=headers)
    assert r.status_code == 201
    raw_key = r.json()["api_key"]

    # La API key sola (sin JWT) debe alcanzar para leer datos protegidos.
    r = client.get("/sectores", headers={"X-API-Key": raw_key})
    assert r.status_code == 200

    # Revocada, deja de funcionar.
    key_id = client.get("/api-keys", headers=headers).json()[0]["id"]
    client.delete(f"/api-keys/{key_id}", headers=headers)
    r = client.get("/sectores", headers={"X-API-Key": raw_key})
    assert r.status_code == 401


def test_exportar_csv_incluye_los_sectores_de_mi_organizacion(client):
    headers, _ = _nueva_org_admin(client)
    client.post("/sectores", json={"nombre": "Exportable"}, headers=headers)

    r = client.get("/sectores/exportar.csv", headers=headers)
    assert r.status_code == 200
    assert "Exportable" in r.text
