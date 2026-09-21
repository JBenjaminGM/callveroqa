"""Lógica de negocio de autenticación."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import verify_password

logger = logging.getLogger("callveroqa.auth")


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Verifica las credenciales de un usuario.

    Devuelve el usuario si email y contraseña son correctos, o None en caso contrario.
    Actualiza la fecha de último acceso al autenticar correctamente.
    """
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        logger.info("Intento de login con email inexistente: %s", email)
        return None

    if not verify_password(password, user.password_hash):
        logger.info("Intento de login con contraseña incorrecta: %s", email)
        return None

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    logger.info("Login correcto del usuario id=%s", user.id)
    return user
