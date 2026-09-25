"""Modelos de configuración: rúbrica de evaluación y settings globales."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    false as sa_false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Tipo JSON portable: JSONB en PostgreSQL, JSON genérico en otras BD (tests SQLite).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class RubricConfig(Base):
    """Una dimensión de la rúbrica de evaluación con su peso porcentual."""

    __tablename__ = "rubric_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    dimension_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # criteria: subcriterios/subcategorías de la dimensión, cada uno activable.
    # Formato: [{"name": str, "enabled": bool}]
    criteria: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)
    # weight: peso porcentual; la suma de todas las dimensiones debe ser 100.00
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    # «No aplica»: la dimensión puede no tener sentido en una llamada concreta
    # (no hubo objeciones que manejar, no era una llamada de venta). Si la IA la
    # marca así, no puntúa y su peso se reparte entre las demás, en vez de
    # contar como un cero que baja la nota por algo que el asesor no pudo hacer.
    allow_na: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false(), nullable=False
    )
    # Cuándo no aplica, en palabras del jefe. Se le pasa a la IA tal cual.
    na_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AppSettings(Base):
    """Pares clave-valor para configuración global (idioma, proveedor IA, etc.)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
