"""Puente entre los modelos de base de datos y el motor de scoring puro.

Toda la aritmética del score vive en app.core.scoring (testeada de forma
aislada). Este módulo solo se encarga de traducir filas de SQLAlchemy en
las dataclasses que ese motor espera, y de decidir qué ronda es "la
última" de cada sector.
"""

from sqlalchemy.orm import Session

from app.core.scoring import Calificacion, Criterio as CriterioDTO, ResultadoScore, calcular_score
from app.models.criterio import Criterio
from app.models.evaluacion import RondaEvaluacion


def calcular_score_de_ronda(ronda: RondaEvaluacion, criterios_activos: list[Criterio]) -> ResultadoScore:
    """Calcula el score de una ronda usando únicamente los criterios activos.

    Si la ronda tiene calificaciones para criterios que ya no están activos,
    se ignoran: el score debe reflejar el método de scoring vigente, no el
    histórico de criterios que existían cuando se evaluó.
    """
    ids_activos = {c.id for c in criterios_activos}
    calificaciones = [
        Calificacion(criterio_id=e.criterio_id, valor=e.calificacion, notas=e.notas or "")
        for e in ronda.evaluaciones
        if e.criterio_id in ids_activos
    ]
    criterios_dto = [
        CriterioDTO(id=c.id, nombre=c.nombre, peso=c.peso, descripcion=c.descripcion or "")
        for c in criterios_activos
    ]
    return calcular_score(calificaciones, criterios_dto)


def obtener_criterios_activos(db: Session, organization_id: int) -> list[Criterio]:
    return (
        db.query(Criterio)
        .filter(Criterio.activo.is_(True), Criterio.organization_id == organization_id)
        .order_by(Criterio.orden, Criterio.id)
        .all()
    )


def ultima_ronda_de(sector) -> RondaEvaluacion | None:
    if not sector.rondas_evaluacion:
        return None
    return max(sector.rondas_evaluacion, key=lambda r: (r.fecha, r.id))
