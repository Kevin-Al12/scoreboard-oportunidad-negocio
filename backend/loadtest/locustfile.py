"""Ejemplo de test de carga con Locust -- no se ejecuta como parte de la
suite normal (no está en requirements.txt para no engordar la instalación
de todos los que solo quieren correr la app).

Instalar y correr:
    pip install locust
    locust -f backend/loadtest/locustfile.py --host http://localhost:8000

Abre http://localhost:8089 para lanzar la corrida desde la UI de Locust.
"""

from locust import HttpUser, between, task


class UsuarioTipico(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        r = self.client.post(
            "/auth/login", json={"email": "admin@acme-analytics.do", "password": "Admin123!"}
        )
        token = r.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(3)
    def ver_ranking(self):
        self.client.get("/dashboard/ranking")

    @task(2)
    def ver_sectores(self):
        self.client.get("/sectores")

    @task(1)
    def ver_auditoria(self):
        self.client.get("/auditoria")
