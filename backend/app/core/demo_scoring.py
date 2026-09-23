"""
Demo manual del motor de scoring, sin API ni base de datos.

Ejecutar con:
    python -m app.core.demo_scoring

Sirve para validar visualmente que el cálculo hace lo que se espera
antes de construir cualquier capa encima.
"""

from app.core.scoring import Calificacion, Criterio, calcular_score

# Los pesos vienen de la propuesta del usuario. No hace falta que sumen
# exactamente 1.0 -- el motor los normaliza -- pero aquí sí suman 1.0
# (100%) para que sea fácil de leer.
CRITERIOS = [
    Criterio(id=1, nombre="Tamaño de mercado", peso=0.20),
    Criterio(id=2, nombre="Nivel de saturación", peso=0.25),
    Criterio(id=3, nombre="Tendencia de crecimiento", peso=0.20),
    Criterio(id=4, nombre="Barreras de entrada", peso=0.15),
    Criterio(id=5, nombre="Complejidad regulatoria", peso=0.10),
    Criterio(id=6, nombre="Capital requerido", peso=0.10),
]

# Nota de convención: en criterios como "saturación", "barreras",
# "complejidad regulatoria" y "capital requerido", un 5 debe
# interpretarse como "favorable a la oportunidad" (ej. baja
# saturación, bajas barreras, baja complejidad, bajo capital), no
# como "más cantidad". Así todos los criterios apuntan en la misma
# dirección: 5 siempre es mejor para el score.
ejemplos_sectores = {
    "Lavado de autos a domicilio": [
        Calificacion(criterio_id=1, valor=3, notas="Mercado mediano, concentrado en zonas urbanas"),
        Calificacion(criterio_id=2, valor=4, notas="Pocos operadores formales, mayormente informal"),
        Calificacion(criterio_id=3, valor=4, notas="Creciendo con el auge de apps de servicios a domicilio"),
        Calificacion(criterio_id=4, valor=4, notas="Barreras bajas, requiere poco equipo"),
        Calificacion(criterio_id=5, valor=5, notas="Sin regulación relevante"),
        Calificacion(criterio_id=6, valor=4, notas="Capital inicial bajo"),
    ],
    "Clínica de estética avanzada": [
        Calificacion(criterio_id=1, valor=4, notas="Mercado grande y en expansión en Santo Domingo"),
        Calificacion(criterio_id=2, valor=2, notas="Alta saturación en zonas premium"),
        Calificacion(criterio_id=3, valor=4, notas="Tendencia sostenida al alza"),
        Calificacion(criterio_id=4, valor=2, notas="Requiere personal certificado y equipos costosos"),
        Calificacion(criterio_id=5, valor=2, notas="Requiere permisos de salud y certificaciones"),
        Calificacion(criterio_id=6, valor=1, notas="Capital inicial alto (equipos, local)"),
    ],
}

if __name__ == "__main__":
    for nombre_sector, calificaciones in ejemplos_sectores.items():
        resultado = calcular_score(calificaciones, CRITERIOS)
        print(f"\n=== {nombre_sector} ===")
        print(f"Score (escala 1-5): {resultado.score_1_a_5}")
        print(f"Score (escala 0-100): {resultado.score_0_a_100}")
        print(resultado.resumen_texto())
        print("Detalle por criterio (ordenado por contribución):")
        for d in resultado.detalle:
            print(
                f"  - {d.criterio_nombre}: valor={d.valor}/5, "
                f"peso={d.peso_normalizado:.0%}, contribución={d.contribucion:.3f}"
            )
