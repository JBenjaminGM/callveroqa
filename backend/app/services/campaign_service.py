"""Lógica de negocio de campañas y su nota de producto."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CAMPAIGN_FIELD_GUIDE,
    CORE_FIELDS,
    LIST_FIELDS,
    CampaignCreate,
    CampaignDraft,
    CampaignUpdate,
)
from app.services import campaign_ai

logger = logging.getLogger("callveroqa.campaigns")

# Etiquetas legibles de cada campo de la nota de producto (para el texto del prompt).
_FIELD_LABELS = {
    "name": "Campaña",
    "product_service": "Producto / servicio",
    "offer_description": "Descripción de la oferta",
    "key_benefits": "Beneficios clave",
    "pricing_conditions": "Precio y condiciones",
    "customer_requirements": "Requisitos del cliente",
    "mandatory_phrases": "Frases obligatorias",
    "prohibited_claims": "Afirmaciones prohibidas",
    "target_audience": "Público objetivo",
    "additional_notes": "Notas adicionales",
}


def list_campaigns(
    db: Session, active: bool | None = None, search: str | None = None
) -> list[Campaign]:
    """Lista las campañas, con filtros opcionales por estado y nombre."""
    query = select(Campaign)
    if active is not None:
        query = query.where(Campaign.active == active)
    if search:
        query = query.where(Campaign.name.ilike(f"%{search}%"))
    query = query.order_by(Campaign.name)
    return list(db.scalars(query).all())


def get_campaign(db: Session, campaign_id: int) -> Campaign | None:
    """Devuelve una campaña por id, o None si no existe."""
    return db.get(Campaign, campaign_id)


def get_campaign_by_name(db: Session, name: str) -> Campaign | None:
    """Devuelve una campaña por su nombre exacto, o None."""
    return db.scalar(select(Campaign).where(Campaign.name == name))


def count_calls(db: Session, campaign_id: int) -> int:
    """Número de llamadas asignadas a una campaña."""
    return db.scalar(
        select(func.count(Call.id)).where(Call.campaign_id == campaign_id)
    ) or 0


def create_campaign(db: Session, data: CampaignCreate) -> Campaign:
    """Crea una campaña. Lanza ValueError si ya existe una con el mismo nombre."""
    name = data.name.strip()
    if get_campaign_by_name(db, name) is not None:
        raise ValueError(f"Ya existe una campaña con el nombre «{name}».")

    payload = data.model_dump()
    payload["name"] = name
    campaign = Campaign(**payload)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    logger.info("Campaña creada id=%s nombre=%s", campaign.id, campaign.name)
    return campaign


def update_campaign(db: Session, campaign: Campaign, data: CampaignUpdate) -> Campaign:
    """Actualiza una campaña existente. Valida unicidad del nombre."""
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"]:
        changes["name"] = changes["name"].strip()
        existing = db.scalar(
            select(Campaign).where(
                Campaign.name == changes["name"], Campaign.id != campaign.id
            )
        )
        if existing is not None:
            raise ValueError(f"Ya existe otra campaña con el nombre «{changes['name']}».")

    for field, value in changes.items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    logger.info("Campaña actualizada id=%s", campaign.id)
    return campaign


def deactivate_campaign(db: Session, campaign: Campaign) -> None:
    """Desactiva una campaña (soft delete)."""
    campaign.active = False
    db.commit()
    logger.info("Campaña desactivada id=%s", campaign.id)


def compute_missing_fields(draft: dict) -> list[str]:
    """Devuelve los campos imprescindibles (CORE_FIELDS) que el borrador no trae."""
    missing = []
    for field in CORE_FIELDS:
        value = draft.get(field)
        if value is None or (isinstance(value, (list, str)) and len(value) == 0):
            missing.append(field)
    return missing


def extract_from_pdf(content: bytes, language: str = "es") -> tuple[dict, list[str], str | None]:
    """Lee un PDF, extrae la nota de producto y calcula los campos que faltan."""
    draft, warning = campaign_ai.extract_campaign_from_pdf(content, language)
    return draft, compute_missing_fields(draft), warning


def assist(
    description: str, current: CampaignDraft | None, language: str = "es"
) -> tuple[dict, str | None]:
    """Pide a la IA que complete la nota de producto a partir de una descripción."""
    current_dict = current.model_dump(exclude_none=True) if current else {}
    return campaign_ai.assist_campaign(description, current_dict, language)


def build_product_note_text(campaign: Campaign) -> str:
    """
    Construye el bloque de texto de la nota de producto para inyectarlo en el
    prompt de análisis. Omite los campos vacíos.
    """
    lines: list[str] = []
    for key, _ in CAMPAIGN_FIELD_GUIDE:
        value = getattr(campaign, key, None)
        if not value:
            continue
        label = _FIELD_LABELS.get(key, key)
        if key in LIST_FIELDS and isinstance(value, list):
            items = "; ".join(str(v) for v in value if str(v).strip())
            if items:
                lines.append(f"- {label}: {items}")
        else:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)
