"""Endpoints de gestión de ejecutivos (agents)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin, require_manager
from app.models.user import User
from app.schemas.agent import (
    AgentCreate,
    AgentCreatedOut,
    AgentDetailOut,
    AgentLoginCreate,
    AgentOut,
    AgentUpdate,
)
from app.schemas.agent import DataErasureOut
from app.schemas.auth import UserOut
from app.services import agent_service, retention_service

router = APIRouter(prefix="/agents", tags=["agents"])


def _ensure_can_view_agent(current_user: User, agent_id: int) -> None:
    """Un asesor solo puede ver su propia ficha; un manager ve todas."""
    if not current_user.is_manager and current_user.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ver este ejecutivo.",
        )


@router.get("", response_model=list[AgentOut])
def list_agents(
    active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los ejecutivos. El asesor solo ve su propia ficha."""
    agents = agent_service.list_agents(db, active=active, search=search)
    if not current_user.is_manager:
        agents = [a for a in agents if a.id == current_user.agent_id]
    return agents


@router.post("", response_model=AgentCreatedOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Crea un nuevo ejecutivo.

    Si la IA ya había detectado su nombre en llamadas previas sin asignar,
    esas llamadas se le vinculan automáticamente (campo `linked_calls`).
    """
    try:
        agent, linked = agent_service.create_agent(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = AgentCreatedOut.model_validate(agent)
    result.linked_calls = linked
    return result


@router.post(
    "/{agent_id}/login", response_model=UserOut, status_code=status.HTTP_201_CREATED
)
def create_agent_login(
    agent_id: int,
    payload: AgentLoginCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Crea una cuenta de acceso de ASESOR vinculada a un ejecutivo."""
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    try:
        user = agent_service.create_agent_login(
            db, agent, email=payload.email, password=payload.password, name=payload.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return UserOut.model_validate(user)


@router.get("/{agent_id}", response_model=AgentDetailOut)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el detalle de un ejecutivo con sus estadísticas."""
    _ensure_can_view_agent(current_user, agent_id)
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")

    total, avg = agent_service.get_agent_stats(db, agent_id)
    detail = AgentDetailOut.model_validate(agent)
    detail.total_calls = total
    detail.average_score = avg
    return detail


@router.put("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Actualiza los datos de un ejecutivo."""
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    try:
        return agent_service.update_agent(db, agent, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Desactiva un ejecutivo (soft delete)."""
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    agent_service.deactivate_agent(db, agent)
    return None


@router.delete("/{agent_id}/data", response_model=DataErasureOut)
def erase_agent_data(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Suprime **todo** lo de este ejecutivo: llamadas, audios, transcripciones,
    análisis, revisiones y respuestas.

    Es el derecho de supresión, y es irreversible. Reservado a administradores
    y separado del borrado normal (`DELETE /agents/{id}`, que solo desactiva):
    dar de baja a alguien del equipo y borrar su rastro no son la misma acción,
    y confundirlas es como se pierden datos sin querer. La ficha se conserva
    desactivada para que los agregados históricos no queden con un hueco.
    """
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    resultado = retention_service.delete_agent_data(db, agent)
    return DataErasureOut(agent_id=agent_id, **resultado)
