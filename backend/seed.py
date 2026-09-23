"""Carga datos de ejemplo: organización, usuarios de los 3 roles, 6 criterios,
8 sectores dominicanos con 2-3 rondas de evaluación cada uno (para que el
histórico y los gráficos de evolución se vean con datos reales), y un
ejemplo de cada feature nueva (comentario con mención, notificación, filtro
guardado, API key).

Los sectores y sus notas son observaciones cualitativas de campo, no datos
oficiales -- donde se menciona una cifra, está marcada explícitamente como
estimación informal de los propios operadores, nunca como estadística
oficial (ver `fuentes_informacion` de cada uno).

Se usa pandas para armar y validar la tabla de calificaciones antes de
insertarla -- el cálculo del score en sí sigue viviendo exclusivamente en
app.core.scoring.

Ejecutar con:
    python seed.py

Es idempotente: si ya existe la organización, no duplica nada. La lógica de
inserción en sí vive en `sembrar()`, reutilizada por reset_demo.py (el cron
que resetea la instancia de demo pública cada noche).
"""

import os
import sys
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.comentario import Comentario
from app.models.criterio import Criterio
from app.models.evaluacion import Evaluacion, RondaEvaluacion
from app.models.filtro_guardado import FiltroGuardado
from app.models.notificacion import Notificacion
from app.models.organization import Organization
from app.models.sector import Sector
from app.models.user import Role, User
from app.services.api_keys import generar_api_key

NOMBRE_ORG = "Acme Analytics RD"

USUARIOS = [
    ("admin@acme-analytics.do", "Admin123!", "Ana Administradora", Role.admin),
    ("editor@acme-analytics.do", "Editor123!", "Eddy Editor", Role.editor),
    # Cuenta de demo pública de solo lectura -- ver README. Un viewer no
    # puede crear/editar/borrar nada (aplicado por rol en el backend, no
    # solo escondido en el frontend), así que compartir esta contraseña no
    # arriesga los datos de la demo más allá de lo que un reset nocturno ya
    # asume.
    ("viewer@acme-analytics.do", "Viewer123!", "Vicky Viewer", Role.viewer),
]

CRITERIOS = [
    ("Tamaño de mercado", 0.20, "Qué tan grande es la demanda potencial en RD."),
    ("Nivel de saturación", 0.25, "5 = baja saturación (poca competencia establecida)."),
    ("Tendencia de crecimiento", 0.20, "5 = tendencia de crecimiento fuerte y sostenida."),
    ("Barreras de entrada", 0.15, "5 = barreras bajas (fácil de empezar)."),
    ("Complejidad regulatoria", 0.10, "5 = baja complejidad (pocos permisos/trámites)."),
    ("Capital requerido", 0.10, "5 = capital inicial bajo."),
]

_NOMBRES_CRITERIOS = [c[0] for c in CRITERIOS]

