from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.scoring import ScoringError
from app.db.session import get_db
from app.models.evaluacion import RondaEvaluacion
from app.models.sector import Sector
from app.models.user import User
from app.services.pdf_service import SectorParaReporte, generar_pdf_top_sectores
from app.services.scoring_service import calcular_score_de_ronda, obtener_criterios_activos, ultima_ronda_de

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/top-sectores.pdf")
def reporte_top_sectores(
    n: int = Query(default=5, ge=1, le=50),
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """PDF con el top N de sectores por score, su detalle por criterio y sus notas.

    Requiere autenticación (JWT o X-API-Key) igual que el resto de la API,
    por eso el frontend lo descarga con `fetch` + Blob en vez de un link
    directo: un <a href> normal no puede mandar el header Authorization.
    """
    criterios_activos = obtener_criterios_activos(db, usuario.organization_id)
    sectores = (
        db.query(Sector)
        .filter(Sector.organization_id == usuario.organization_id)
        .options(joinedload(Sector.rondas_evaluacion).joinedload(RondaEvaluacion.evaluaciones))
        .all()
    )

    candidatos: list[SectorParaReporte] = []
    for sector in sectores:
        ronda = ultima_ronda_de(sector)
        if ronda is None:
            continue
        try:
            resultado = calcular_score_de_ronda(ronda, criterios_activos)
        except ScoringError:
            continue
        candidatos.append(
            SectorParaReporte(
                nombre=sector.nombre,
                descripcion=sector.descripcion,
                notas=sector.notas,
                fecha_evaluacion=ronda.fecha,
                resultado=resultado,
            )
        )

    candidatos.sort(key=lambda s: s.resultado.score_0_a_100, reverse=True)
    top = candidatos[:n]

    pdf_bytes = generar_pdf_top_sectores(top)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=top-sectores.pdf"},
    )
