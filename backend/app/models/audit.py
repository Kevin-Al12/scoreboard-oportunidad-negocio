from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditLog(Base):
    """Quién cambió qué, cuándo — un registro por campo modificado.

    Guardar valor_anterior/valor_nuevo como texto (en vez de un JSON de todo
    el objeto) es lo que permite revertir un cambio puntual sin arriesgar
    pisar otros campos que se hayan editado después.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    entidad: Mapped[str] = mapped_column(String(40), nullable=False)  # "sector" | "criterio" | "evaluacion"
    entidad_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    campo: Mapped[str] = mapped_column(String(80), nullable=False)
    valor_anterior: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(Text, nullable=True)

    revertido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