# Cada sector trae 2-3 rondas de evaluación en fechas distintas, con notas
# que explican POR QUÉ cambió la calificación de una ronda a la siguiente
# -- eso es lo que hace que el histórico cuente algo, no solo números.
SECTORES = [
    {
        "nombre": "Delivery de comida directo (sin apps grandes) en Santo Domingo",
        "descripcion": "Reparto de comida preparada a domicilio en el Gran Santo Domingo, "
        "por fuera de las apps grandes: pedidos directos por WhatsApp/Instagram, con moto propia.",
        "fuentes_informacion": "Conversaciones con 4 dueños de restaurantes en Piantini y Naco "
        "(jul-2025) y observación de grupos de Facebook de delivery independiente. Sin cifras oficiales.",
        "responsable": True,
        "rondas": [
            ("2025-06-01", "Primera mirada: mucha demanda, pero casi todo pasa por PedidosYa/Uber Eats, "
             "que se llevan 25-30% de comisión.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 4, "Complejidad regulatoria": 3, "Capital requerido": 4}),
            ("2025-10-01", "Varios restaurantes están migrando a pedidos directos para evitar la comisión; "
             "la oportunidad real es dar la infraestructura (catálogo + cobro), no ser 'una app de reparto más'.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 3, "Tendencia de crecimiento": 5,
              "Barreras de entrada": 4, "Complejidad regulatoria": 3, "Capital requerido": 4}),
            ("2026-02-01", "Ya aparecieron 2-3 competidores locales ofreciendo lo mismo (catálogo + WhatsApp "
             "Business). Sigue siendo el mejor del batch, pero la ventana se está cerrando.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 5,
              "Barreras de entrada": 3, "Complejidad regulatoria": 3, "Capital requerido": 4}),
        ],
    },
    {
        "nombre": "Turismo comunitario en Samaná (avistamiento de ballenas)",
        "descripcion": "Paquetes operados por cooperativas locales: avistamiento de ballenas jorobadas, "
        "cabañas rurales y gastronomía local en Las Galeras.",
        "fuentes_informacion": "Visita de campo a Samaná (ago-2025) y conversación con la cooperativa de "
        "guías de Las Galeras. Las cifras de temporada son estimaciones informales de los propios "
        "operadores, no datos oficiales de Turismo.",
        "responsable": True,
        "rondas": [
            ("2025-08-01", "Muy dependiente de la temporada de ballenas (enero-marzo). Fuera de temporada "
             "el flujo cae mucho.",
             {"Tamaño de mercado": 3, "Nivel de saturación": 4, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 2, "Complejidad regulatoria": 2, "Capital requerido": 3}),
            ("2025-12-01", "Según la cooperativa, las reservas para la temporada 2026 ya superan las del "
             "año anterior (estimación informal de ellos mismos, no hay conteo oficial).",
             {"Tamaño de mercado": 4, "Nivel de saturación": 4, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 2, "Complejidad regulatoria": 2, "Capital requerido": 3}),
            ("2026-03-01", "Cerró la temporada alta con buena ocupación según los guías; también entraron "
             "dos operadores nuevos vía Airbnb Experiences usando el mismo circuito.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 3, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 2, "Complejidad regulatoria": 2, "Capital requerido": 3}),
        ],
    },
    {
        "nombre": "Reparación de celulares y electrónica de consumo",
        "descripcion": "Talleres de reparación de pantallas, baterías y placas para smartphones y laptops.",
        "fuentes_informacion": "Recorrido por talleres en la Duarte y Plaza Lama (sep-2025) y un grupo de "
        "Facebook de técnicos de electrónica de RD.",
        "responsable": False,
        "rondas": [
            ("2025-09-01", "La barrera real no es el capital, es conseguir repuestos originales/buenos a "
             "tiempo -- casi todo se importa.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 4, "Complejidad regulatoria": 5, "Capital requerido": 4}),
            ("2026-01-01", "El costo de piezas importadas subió con el tipo de cambio; varios talleres "
             "reportan márgenes más ajustados que hace unos meses.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 4, "Complejidad regulatoria": 5, "Capital requerido": 3}),
        ],
    },
    {
        "nombre": "Digitalización de colmados (catálogo + cobro digital)",
        "descripcion": "Servicio para colmados tradicionales: catálogo por WhatsApp/app simple, cobro "
        "digital y delivery de barrio -- no es abrir un colmado nuevo, es venderle tecnología a los que ya existen.",
        "fuentes_informacion": "Entrevistas con 3 colmaderos en Los Mina y Herrera (oct-2025).",
        "responsable": False,
        "rondas": [
            ("2025-10-15", "El colmado como negocio está saturadísimo (hay uno en cada cuadra), pero eso "
             "no es lo que se está evaluando -- es el SERVICIO de digitalización sobre colmados existentes.",
             {"Tamaño de mercado": 5, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 3, "Complejidad regulatoria": 4, "Capital requerido": 3}),
            ("2026-02-15", "Reenfocada la evaluación hacia el servicio de digitalización: muy pocos "
             "colmados ya están digitalizados, así que ESE nicho específico está mucho menos saturado.",
             {"Tamaño de mercado": 5, "Nivel de saturación": 3, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 3, "Complejidad regulatoria": 4, "Capital requerido": 3}),
        ],
    },
    {
        "nombre": "Traslados turísticos privados (aeropuerto - Punta Cana/Samaná)",
        "descripcion": "Transporte privado puerta a puerta para turistas, alternativa a los tours "
        "organizados de las agencias grandes.",
        "fuentes_informacion": "Cotizaciones de 5 operadores existentes vía Instagram (nov-2025). No se "
        "consultó ninguna estadística oficial de pasajeros.",
        "responsable": False,
        "rondas": [
            ("2025-11-01", "Muy competido en precio; diferenciarse por servicio (inglés, puntualidad, "
             "vehículo nuevo) parece el único ángulo viable.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 3, "Complejidad regulatoria": 3, "Capital requerido": 2}),
            ("2026-03-01", "Sin cambios grandes respecto a noviembre: sector estable pero muy peleado en precio.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 3, "Complejidad regulatoria": 3, "Capital requerido": 2}),
        ],
    },
    {
        "nombre": "Cacao orgánico artesanal ('bean to bar')",
        "descripcion": "Producción y venta de chocolate artesanal a partir de cacao orgánico dominicano, "
        "para mercado local premium y exportación en pequeña escala.",
        "fuentes_informacion": "Conversación con un productor en San Francisco de Macorís (may-2025) y "
        "observación en ferias de emprendimiento en Santo Domingo.",
        "responsable": False,
        "rondas": [
            ("2025-05-01", "El cacao como materia prima abunda y es de buena calidad; el cuello de "
             "botella real es el procesamiento y el acceso a mercados de exportación.",
             {"Tamaño de mercado": 2, "Nivel de saturación": 4, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 2, "Complejidad regulatoria": 3, "Capital requerido": 2}),
            ("2025-12-01", "Un par de tiendas gourmet en Santo Domingo empezaron a vender marcas locales -- "
             "señal de demanda creciendo, aunque sigue siendo un nicho pequeño.",
             {"Tamaño de mercado": 3, "Nivel de saturación": 4, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 2, "Complejidad regulatoria": 3, "Capital requerido": 2}),
        ],
    },
    {
        "nombre": "Limpieza y mantenimiento de propiedades Airbnb",
        "descripcion": "Servicio de limpieza, lavandería y mantenimiento entre huéspedes para anfitriones "
        "de Airbnb en Las Terrenas, Punta Cana y Santo Domingo.",
        "fuentes_informacion": "Grupo de Facebook de anfitriones de Airbnb RD y conversación con 2 "
        "administradores de propiedades en Las Terrenas (sep-2025).",
        "responsable": False,
        "rondas": [
            ("2025-09-15", "La demanda existe pero está muy fragmentada -- cada anfitrión resuelve por su "
             "cuenta. Hay espacio para un servicio confiable y estandarizado.",
             {"Tamaño de mercado": 3, "Nivel de saturación": 3, "Tendencia de crecimiento": 5,
              "Barreras de entrada": 4, "Complejidad regulatoria": 4, "Capital requerido": 4}),
            ("2026-01-15", "La temporada alta trajo más consultas de anfitriones nuevos buscando un "
             "servicio recurrente, no solo limpiezas sueltas.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 3, "Tendencia de crecimiento": 5,
              "Barreras de entrada": 4, "Complejidad regulatoria": 4, "Capital requerido": 4}),
            ("2026-04-01", "Empezaron a aparecer 2 administradoras de propiedades más grandes empaquetando "
             "este servicio, lo que sube la barrera de competir por separado.",
             {"Tamaño de mercado": 4, "Nivel de saturación": 2, "Tendencia de crecimiento": 4,
              "Barreras de entrada": 3, "Complejidad regulatoria": 4, "Capital requerido": 4}),
        ],
    },
    {
        "nombre": "Clases de kitesurf y deportes acuáticos en Cabarete",
        "descripcion": "Escuela de kitesurf/windsurf para turistas y locales en la zona de Cabarete/Encuentro.",
        "fuentes_informacion": "Visita a Cabarete y conversación con 2 instructores independientes (jun-2025).",
        "responsable": False,
        "rondas": [
            ("2025-06-15", "Cabarete ya tiene marca internacional en kitesurf, lo que ayuda a la demanda "
             "pero también significa competencia establecida desde hace años.",
             {"Tamaño de mercado": 2, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 2, "Complejidad regulatoria": 4, "Capital requerido": 1}),
            ("2025-11-15", "Entrando la temporada alta de viento hay más turistas probando la actividad, "
             "pero la mayoría de las escuelas grandes ya tienen su clientela recurrente vía hoteles aliados.",
             {"Tamaño de mercado": 3, "Nivel de saturación": 2, "Tendencia de crecimiento": 3,
              "Barreras de entrada": 2, "Complejidad regulatoria": 4, "Capital requerido": 1}),
        ],
    },
]


def _parece_base_de_desarrollo(database_url: str) -> bool:
    return database_url.startswith("sqlite") or any(
        marca in database_url for marca in ("localhost", "127.0.0.1", "@db:", "@postgres:")
    )


def sembrar(db: Session) -> str:
    """Inserta organización + usuarios + criterios + sectores (con su
    histórico de rondas) + un ejemplo de cada feature corporativa. Asume
    que la base ya está vacía de esta organización -- no chequea
    duplicados (eso lo hace `seed()`, o el caller para el caso del reset).

    Devuelve la API key de ejemplo generada (para imprimirla en consola).
    """
    org = Organization(nombre=NOMBRE_ORG)
    db.add(org)
    db.commit()
    db.refresh(org)

    usuarios = {}
    for email, password, nombre, role in USUARIOS:
        u = User(
            organization_id=org.id,
            email=email,
            hashed_password=hash_password(password),
            nombre_completo=nombre,
            role=role,
        )
        db.add(u)
        usuarios[role] = u
    db.commit()
    for u in usuarios.values():
        db.refresh(u)
    admin, editor, viewer = usuarios[Role.admin], usuarios[Role.editor], usuarios[Role.viewer]

    criterios = [
        Criterio(organization_id=org.id, nombre=nombre, peso=peso, descripcion=desc, orden=i)
        for i, (nombre, peso, desc) in enumerate(CRITERIOS)
    ]
    db.add_all(criterios)
    db.commit()
    for c in criterios:
        db.refresh(c)
    criterio_por_nombre = {c.nombre: c for c in criterios}

    # DataFrame para validar la forma de los datos ANTES de insertar: una
    # fila por (sector, ronda), una columna por criterio -- así un typo
    # (calificación fuera de 1-5, o un criterio con el nombre mal escrito)
    # revienta acá con un mensaje claro, en vez de silenciosamente.
    filas_validacion = [
        {"sector": s["nombre"], "fecha": fecha, **calificaciones}
        for s in SECTORES
        for fecha, _, calificaciones in s["rondas"]
    ]
    df = pd.DataFrame(filas_validacion)
    assert df[_NOMBRES_CRITERIOS].isin([1, 2, 3, 4, 5]).all().all(), "Hay calificaciones fuera de 1-5 en el seed"
    assert df[_NOMBRES_CRITERIOS].notna().all().all(), "Faltan calificaciones en alguna ronda del seed"
    assert set(df.columns) - {"sector", "fecha"} == set(_NOMBRES_CRITERIOS), "Un criterio del seed no matchea CRITERIOS"

    sectores_creados = []
    for s in SECTORES:
        sector = Sector(
            organization_id=org.id,
            creado_por_id=admin.id,
            responsable_id=editor.id if s["responsable"] else None,
            nombre=s["nombre"],
            descripcion=s["descripcion"],
            notas=s["rondas"][-1][1],  # la nota de la evaluación más reciente, como resumen del sector
            fuentes_informacion=s["fuentes_informacion"],
        )
        for fecha, notas_ronda, calificaciones in s["rondas"]:
            ronda = RondaEvaluacion(fecha=date.fromisoformat(fecha), notas=notas_ronda, creado_por_id=admin.id)
            for nombre_criterio, valor in calificaciones.items():
                ronda.evaluaciones.append(
                    Evaluacion(criterio_id=criterio_por_nombre[nombre_criterio].id, calificacion=valor)
                )
            sector.rondas_evaluacion.append(ronda)
        db.add(sector)
        sectores_creados.append(sector)

    db.commit()
    for s in sectores_creados:
        db.refresh(s)

    # --- Ejemplos de las features "corporativas" para que se vean con datos reales ---
    sector_estrella = sectores_creados[0]

    db.add(
        Comentario(
            sector_id=sector_estrella.id,
            user_id=admin.id,
            texto=f"@{editor.nombre_completo.split(' ')[0]} revisa este sector, parece el más prometedor del batch. "
            "¿Tienes más fuentes aparte de las conversaciones informales?",
            menciones_user_ids=[editor.id],
        )
    )
    db.add(
        Notificacion(
            user_id=editor.id,
            tipo="mencion",
            mensaje=f"Ana Administradora te mencionó en un comentario sobre '{sector_estrella.nombre}'",
            entidad_ref=f"sector:{sector_estrella.id}",
        )
    )
    db.add(FiltroGuardado(user_id=admin.id, nombre="Alta oportunidad", params={"min_score": 70}))
    db.commit()

    raw_key, _ = generar_api_key(db, admin, "Integración de ejemplo (seed)")
    return raw_key


def seed() -> None:
    # Este script crea usuarios con contraseñas conocidas y públicas
    # (Admin123!, etc. -- están hasta en el README). Si alguna vez se corre
    # sin querer contra una base que no parece de desarrollo, esas cuentas
    # quedarían activas y accesibles ahí.
    database_url = get_settings().database_url
    if not _parece_base_de_desarrollo(database_url) and os.environ.get("CONFIRMO_SEED_EN_ESTA_BASE") != "si":
        print(
            f"DATABASE_URL ('{database_url}') no parece una base de desarrollo local.\n"
            "seed.py crea usuarios con contraseñas de ejemplo PÚBLICAS (están en el README).\n"
            "Si de verdad querés sembrarlos ahí, corré de nuevo con:\n"
            "  CONFIRMO_SEED_EN_ESTA_BASE=si python seed.py\n"
            "(Para la instancia de demo pública, usá reset_demo.py en vez de este script.)",
            file=sys.stderr,
        )
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Organization).filter(Organization.nombre == NOMBRE_ORG).first() is not None:
            print(f"La organización '{NOMBRE_ORG}' ya existe, no se vuelve a sembrar.")
            return

        raw_key = sembrar(db)

        total_rondas = sum(len(s["rondas"]) for s in SECTORES)
        print(f"\nOrganización creada: {NOMBRE_ORG}")
        print("Usuarios de prueba (organización, rol -> email / contraseña):")
        for email, password, nombre, role in USUARIOS:
            print(f"  [{role.value:6s}] {nombre:20s} {email} / {password}")
        print(f"\nAPI key de ejemplo (admin) -- pruébala con X-API-Key: {raw_key}")
        print(f"Insertados {len(CRITERIOS)} criterios y {len(SECTORES)} sectores con {total_rondas} rondas de evaluación en total.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
