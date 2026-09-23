from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Criterio(Base):
    """Criterio de evaluación con peso configurable (ej. 'Saturación de mercado', 25%).

    Los pesos se guardan y ajustan aquí, en base de datos -- no hardcodeados
    en el código -- para poder recalibrar el método de scoring sin deploy.
    El motor de scoring (app.core.scoring) normaliza los pesos activos antes
    de calcular, así que no hace falta que sumen exactamente 1.0 en todo
    momento (útil mientras se agregan/desactivan criterios).
    """

    __tablename__ = "criterios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    peso: Mapped[float] = mapped_column(Float, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
