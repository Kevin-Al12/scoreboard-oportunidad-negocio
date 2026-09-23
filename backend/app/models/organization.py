from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Organization(Base):
    """Tenant — aísla los datos de un equipo/empresa del resto (multi-tenancy)."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    # Por organización, NO global -- un solo webhook global mandaría las
    # notificaciones de todas las organizaciones al mismo canal de Slack,
    # mezclando nombres de sectores/usuarios de empresas distintas.
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
