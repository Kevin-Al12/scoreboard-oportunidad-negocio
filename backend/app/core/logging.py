"""Logging estructurado (JSON por línea) en vez de texto libre.

Suficiente para que un agregador real (CloudWatch, Datadog, Loki) pueda
parsear cada línea sin regex; no sustituye un pipeline de observabilidad
completo (eso implicaría correlación de trace-id, métricas, dashboards --
fuera del alcance de un proyecto de ejemplo).
"""

import json
import logging
import sys
from datetime import datetime, timezone


class FormateadorJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configurar_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormateadorJSON())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    # uvicorn trae sus propios loggers con su propio formato; se homogenizan.
    for nombre in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(nombre)
        logger.handlers = [handler]
        logger.propagate = False
