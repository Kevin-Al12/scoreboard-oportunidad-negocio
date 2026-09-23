from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.services.conectores.banco_mundial import obtener_contexto_macro

router = APIRouter(prefix="/contexto-mercado", tags=["contexto-mercado"])


@router.get("/indicadores-macro")
def indicadores_macro(usuario: User = Depends(get_current_user)):
    """Indicadores macro reales de RD (Banco Mundial, API pública) para dar
    contexto al análisis de oportunidad. Ver app/services/conectores/ para
    el patrón a seguir si se conecta una fuente de datos de mercado paga."""
    return obtener_contexto_macro()
