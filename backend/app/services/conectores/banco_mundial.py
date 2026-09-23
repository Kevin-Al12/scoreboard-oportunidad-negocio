"""Conector de ejemplo a una fuente de datos EXTERNA REAL.

Esto es lo único de la lista de "integraciones" que sí llama a un servicio
externo de verdad: la API pública del Banco Mundial (no requiere API key).
Sirve para ilustrar el patrón de "conector" -- una función que trae
contexto de mercado en vez de cargarlo a mano -- sin fabricar datos falsos.

Fuentes de datos de mercado dominicano específicas (ONE, Nielsen, Kantar,
cámaras de comercio) normalmente requieren convenios o suscripciones pagas
que no existen en este entorno; agregar un conector para ellas es
mecánico una vez que se tenga acceso: misma forma, otra URL/parseo.
"""

import time

import httpx

BASE_URL = "https://api.worldbank.org/v2/country/DO/indicator"

# Estos indicadores se publican una vez al año -- sin caché, cada carga del
# dashboard disparaba 3 llamadas externas de hasta 6s cada una. 24h es de
# sobra para no notar el cambio de un dato que se actualiza anualmente.
_TTL_SEGUNDOS = 24 * 60 * 60
_cache: dict[str, tuple[float, dict | None]] = {}

# Indicadores públicos del Banco Mundial relevantes para un análisis de
# oportunidad de mercado en RD.
INDICADORES = {
    "crecimiento_pib": "NY.GDP.MKTP.KD.ZG",
    "inflacion": "FP.CPI.TOTL.ZG",
    "desempleo": "SL.UEM.TOTL.ZS",
}


def obtener_indicador(clave: str) -> dict | None:
    """Devuelve el dato más reciente disponible de un indicador, o None si falla la llamada.
    Cacheado 24h -- ver _TTL_SEGUNDOS arriba."""
    ahora = time.monotonic()
    if clave in _cache:
        guardado_en, valor = _cache[clave]
        if ahora - guardado_en < _TTL_SEGUNDOS:
            return valor

    codigo = INDICADORES.get(clave)
    if not codigo:
        return None
    try:
        r = httpx.get(
            f"{BASE_URL}/{codigo}",
            params={"format": "json", "per_page": 10},
            timeout=6,
        )
        r.raise_for_status()
        _, filas = r.json()
        resultado = None
        for fila in filas:
            if fila.get("value") is not None:
                resultado = {"indicador": clave, "anio": int(fila["date"]), "valor": fila["value"]}
                break
        _cache[clave] = (ahora, resultado)
        return resultado
    except Exception:
        # Si falla y había un valor viejo en caché, mejor devolver ese que
        # nada -- pero no lo "refrescamos" (queda para reintentar pronto).
        if clave in _cache:
            return _cache[clave][1]
        return None


def obtener_contexto_macro() -> dict:
    """Trae los indicadores disponibles; los que fallen (sin internet, API caída) quedan en None."""
    return {clave: obtener_indicador(clave) for clave in INDICADORES}
