"""
Dependencias reutilizables de FastAPI.

La principal es `get_current_user`, que valida el JWT del header
Authorization y devuelve el usuario autenticado.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import ROLE_ADMIN, User
from app.utils.security import decode_access_token

# Esquema de autenticación tipo "Bearer <token>".
bearer_scheme = HTTPBearer(auto_error=False)

# Métodos que no cambian nada. Todo lo demás se considera escritura.
METODOS_DE_LECTURA = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Valida el token JWT y devuelve el usuario autenticado.

    Lanza 401 si el token falta, es inválido o el usuario ya no existe.
    """
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Inicie sesión para continuar.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise error

    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise error

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise error

    user = db.get(User, user_id)
    if user is None:
        raise error

    # Una baja tiene que cerrar la puerta ya, no cuando caduque su token: se
    # comprueba en cada petición, que es lo que hace real el "desactivar".
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está desactivada. Habla con un administrador.",
        )

    # Cuentas de solo lectura (la demo pública): pueden consultarlo todo, pero
    # cualquier método que escriba se rechaza aquí. Al vivir en la dependencia
    # que ya usan todos los endpoints autenticados, no hay forma de saltárselo
    # olvidando un decorador en un endpoint nuevo.
    if user.is_readonly and request.method not in METODOS_DE_LECTURA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta es una cuenta de demostración: puedes explorar toda la "
                "plataforma, pero no modificar datos."
            ),
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Exige rol de administrador.

    Se reserva para lo irreversible —suprimir los datos de una persona—, que un
    jefe de área no debería poder hacer por su cuenta.
    """
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acción reservada a administradores.",
        )
    return current_user


def require_manager(current_user: User = Depends(get_current_user)) -> User:
    """Exige rol de gestión (admin o jefe). Lanza 403 para asesores."""
    if not current_user.is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acción reservada a jefes de área o administradores.",
        )
    return current_user
