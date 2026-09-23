import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRET_KEY_PLACEHOLDER = "dev-secret-key-cambiar-en-produccion"
SECRET_KEY_MIN_LEN = 32

_CORS_ORIGINS_POR_DEFECTO = ",".join(
    f"http://localhost:{p}" for p in (3000, 5173, 5174, 5175, 5176, 5177)
)


class Settings(BaseSettings):
    """Configuración de la app, cargable desde variables de entorno o .env.

    DATABASE_URL apunta a Postgres en producción/uso normal, pero puede
    apuntar a SQLite (ej. "sqlite:///./dev.db") para desarrollo local
    rápido sin tener que levantar un servidor de Postgres.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://scoreboard:scoreboard@localhost:5432/scoreboard"

    # Guardado como string plano (no list[str]) A PROPÓSITO: pydantic-settings
    # intenta decodificar como JSON cualquier variable de entorno que llene un
    # campo `list[...]` ANTES de que corra ningún validador propio -- así que
    # un valor separado por comas (mucho más cómodo de pegar en el panel de
    # variables de entorno de Render/Railway) reventaba con
    # "SettingsError: error parsing value" antes de llegar a nuestro código.
    # `cors_origins` (la property de abajo) hace el parseo de verdad y sigue
    # aceptando el formato JSON `["https://a.com"]` por compatibilidad con lo
    # que ya usaba el .env local.
    # validation_alias mantiene el nombre de variable de entorno CORS_ORIGINS
    # (el que usan el resto de la docs/deploy) aunque el atributo interno se
    # llame distinto.
    cors_origins_raw: str = Field(default=_CORS_ORIGINS_POR_DEFECTO, validation_alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        v = self.cors_origins_raw.strip()
        if v.startswith("["):
            return json.loads(v)
        return [origen.strip() for origen in v.split(",") if origen.strip()]

    # Auth: firma los JWT de sesión. NO se puede dejar en el valor de
    # ejemplo -- ver validar_secret_key(), que hace que la app se niegue a
    # arrancar si no se cambió.
    secret_key: str = SECRET_KEY_PLACEHOLDER

    # --- Integraciones opcionales: si no se configuran, los adaptadores
    # correspondientes simplemente no envían nada externo (ver
    # app/services/notificaciones.py) y el registro in-app se crea igual.
    # Slack NO va aquí -- es por organización (Organization.slack_webhook_url),
    # porque un webhook global mandaría notificaciones de una organización
    # al canal de Slack de otra. ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    # Rate limiting de la API pública (por API key). Ver app/core/rate_limit.py.
    api_rate_limit_por_minuto: int = 60

    # En Render/Railway (y cualquier PaaS detrás de un proxy/load balancer),
    # request.client.host es la IP INTERNA del proxy -- todo el tráfico
    # externo comparte esa misma IP, así que el rate limit por IP terminaría
    # limitando a todos los usuarios juntos como si fueran uno solo. Con
    # esto en true, se usa el último valor de X-Forwarded-For (el que el
    # proxy de la plataforma le agrega a la cadena) como IP real.
    #
    # NUNCA activar esto si la app recibe tráfico directo de internet sin un
    # proxy de por medio -- cualquiera podría poner su propio
    # X-Forwarded-For y hacerse pasar por otra IP para saltarse el límite.
    trust_proxy_headers: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validar_secret_key(settings: Settings) -> None:
    """Se llama al arrancar la app (app/main.py). Falla rápido y ruidoso en
    vez de dejar corriendo un servidor donde cualquiera que conozca (o
    adivine) la clave de ejemplo puede forjar un JWT de cualquier usuario,
    incluido un admin."""
    if settings.secret_key == SECRET_KEY_PLACEHOLDER or len(settings.secret_key) < SECRET_KEY_MIN_LEN:
        raise RuntimeError(
            "SECRET_KEY insegura o no configurada. Generá una real con:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "y ponla en backend/.env como SECRET_KEY=... (mínimo 32 caracteres, "
            "distinta del valor de ejemplo)."
        )
