"""
Motor de scoring de oportunidad de negocio.

Módulo puro: no depende de FastAPI, SQLAlchemy ni ninguna capa de
persistencia. Recibe estructuras de datos simples (dataclasses) y
devuelve un resultado calculado. Esto permite:

- Testearlo sin levantar base de datos ni servidor.
- Reutilizarlo desde la API, desde un script de seed, o desde una
  notebook de análisis, sin duplicar la lógica de negocio.

Reglas del cálculo
-------------------
1. Cada criterio tiene un peso (0 a 1, o cualquier número positivo).
   Los pesos NO necesitan sumar 1.0: el motor los normaliza antes de
   calcular, para que ajustar un peso en la config nunca rompa el
   cálculo ni obligue a que la suma cuadre exactamente.
2. Cada calificación es un entero de 1 a 5.
3. El score ponderado crudo queda en escala 1-5 (promedio ponderado
   de las calificaciones). Se reexpresa además en escala 0-100
   ((crudo - 1) / 4 * 100) porque es más intuitiva para comparar
   sectores en un ranking/dashboard.
4. Si falta la calificación de algún criterio activo, se lanza un
   error explícito en vez de asumir un valor por defecto: un score
   calculado sobre datos incompletos sería engañoso para decidir en
   qué sector invertir.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ScoringError(ValueError):
    """Error de validación de datos de entrada al motor de scoring."""


@dataclass(frozen=True)
class Criterio:
    id: int
    nombre: str
    peso: float
    descripcion: str = ""

    def __post_init__(self) -> None:
        if self.peso <= 0:
            raise ScoringError(
                f"El criterio '{self.nombre}' tiene peso no positivo: {self.peso}"
            )


@dataclass(frozen=True)
class Calificacion:
    criterio_id: int
    valor: int
    notas: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.valor, int) or not (1 <= self.valor <= 5):
            raise ScoringError(
                f"La calificación para criterio_id={self.criterio_id} debe ser un "
                f"entero entre 1 y 5, se recibió: {self.valor!r}"
            )


@dataclass(frozen=True)
class DetalleCriterio:
    criterio_id: int
    criterio_nombre: str
    valor: int
    peso_original: float
    peso_normalizado: float
    contribucion: float  # valor * peso_normalizado, en escala 1-5


@dataclass(frozen=True)
class ResultadoScore:
    score_1_a_5: float
    score_0_a_100: float
    detalle: list[DetalleCriterio] = field(default_factory=list)

    def resumen_texto(self) -> str:
        """Explicación breve de qué criterios más pesaron en el score, útil para el PDF."""
        top = sorted(self.detalle, key=lambda d: d.contribucion, reverse=True)[:3]
        partes = [f"{d.criterio_nombre} ({d.valor}/5)" for d in top]
        return "Criterios que más destacan: " + ", ".join(partes)


def calcular_score(
    calificaciones: list[Calificacion],
    criterios: list[Criterio],
) -> ResultadoScore:
    """Calcula el score ponderado de un sector a partir de sus calificaciones.

    Lanza ScoringError si:
    - hay criterios sin calificación correspondiente,
    - hay calificaciones para criterios que no existen en la lista de criterios,
    - hay calificaciones duplicadas para el mismo criterio.
    """
    if not criterios:
        raise ScoringError("Debe proveerse al menos un criterio para calcular el score.")

    criterios_por_id = {c.id: c for c in criterios}

    ids_calificados = [c.criterio_id for c in calificaciones]
    if len(ids_calificados) != len(set(ids_calificados)):
        raise ScoringError("Hay calificaciones duplicadas para el mismo criterio.")

    ids_desconocidos = set(ids_calificados) - set(criterios_por_id)
    if ids_desconocidos:
        raise ScoringError(
            f"Hay calificaciones para criterios inexistentes: {sorted(ids_desconocidos)}"
        )

    ids_faltantes = set(criterios_por_id) - set(ids_calificados)
    if ids_faltantes:
        nombres_faltantes = [criterios_por_id[i].nombre for i in sorted(ids_faltantes)]
        raise ScoringError(
            f"Faltan calificaciones para los criterios: {nombres_faltantes}"
        )

    peso_total = sum(c.peso for c in criterios)

    calificaciones_por_criterio = {c.criterio_id: c for c in calificaciones}

    detalle: list[DetalleCriterio] = []
    score_1_a_5 = 0.0
    for criterio in criterios:
        calificacion = calificaciones_por_criterio[criterio.id]
        peso_normalizado = criterio.peso / peso_total
        contribucion = calificacion.valor * peso_normalizado
        score_1_a_5 += contribucion
        detalle.append(
            DetalleCriterio(
                criterio_id=criterio.id,
                criterio_nombre=criterio.nombre,
                valor=calificacion.valor,
                peso_original=criterio.peso,
                peso_normalizado=peso_normalizado,
                contribucion=contribucion,
            )
        )

    score_0_a_100 = (score_1_a_5 - 1) / 4 * 100

    detalle.sort(key=lambda d: d.contribucion, reverse=True)

    return ResultadoScore(
        score_1_a_5=round(score_1_a_5, 3),
        score_0_a_100=round(score_0_a_100, 2),
        detalle=detalle,
    )
