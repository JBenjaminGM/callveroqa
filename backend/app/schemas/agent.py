"""Schemas de ejecutivos (agents)."""

from datetime import date

from pydantic import BaseModel, EmailStr, Field


class AgentBase(BaseModel):
    """Campos comunes de un ejecutivo."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    campaign: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    photo_url: str | None = None


class AgentCreate(AgentBase):
    """Datos para crear un ejecutivo."""

    pass


class AgentUpdate(BaseModel):
    """Datos para actualizar un ejecutivo (todos los campos opcionales)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    campaign: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    photo_url: str | None = None
    active: bool | None = None


class AgentOut(AgentBase):
    """Representación de un ejecutivo en las respuestas."""

    id: int
    active: bool

    model_config = {"from_attributes": True}


class AgentDetailOut(AgentOut):
    """Ejecutivo con estadísticas agregadas."""

    total_calls: int = 0
    average_score: float | None = None


class AgentCreatedOut(AgentOut):
    """Ejecutivo recién creado, con el nº de llamadas que se le vincularon."""

    linked_calls: int = 0


class AgentLoginCreate(BaseModel):
    """Datos para crear la cuenta de acceso (asesor) de un ejecutivo."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=255)


class DataErasureOut(BaseModel):
    """Recuento de lo suprimido, para poder registrarlo donde haga falta."""

    agent_id: int
    calls_deleted: int
    audios_deleted: int
