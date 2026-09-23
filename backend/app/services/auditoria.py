"""Registro de auditoría: quién cambió qué campo, cuándo, y de qué valor a cuál.

Se guarda un registro POR CAMPO modificado (no un diff de todo el objeto),
para que revertir uno no arriesgue pisar otro cambio hecho después sobre el
mismo registro.
"""

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def registrar_cambios(
    db: Session,
    organization_id: int,
    user_id: int | None,
    entidad: str,
    entidad_id: int,
    cambios: dict[str, tuple[object, object]],
) -> list[AuditLog]:
    """`cambios` es {campo: (valor_anterior, valor_nuevo)}. Solo registra los que de verdad cambiaron."""
    entradas = []
    for campo, (anterior, nuevo) in cambios.items():
        if anterior == nuevo:
            continue
        entrada = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            entidad=entidad,
            entidad_id=entidad_id,
            campo=campo,
            valor_anterior=None if anterior is None else str(anterior),
            valor_nuevo=None if nuevo is None else str(nuevo),
        )
        db.add(entrada)
        entradas.append(entrada)
    if entradas:
        db.commit()
    return entradas


# Campos que se pueden revertir automáticamente: (modelo, tipo de casteo).
# Deliberadamente acotado -- revertir un campo de texto libre o una relación
# es ambiguo (¿y si hubo dos cambios después?), así que solo se ofrece
# reversión automática para campos numéricos simples y bien acotados donde
# "volver al valor anterior" es inequívoco.
CAMPOS_REVERTIBLES = {
    ("criterio", "peso"): float,
    ("criterio", "activo"): lambda v: v == "True",
    ("evaluacion", "calificacion"): int,
}
