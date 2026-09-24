"""Schemas de administración de cuentas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserAdminOut(BaseModel):
    """Una cuenta tal como la ve un administrador."""

    id: int
    name: str
    email: EmailStr
    role: str
    agent_id: int | None = None
    active: bool = True
    is_readonly: bool = False
    created_at: datetime | None = None
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    """Alta de una cuenta. Sin contraseña, se genera y se muestra una vez."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: str
    password: str | None = None
    agent_id: int | None = None


class UserUpdateRequest(BaseModel):
    """
    Cambios sobre una cuenta.

    Todo es opcional: lo que no se envía no se toca. `agent_id` distingue entre
    "no lo toques" (ausente) y "déjalo vacío" (null), por eso se lee del JSON
    crudo en el router.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None
    active: bool | None = None
    agent_id: int | None = None


class UserCreatedOut(BaseModel):
    """Respuesta del alta: la cuenta y, si se generó, su contraseña inicial."""

    user: UserAdminOut
    # Solo viaja en esta respuesta y no se puede volver a consultar.
    generated_password: str | None = None


class PasswordResetOut(BaseModel):
    """Contraseña nueva tras un reseteo. Se muestra una sola vez."""

    password: str


class ChangePasswordRequest(BaseModel):
    """Cambio de contraseña por el propio usuario."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)
