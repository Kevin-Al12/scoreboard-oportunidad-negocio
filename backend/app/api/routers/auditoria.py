from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.criterio import Criterio
from app.models.evaluacion import Evaluacion
from app.models.user import Role, User
from app.schemas.audit import AuditLogOut
from app.services.auditoria import CAMPOS_REVERTIBLES

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


def _es_revertible(entrada: AuditLog) -> bool:
    return not entrada.revertido and (entrada.entidad, entrada.campo) in CAMPOS_REVERTIBLES


@router.get("", response_model=list[AuditLogOut])
def listar_auditoria(
    entidad: str | None = None,
    entidad_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).filter(AuditLog.organization_id == usuario.organization_id)
    if entidad:
        query = query.filter(AuditLog.entidad == entidad)
    if entidad_id is not None:
        query = query.filter(AuditLog.entidad_id == entidad_id)

    filas = query.order_by(AuditLog.creado_en.desc()).offset(offset).limit(limit).all()

    usuarios_por_id = {u.id: u.nombre_completo for u in db.query(User).filter(User.organization_id == usuario.organization_id)}

    resultado = []
    for f in filas:
        item = AuditLogOut.model_validate(f)
        item.revertible = _es_revertible(f)
        item.usuario_nombre = usuarios_por_id.get(f.user_id, "—") if f.user_id else "Sistema"
        resultado.append(item)
    return resultado


@router.post("/{audit_id}/revertir", response_model=AuditLogOut)
def revertir_cambio(
    audit_id: int,
    usuario: User = Depends(require_role(Role.admin, Role.editor)),
    db: Session = Depends(get_db),
):
    entrada = db.get(AuditLog, audit_id)
    if not entrada or entrada.organization_id != usuario.organization_id:
        raise HTTPException(404, "Registro de auditoría no encontrado")
    if not _es_revertible(entrada):
        raise HTTPException(422, "Este cambio no se puede revertir automáticamente")

    caster = CAMPOS_REVERTIBLES[(entrada.entidad, entrada.campo)]
    valor_a_restaurar = caster(entrada.valor_anterior) if entrada.valor_anterior is not None else None

    if entrada.entidad == "criterio":
        objetivo = db.get(Criterio, entrada.entidad_id)
    elif entrada.entidad == "evaluacion":
        objetivo = db.get(Evaluacion, entrada.entidad_id)
    else:
        objetivo = None

    if objetivo is None:
        raise HTTPException(404, "El registro original ya no existe (fue borrado)")

    valor_actual = getattr(objetivo, entrada.campo)
    setattr(objetivo, entrada.campo, valor_a_restaurar)
    entrada.revertido = True

    # La reversión ES un cambio -- se audita igual que cualquier otro, para
    # que el historial diga "quién revirtió qué" en vez de dejar un salto
    # silencioso en los valores.
    db.add(
        AuditLog(
            organization_id=usuario.organization_id,
            user_id=usuario.id,
            entidad=entrada.entidad,
            entidad_id=entrada.entidad_id,
            campo=entrada.campo,
            valor_anterior=None if valor_actual is None else str(valor_actual),
            valor_nuevo=None if valor_a_restaurar is None else str(valor_a_restaurar),
        )
    )

    db.commit()
    db.refresh(entrada)

    salida = AuditLogOut.model_validate(entrada)
    salida.revertible = False
    return salida
