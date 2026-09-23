from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Sector(Base):
    """Un sector/nicho de negocio evaluado (ej. 'Lavado de autos a domicilio')."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Multi-tenancy: todo sector pertenece a una organización, y las
    # consultas siempre se filtran por la del usuario autenticado.
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Asignación: quién es responsable de darle seguimiento a este sector.
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notas: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fuentes_informacion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    rondas_evaluacion = relationship(
        "RondaEvaluacion", back_populates="sector", cascade="all, delete-orphan"
    )
