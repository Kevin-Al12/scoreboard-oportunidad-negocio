"""Smoke test de la API completa (sectores -> criterios -> rondas -> score)."""


def test_flujo_completo_sector_criterios_ronda_y_score(client, auth_headers):
    # 1. Crear criterios (pesos configurables, no hardcodeados)
    pesos = [
        ("Tamaño de mercado", 0.20),
        ("Nivel de saturación", 0.25),
        ("Tendencia de crecimiento", 0.20),
        ("Barreras de entrada", 0.15),
        ("Complejidad regulatoria", 0.10),
        ("Capital requerido", 0.10),
    ]
    criterio_ids = []
    for nombre, peso in pesos:
        r = client.post("/criterios", json={"nombre": nombre, "peso": peso}, headers=auth_headers)
        assert r.status_code == 201, r.text
        criterio_ids.append(r.json()["id"])

    # 2. Crear un sector
    r = client.post(
        "/sectores",
        json={
            "nombre": "Lavado de autos a domicilio",
            "descripcion": "Servicio móvil de detailing",
            "notas": "Alta demanda en zonas residenciales",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    sector_id = r.json()["id"]

    # 3. Sector recién creado no tiene score todavía
    r = client.get(f"/sectores/{sector_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["score_0_a_100"] is None

    # 4. Registrar una ronda de evaluación completa
    valores = [3, 4, 4, 4, 5, 4]
    calificaciones = [
        {"criterio_id": cid, "calificacion": val, "notas": "demo"}
        for cid, val in zip(criterio_ids, valores)
    ]
    r = client.post(f"/sectores/{sector_id}/rondas", json={"calificaciones": calificaciones}, headers=auth_headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["score_0_a_100"] == 72.5
    assert data["score_1_a_5"] == 3.9

    # 5. El sector ahora refleja el score de su última ronda
    r = client.get(f"/sectores/{sector_id}", headers=auth_headers)
    assert r.json()["score_0_a_100"] == 72.5

    # 6. Reevaluar el sector en otra fecha (histórico)
    calificaciones_mejoradas = [
        {"criterio_id": cid, "calificacion": 5, "notas": ""} for cid in criterio_ids
    ]
    r = client.post(
        f"/sectores/{sector_id}/rondas",
        json={"fecha": "2026-01-01", "calificaciones": calificaciones_mejoradas},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["score_0_a_100"] == 100.0

    r = client.get(f"/sectores/{sector_id}/rondas", headers=auth_headers)
    assert len(r.json()) == 2


def test_criterio_con_peso_invalido_es_rechazado(client, auth_headers):
    r = client.post("/criterios", json={"nombre": "Peso negativo", "peso": -1}, headers=auth_headers)
    assert r.status_code == 422


def test_endpoints_protegidos_requieren_autenticacion(client):
    assert client.get("/sectores").status_code == 401
    assert client.get("/dashboard/ranking").status_code == 401
