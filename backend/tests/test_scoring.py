import pytest

from app.core.scoring import Calificacion, Criterio, ScoringError, calcular_score

CRITERIOS = [
    Criterio(id=1, nombre="Tamaño de mercado", peso=0.20),
    Criterio(id=2, nombre="Nivel de saturación", peso=0.25),
    Criterio(id=3, nombre="Tendencia de crecimiento", peso=0.20),
    Criterio(id=4, nombre="Barreras de entrada", peso=0.15),
    Criterio(id=5, nombre="Complejidad regulatoria", peso=0.10),
    Criterio(id=6, nombre="Capital requerido", peso=0.10),
]


def test_score_maximo_da_100():
    calificaciones = [Calificacion(criterio_id=c.id, valor=5) for c in CRITERIOS]
    resultado = calcular_score(calificaciones, CRITERIOS)
    assert resultado.score_1_a_5 == 5.0
    assert resultado.score_0_a_100 == 100.0


def test_score_minimo_da_0():
    calificaciones = [Calificacion(criterio_id=c.id, valor=1) for c in CRITERIOS]
    resultado = calcular_score(calificaciones, CRITERIOS)
    assert resultado.score_1_a_5 == 1.0
    assert resultado.score_0_a_100 == 0.0


def test_calculo_ponderado_manual():
    # Réplica manual del cálculo esperado para valores mixtos.
    valores = {1: 3, 2: 4, 3: 4, 4: 4, 5: 5, 6: 4}
    calificaciones = [Calificacion(criterio_id=k, valor=v) for k, v in valores.items()]
    resultado = calcular_score(calificaciones, CRITERIOS)

    esperado_1_a_5 = sum(c.peso * valores[c.id] for c in CRITERIOS)  # pesos ya suman 1.0
    assert resultado.score_1_a_5 == pytest.approx(esperado_1_a_5, abs=1e-6)

    esperado_0_a_100 = (esperado_1_a_5 - 1) / 4 * 100
    assert resultado.score_0_a_100 == pytest.approx(esperado_0_a_100, abs=1e-2)


def test_pesos_se_normalizan_aunque_no_sumen_1():
    # Mismos pesos relativos que CRITERIOS pero escalados x10 (no suman 1.0).
    criterios_sin_normalizar = [
        Criterio(id=c.id, nombre=c.nombre, peso=c.peso * 10) for c in CRITERIOS
    ]
    valores = {1: 3, 2: 4, 3: 4, 4: 4, 5: 5, 6: 4}
    calificaciones = [Calificacion(criterio_id=k, valor=v) for k, v in valores.items()]

    resultado_normal = calcular_score(calificaciones, CRITERIOS)
    resultado_escalado = calcular_score(calificaciones, criterios_sin_normalizar)

    assert resultado_normal.score_1_a_5 == pytest.approx(resultado_escalado.score_1_a_5)
    assert resultado_normal.score_0_a_100 == pytest.approx(resultado_escalado.score_0_a_100)


def test_falta_calificacion_lanza_error():
    calificaciones = [Calificacion(criterio_id=c.id, valor=3) for c in CRITERIOS[:-1]]
    with pytest.raises(ScoringError, match="Faltan calificaciones"):
        calcular_score(calificaciones, CRITERIOS)


def test_calificacion_de_criterio_inexistente_lanza_error():
    calificaciones = [Calificacion(criterio_id=c.id, valor=3) for c in CRITERIOS]
    calificaciones.append(Calificacion(criterio_id=999, valor=3))
    with pytest.raises(ScoringError, match="criterios inexistentes"):
        calcular_score(calificaciones, CRITERIOS)


def test_calificacion_duplicada_lanza_error():
    calificaciones = [Calificacion(criterio_id=c.id, valor=3) for c in CRITERIOS]
    calificaciones.append(Calificacion(criterio_id=CRITERIOS[0].id, valor=5))
    with pytest.raises(ScoringError, match="duplicadas"):
        calcular_score(calificaciones, CRITERIOS)


@pytest.mark.parametrize("valor_invalido", [0, 6, -1, 3.5])
def test_calificacion_fuera_de_rango_lanza_error(valor_invalido):
    with pytest.raises(ScoringError):
        Calificacion(criterio_id=1, valor=valor_invalido)


def test_criterio_con_peso_no_positivo_lanza_error():
    with pytest.raises(ScoringError):
        Criterio(id=1, nombre="Peso inválido", peso=0)


def test_sin_criterios_lanza_error():
    with pytest.raises(ScoringError, match="al menos un criterio"):
        calcular_score([], [])


def test_resumen_texto_incluye_top_criterios():
    valores = {1: 3, 2: 4, 3: 4, 4: 4, 5: 5, 6: 4}
    calificaciones = [Calificacion(criterio_id=k, valor=v) for k, v in valores.items()]
    resultado = calcular_score(calificaciones, CRITERIOS)
    assert "Criterios que más destacan" in resultado.resumen_texto()
