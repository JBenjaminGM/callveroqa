"""Modelo de usuario del sistema y roles de acceso."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    false as sa_false,
    func,
    true as sa_true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# --- Roles ---
# admin y jefe comparten permisos por ahora (acceso total de gestión y analítica);
# se diferenciarán en el futuro. El asesor solo accede a SU propio rendimiento.
ROLE_ADMIN = "admin"
ROLE_JEFE = "jefe"
ROLE_ASESOR = "asesor"
VALID_ROLES = {ROLE_ADMIN, ROLE_JEFE, ROLE_ASESOR}
# Roles con permisos de gestión/analítica global.
MANAGER_ROLES = {ROLE_ADMIN, ROLE_JEFE}


class User(Base):
    """Usuario que accede a la plataforma (administrador, jefe de área o asesor)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=ROLE_JEFE, nullable=False)
    # Vínculo del asesor con su ficha de ejecutivo: permite que vea solo sus
    # llamadas y su rendimiento. Para admin/jefe es NULL.
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    # Cuenta de solo lectura: puede ver toda la plataforma pero no modificar nada.
    # Pensada para la cuenta de demostración pública.
    is_readonly: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false(), nullable=False
    )
    # Cuenta activa. Dar de baja no borra: el historial de esa persona sigue
    # explicando los datos, pero la cuenta ya no puede entrar.
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa_true(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    agent: Mapped["Agent | None"] = relationship("Agent")  # noqa: F821

    @property
    def is_manager(self) -> bool:
        """True si el usuario tiene permisos de gestión/analítica global (admin o jefe)."""
        return self.role in MANAGER_ROLES
