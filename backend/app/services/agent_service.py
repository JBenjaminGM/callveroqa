"""Lógica de negocio de gestión de ejecutivos (agents)."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.user import ROLE_ASESOR, User
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.name_matching import find_matching_agent
from app.utils.security import hash_password

logger = logging.getLogger("callveroqa.agents")


def link_unassigned_calls(db: Session, agent: Agent) -> int:
    """
    Vincula al ejecutivo las llamadas sin asignar cuyo nombre detectado
    coincida (de forma difusa) con el suyo.

    Se usa al crear un ejecutivo: si la IA ya había detectado su nombre en
    llamadas previas, esas llamadas se le asignan automáticamente.
    Devuelve el número de llamadas vinculadas.
    """
    pending = db.scalars(
        select(Call).where(
            Call.agent_id.is_(None), Call.detected_agent_name.is_not(None)
        )
    ).all()

    linked = 0
    for call in pending:
        match, _ = find_matching_agent(call.detected_agent_name or "", [agent])
        if match is not None:
            call.agent_id = agent.id
            linked += 1

    if linked:
        db.commit()
        logger.info("Ejecutivo id=%s vinculado a %s llamadas previas", agent.id, linked)
    return linked


def list_agents(db: Session, active: bool | None = None, search: str | None = None) -> list[Agent]:
    """Lista los ejecutivos, con filtros opcionales por estado y nombre."""
    query = select(Agent)
    if active is not None:
        query = query.where(Agent.active == active)
    if search:
        query = query.where(Agent.name.ilike(f"%{search}%"))
    query = query.order_by(Agent.name)
    return list(db.scalars(query).all())


def get_agent(db: Session, agent_id: int) -> Agent | None:
    """Devuelve un ejecutivo por id, o None si no existe."""
    return db.get(Agent, agent_id)


def create_agent(db: Session, data: AgentCreate) -> tuple[Agent, int]:
    """
    Crea un nuevo ejecutivo y vincula sus llamadas previas sin asignar.

    Devuelve (ejecutivo, nº de llamadas vinculadas automáticamente).
    """
    if data.email:
        existing = db.scalar(select(Agent).where(Agent.email == data.email))
        if existing is not None:
            raise ValueError(f"Ya existe un ejecutivo con el email {data.email}.")

    agent = Agent(**data.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info("Ejecutivo creado id=%s nombre=%s", agent.id, agent.name)

    # Vincula automáticamente llamadas previas detectadas con ese nombre.
    linked = link_unassigned_calls(db, agent)
    return agent, linked


def update_agent(db: Session, agent: Agent, data: AgentUpdate) -> Agent:
    """Actualiza los datos de un ejecutivo existente."""
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"]:
        existing = db.scalar(
            select(Agent).where(Agent.email == changes["email"], Agent.id != agent.id)
        )
        if existing is not None:
            raise ValueError(f"Ya existe otro ejecutivo con el email {changes['email']}.")

    for field, value in changes.items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    logger.info("Ejecutivo actualizado id=%s", agent.id)
    return agent


def deactivate_agent(db: Session, agent: Agent) -> None:
    """Desactiva un ejecutivo (soft delete: no se borra, se marca inactivo)."""
    agent.active = False
    db.commit()
    logger.info("Ejecutivo desactivado id=%s", agent.id)


def create_agent_login(
    db: Session, agent: Agent, *, email: str, password: str, name: str | None = None
) -> User:
    """
    Crea una cuenta de acceso de ASESOR vinculada a un ejecutivo.

    Valida que el email no exista ya y que el ejecutivo no tenga otra cuenta.
    """
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ValueError(f"Ya existe un usuario con el email {email}.")
    if db.scalar(select(User).where(User.agent_id == agent.id)) is not None:
        raise ValueError("Este ejecutivo ya tiene una cuenta de acceso.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=(name or agent.name),
        role=ROLE_ASESOR,
        agent_id=agent.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Login de asesor creado id=%s para ejecutivo id=%s", user.id, agent.id)
    return user


def get_agent_stats(db: Session, agent_id: int) -> tuple[int, float | None]:
    """
    Devuelve (total de llamadas analizadas, score promedio) de un ejecutivo.

    Solo cuenta llamadas con estado DONE.
    """
    total = db.scalar(
        select(func.count(Call.id)).where(
            Call.agent_id == agent_id, Call.status == CallStatus.DONE
        )
    ) or 0

    avg = db.scalar(
        select(func.avg(Analysis.global_score))
        .join(Call, Call.id == Analysis.call_id)
        .where(Call.agent_id == agent_id)
    )
    return total, (round(float(avg), 1) if avg is not None else None)
