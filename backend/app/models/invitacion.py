import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import Role


def _token() -> str:
    return secrets.token_urlsafe(24)


def _expira_en() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class Invitacion(Base):
    """Única forma real de unirse a una organización existente.

    Antes, registrarse con el nombre exacto de una organización ya existente
    bastaba para entrar a ella (como viewer) -- cualquiera que supiera el
    nombre de una empresa tenía acceso a sus sectores, notas y comentarios.
    Ahora unirse requiere un token que solo un admin de esa organización
    puede generar (ver POST /invitaciones), atado a un email y con
    expiración.
    """

    __tablename__ = "invitaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer, nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=_token)
    usada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_expira_en)
