from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Notificacion(Base):
    """Notificación in-app. Los canales email/Slack son adaptadores opcionales
    (ver app/services/notificaciones.py) que se activan solo si hay
    credenciales configuradas; el registro in-app siempre se crea."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ej. "sector:3"
    leido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enviado_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enviado_slack: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
