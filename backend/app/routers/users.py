"""
Administración de cuentas: quién entra a la plataforma y con qué permisos.

Todo aquí exige rol de gestión (`require_manager`). El cambio de la contraseña
propia vive en `auth`, porque lo hace cualquiera sobre su propia cuenta.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_manager
from app.models.user import User
from app.schemas.user import (
    PasswordResetOut,
    UserAdminOut,
    UserCreatedOut,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminOut])
def list_users(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Cuentas de la plataforma, las activas primero."""
    return [
        UserAdminOut.model_validate(u)
        for u in user_service.list_users(db, include_inactive=include_inactive)
    ]


@router.post("", response_model=UserCreatedOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Da de alta una cuenta.

    Si no se envía contraseña, se genera una y **se devuelve en esta respuesta y
    solo aquí**: no queda forma de volver a leerla.
    """
    user, generada = user_service.create_user(
        db,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password=payload.password,
        agent_id=payload.agent_id,
    )
    return UserCreatedOut(
        user=UserAdminOut.model_validate(user), generated_password=generada
    )


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Cambia nombre, rol, vínculo con un ejecutivo o estado de una cuenta."""
    user = user_service.get_user(db, user_id)
    actualizado = user_service.update_user(
        db,
        user,
        actor=current_user,
        name=payload.name,
        role=payload.role,
        active=payload.active,
        agent_id=payload.agent_id,
        # `model_fields_set` distingue "no lo toques" (ausente) de "déjalo
        # vacío" (null explícito), que en una baja de asesor no es lo mismo.
        agent_id_set="agent_id" in payload.model_fields_set,
    )
    return UserAdminOut.model_validate(actualizado)


@router.post("/{user_id}/reset-password", response_model=PasswordResetOut)
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Devuelve el acceso a quien perdió su contraseña.

    No hay correo saliente: la contraseña nueva se muestra una vez a quien la
    resetea, que es quien tiene que entregarla.
    """
    user = user_service.get_user(db, user_id)
    return PasswordResetOut(
        password=user_service.reset_password(db, user, actor=current_user)
    )
