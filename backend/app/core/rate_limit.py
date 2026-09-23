"""Rate limiting de demostración (por API key y por IP).

Es una ventana deslizante en memoria de proceso -- suficiente para mostrar
el patrón y frenar abuso accidental en un solo proceso, pero NO es correcto
en producción con varios workers/instancias (cada proceso tiene su propio
contador). Para eso, esto debería respaldarse en Redis (INCR + EXPIRE) en
vez de un dict en memoria; se deja así de simple a propósito para no
introducir una dependencia de infraestructura en un proyecto de ejemplo.
"""

import re
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.core.config import get_settings

_settings = get_settings()
_contador_api_key: dict[str, list[float]] = defaultdict(list)
_contador_ip: dict[str, list[float]] = defaultdict(list)

# Máximo de claves distintas que se trackean a la vez -- sin esto, alguien
# mandando X-API-Key aleatorias en cada request hace crecer el diccionario
# sin límite (cada clave nueva, aunque inválida, se quedaba en memoria para
# siempre). Con el formato + el tope, lo peor que pasa es que se descarten
# entradas viejas.
_MAX_CLAVES_TRACKEADAS = 5000
_FORMATO_API_KEY = re.compile(r"^sbk_[A-Za-z0-9_-]{20,80}$")


def _contar(contador: dict, clave: str, limite: int, ventana: float = 60.0) -> None:
    ahora = time.monotonic()
    if len(contador) > _MAX_CLAVES_TRACKEADAS:
        contador.clear()  # ventana de 60s: perder contadores en curso es aceptable frente a memoria sin límite

    marcas = contador[clave]
    marcas[:] = [t for t in marcas if ahora - t < ventana]
    if len(marcas) >= limite:
        raise HTTPException(429, f"Límite de {limite} solicitudes/minuto excedido")
    marcas.append(ahora)


def limitar_por_api_key(request: Request) -> None:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return  # las requests con sesión de usuario (JWT) no se limitan aquí

    if not _FORMATO_API_KEY.match(api_key):
        # No tiene la forma de una API key real (sbk_...) -- se rechaza de
        # una vez, sin gastar memoria en trackearla.
        raise HTTPException(401, "API key inválida")

    _contar(_contador_api_key, api_key, _settings.api_rate_limit_por_minuto)


def _ip_del_cliente(request: Request) -> str:
    """Detrás de un proxy de confianza (Render, Railway...), request.client.host
    es la IP interna del proxy -- TODO el tráfico externo compartiría esa
    misma IP y el rate limit terminaría tratando a todos los usuarios como
    uno solo. En ese caso (settings.trust_proxy_headers=True) se usa el
    ÚLTIMO valor de X-Forwarded-For: es el que el propio proxy le agregó a
    la cadena al recibir la conexión, así que no lo puede falsificar un
    cliente mandando su propio header (el proxy solo *agrega*, no deja que
    se sobrescriba lo que ya puso).

    Sin trust_proxy_headers, se usa siempre request.client.host -- confiar
    en X-Forwarded-For sin tener un proxy real por delante permitiría que
    cualquiera se salte el límite mandando ese header con una IP distinta
    en cada intento.
    """
    if _settings.trust_proxy_headers:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[-1].strip()
    return request.client.host if request.client else "desconocida"


def limitar_por_ip(request: Request) -> None:
    """Para /auth/login y /auth/registro -- sin esto, se pueden probar
    contraseñas sin límite (el rate limit por API key no aplicaba aquí)."""
    _contar(_contador_ip, _ip_del_cliente(request), limite=10, ventana=60.0)
