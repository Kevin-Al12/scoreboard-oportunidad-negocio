from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RondaEvaluacion(Base):
    """Una 'pasada' completa de evaluación de un sector en una fecha dada.

    Agrupa las calificaciones por criterio de esa fecha, para poder:
    - calcular UN score por ronda (no por calificación suelta), y
    - reevaluar el mismo sector en una fecha distinta creando otra ronda,
      dejando el histórico completo para comparar cómo cambió el score.
    """

    __tablename__ = "rondas_evaluacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sector_id: Mapped[int] = mapped_column(
        ForeignKey("sectores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    notas: Mapped[str] = mapped_column(Text, default="", nullable=False)
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sector = relationship("Sector", back_populates="rondas_evaluacion")
    evaluaciones = relationship(
        "Evaluacion", back_populates="ronda", cascade="all, delete-orphan"
    )


class Evaluacion(Base):
    """Calificación (1-5) de un criterio específico dentro de una ronda de evaluación."""

    __tablename__ = "evaluaciones"
    __table_args__ = (
        UniqueConstraint("ronda_id", "criterio_id", name="uq_evaluacion_ronda_criterio"),
        CheckConstraint("calificacion >= 1 AND calificacion <= 5", name="ck_calificacion_1_a_5"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ronda_id: Mapped[int] = mapped_column(
        ForeignKey("rondas_evaluacion.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterio_id: Mapped[int] = mapped_column(
        ForeignKey("criterios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    calificacion: Mapped[int] = mapped_column(Integer, nullable=False)
    notas: Mapped[str] = mapped_column(Text, default="", nullable=False)

    ronda = relationship("RondaEvaluacion", back_populates="evaluaciones")
    criterio = relationship("Criterio")
