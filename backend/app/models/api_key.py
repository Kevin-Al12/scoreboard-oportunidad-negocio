from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ApiKey(Base):
    """Clave para consumir la API pública sin sesión de usuario (integraciones).

    Solo se guarda el hash — la clave en texto plano se muestra una única
    vez al crearla, igual que en cualquier proveedor real (Stripe, GitHub…).
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    prefijo: Mapped[str] = mapped_column(String(12), nullable=False)  # para identificarla en la UI sin exponerla
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ultimo_uso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
