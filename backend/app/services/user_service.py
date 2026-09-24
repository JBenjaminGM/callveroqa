"""
Gestión de cuentas: altas, bajas, roles y contraseñas.

Un cliente tiene que poder montar su equipo y recuperar un acceso perdido sin
llamar a nadie y sin tocar la base de datos. Eso es lo que hay aquí.

Tres reglas que no son obvias y que evitan quedarse fuera de casa:

1. **Siempre queda al menos un administrador activo.** Ni desactivarse a uno
   mismo, ni bajarse el rol, ni desactivar al último admin.
2. **Las bajas no borran.** `active=False` cierra el acceso y conserva el
   historial: las llamadas y revisiones de esa persona siguen explicando los
   datos del equipo.
3. **La cuenta de demostración es intocable desde la API.** Es pública y de solo
   lectura; cambiarle la contraseña o el rol la convertiría en una puerta abierta.
"""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.user import MANAGER_ROLES, ROLE_ADMIN, ROLE_ASESOR, VALID_ROLES, User
from app.utils.security import hash_password, verify_password

logger = logging.getLogger("callveroqa.users")

# Longitud mínima de contraseña. No se piden símbolos ni mayúsculas: la longitud
# es lo que de verdad cuesta romper, y las reglas barrocas solo llevan a
# contraseñas predecibles apuntadas en un post-it.
MIN_PASSWORD_LENGTH = 10

# Contraseñas que versiones antiguas del seed dejaron escritas en el repositorio.
# Aunque alguien las recuerde, no se pueden volver a usar.
PUBLISHED_PASSWORDS = {"Admin123" + "!", "Jefe123" + "!", "Asesor123" + "!"}


def validate_password(password: str, *, email: str | None = None) -> None:
    """Valida una contraseña nueva. Lanza 422 con un motivo legible."""
    password = password or ""
    problemas = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problemas.append(f"debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
    if password in PUBLISHED_PASSWORDS:
        problemas.append("esa contraseña llegó a publicarse y no se puede reutilizar")
    if email and password.strip().lower() == email.strip().lower():
        problemas.append("no puede ser igual al email")
    if password.strip() != password:
        problemas.append("no puede empezar ni terminar con espacios")
    if problemas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña " + "; ".join(problemas) + ".",
        )


def generate_password() -> str:
    """Contraseña aleatoria para un alta o un reseteo. Se enseña una sola vez."""
    return secrets.token_urlsafe(12)


def _protegida(user: User) -> bool:
    """La cuenta de demostración pública no se administra desde la API."""
    return bool(user.is_readonly)


def _admins_activos(db: Session, excluir_id: int | None = None) -> int:
    query = (
        select(func.count())
        .select_from(User)
        .where(User.role == ROLE_ADMIN, User.active.is_(True))
    )
    if excluir_id is not None:
        query = query.where(User.id != excluir_id)
    return db.scalar(query) or 0


def _asegurar_que_queda_un_admin(db: Session, user: User) -> None:
    """Impide el cambio que dejaría la plataforma sin ningún administrador."""
    if user.role == ROLE_ADMIN and _admins_activos(db, excluir_id=user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Es el único administrador activo. Nombra a otro administrador "
                "antes de desactivar o cambiar el rol de esta cuenta."
            ),
        )


def list_users(db: Session, *, include_inactive: bool = True) -> list[User]:
    """Todas las cuentas, las activas primero y por nombre."""
    query = select(User).order_by(User.active.desc(), User.name)
    if not include_inactive:
        query = query.where(User.active.is_(True))
    return list(db.scalars(query).all())


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    return user


def _validar_rol_y_agente(db: Session, role: str, agent_id: int | None) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rol desconocido: {role}.",
        )
    if role == ROLE_ASESOR:
        if agent_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un asesor tiene que estar vinculado a un ejecutivo.",
            )
        if db.get(Agent, agent_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El ejecutivo indicado no existe.",
            )
    elif agent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo los asesores se vinculan a un ejecutivo.",
        )


def create_user(
    db: Session,
    *,
    email: str,
    name: str,
    role: str,
    password: str | None = None,
    agent_id: int | None = None,
) -> tuple[User, str | None]:
    """
    Crea una cuenta. Devuelve (usuario, contraseña_generada).

    Si no se indica contraseña se genera una y se devuelve **una sola vez**: no
    se vuelve a poder leer, y quien la reciba debería cambiarla al entrar.
    """
    email = email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email.",
        )
    _validar_rol_y_agente(db, role, agent_id)

    generada = None
    if password:
        validate_password(password, email=email)
    else:
        password = generate_password()
        generada = password

    user = User(
        email=email,
        name=name.strip(),
        role=role,
        agent_id=agent_id,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Usuario creado id=%s rol=%s", user.id, user.role)
    return user, generada


def update_user(
    db: Session,
    user: User,
    *,
    actor: User,
    name: str | None = None,
    role: str | None = None,
    active: bool | None = None,
    agent_id: int | None = None,
    agent_id_set: bool = False,
) -> User:
    """Cambia nombre, rol, vínculo o estado de una cuenta."""
    if _protegida(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de demostración no se puede modificar.",
        )
    if user.id == actor.id and (active is False or (role and role != user.role)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes desactivarte ni cambiarte el rol a ti mismo.",
        )

    nuevo_rol = role or user.role
    nuevo_agente = agent_id if agent_id_set else user.agent_id
    if nuevo_rol in MANAGER_ROLES and role is not None:
        # Un manager nunca queda colgado de una ficha de ejecutivo.
        nuevo_agente = None
    if role is not None or agent_id_set:
        _validar_rol_y_agente(db, nuevo_rol, nuevo_agente)
    if (role and role != user.role) or active is False:
        _asegurar_que_queda_un_admin(db, user)

    if name is not None:
        user.name = name.strip()
    if role is not None:
        user.role = role
    if role is not None or agent_id_set:
        user.agent_id = nuevo_agente
    if active is not None:
        user.active = active
    db.commit()
    db.refresh(user)
    logger.info(
        "Usuario actualizado id=%s rol=%s activo=%s", user.id, user.role, user.active
    )
    return user


def reset_password(db: Session, user: User, *, actor: User) -> str:
    """Genera una contraseña nueva para otra persona y la devuelve una sola vez."""
    if _protegida(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de demostración no se puede modificar.",
        )
    nueva = generate_password()
    user.password_hash = hash_password(nueva)
    db.commit()
    logger.info("Contraseña reseteada para id=%s por id=%s", user.id, actor.id)
    return nueva


def change_own_password(db: Session, user: User, *, current: str, new: str) -> None:
    """Cambia la contraseña del propio usuario, comprobando antes la actual."""
    if _protegida(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta es una cuenta de demostración: puedes explorar toda la "
                "plataforma, pero no modificar datos."
            ),
        )
    if not verify_password(current, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )
    if current == new:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña nueva tiene que ser distinta de la actual.",
        )
    validate_password(new, email=user.email)
    user.password_hash = hash_password(new)
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    logger.info("Contraseña cambiada por el propio usuario id=%s", user.id)
