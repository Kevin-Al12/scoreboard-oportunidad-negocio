"""Resetea la instancia de DEMO pública: borra todos los datos y vuelve a
sembrar la organización de ejemplo desde cero.

Pensado para correr como cron job nocturno (ver render.yaml) contra la base
de datos de la demo pública -- así cualquier cosa que un visitante haya
creado durante el día (sectores de prueba, comentarios, invitaciones, etc.)
desaparece y la demo vuelve a verse igual que el primer día.

A diferencia de seed.py, este script NO tiene el guardrail de "¿esto parece
una base de desarrollo?" -- su propósito explícito es correr contra la base
de producción de la demo. Para que no se pueda ejecutar por accidente
contra una base que no es la de la demo, exige la variable de entorno
ES_INSTANCIA_DEMO=si (la pone render.yaml en el cron job).

Ejecutar con:
    ES_INSTANCIA_DEMO=si python reset_demo.py
"""

import os
import sys

from app.db.session import SessionLocal
from app.models.api_key import ApiKey
from app.models.audit import AuditLog
from app.models.comentario import Comentario
from app.models.criterio import Criterio
from app.models.evaluacion import Evaluacion, RondaEvaluacion
from app.models.filtro_guardado import FiltroGuardado
from app.models.invitacion import Invitacion
from app.models.notificacion import Notificacion
from app.models.organization import Organization
from app.models.sector import Sector
from app.models.user import User
from seed import sembrar

# Orden de borrado: hijos antes que padres, para no chocar con las
# foreign keys (aunque la mayoría son ON DELETE CASCADE, ser explícitos
# acá deja el orden documentado y no depende de que cada FK tenga cascade).
_TABLAS_EN_ORDEN_DE_BORRADO = [
    Evaluacion,
    RondaEvaluacion,
    Comentario,
    Notificacion,
    FiltroGuardado,
    ApiKey,
    AuditLog,
    Invitacion,
    Sector,
    Criterio,
    User,
    Organization,
]


def resetear() -> None:
    if os.environ.get("ES_INSTANCIA_DEMO") != "si":
        print(
            "Este script borra TODOS los datos de la base a la que apunte DATABASE_URL.\n"
            "Para evitar correrlo por accidente contra una base que no es la de la demo "
            "pública, requiere ES_INSTANCIA_DEMO=si:\n"
            "  ES_INSTANCIA_DEMO=si python reset_demo.py",
            file=sys.stderr,
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        for modelo in _TABLAS_EN_ORDEN_DE_BORRADO:
            db.query(modelo).delete()
        db.commit()

        raw_key = sembrar(db)
        print(f"Demo reseteada. Nueva API key de ejemplo: {raw_key}")
    finally:
        db.close()


if __name__ == "__main__":
    resetear()
