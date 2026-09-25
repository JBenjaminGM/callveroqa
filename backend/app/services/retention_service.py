"""
Retención de grabaciones y borrado de los datos de una persona.

Un banco no pregunta si se puede guardar una grabación para siempre: pregunta
**cuánto tiempo se guarda** y **cómo se borra lo de alguien concreto**. Sin una
respuesta a las dos, la conversación de compra se para ahí.

Dos operaciones, con una diferencia importante entre ellas:

- **Retención**: caduca el *audio*, no la evaluación. Pasados N días se borra la
  grabación del almacenamiento y la llamada se queda con su transcripción, su
  nota y sus recomendaciones. Es lo que permite decir "no conservamos voz más
  allá de N días" sin perder el histórico de calidad.
- **Borrado de una persona**: eso sí se lleva todo lo suyo —llamadas, audios,
  transcripciones, análisis, revisiones— porque es lo que significa suprimir.

La purga corre sola, con freno: como mucho una vez cada seis horas, disparada
por el uso de la aplicación. No hay cron en el plan gratuito de Render, y un
`while True` en el proceso de la API es peor que esto.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.call import Call
from app.models.coaching_session import CoachingSession
from app.models.settings import AppSettings
from app.services.storage_service import get_storage_provider

logger = logging.getLogger("callveroqa.retention")

# Clave del ajuste en `app_settings`. 0 = no caduca nunca (valor por defecto:
# nadie debería perder datos por actualizar la aplicación).
RETENTION_SETTING = "retention_audio_days"
RETENTION_DEFAULT = 0

# Cada cuánto se permite que la purga automática vuelva a correr.
HORAS_ENTRE_PURGAS = 6

_ultima_purga: datetime | None = None


def get_retention_days(db: Session) -> int:
    """Días de retención configurados. 0 significa que el audio no caduca."""
    fila = db.get(AppSettings, RETENTION_SETTING)
    if fila is None:
        return RETENTION_DEFAULT
    try:
        return max(0, int(str(fila.value).strip()))
    except (TypeError, ValueError):
        logger.warning("Valor de retención ilegible (%r); se ignora.", fila.value)
        return RETENTION_DEFAULT


def set_retention_days(db: Session, dias: int) -> int:
    """Guarda la política de retención (0 = no caducar)."""
    dias = max(0, int(dias))
    fila = db.get(AppSettings, RETENTION_SETTING)
    if fila is None:
        db.add(AppSettings(key=RETENTION_SETTING, value=str(dias)))
    else:
        fila.value = str(dias)
    db.commit()
    logger.info("Política de retención de audio: %s días", dias or "sin caducidad")
    return dias


def expired_calls(db: Session, dias: int) -> list[Call]:
    """
    Llamadas cuyo audio ya pasó de la fecha de caducidad y sigue existiendo.

    Se descartan las que **comparten el archivo** con una llamada aún vigente:
    un mismo audio puede estar referenciado por varias llamadas (ocurre con los
    datos de demostración, y con cualquier deduplicación futura), y borrarlo
    dejaría muda a una llamada que todavía no ha caducado. Esa llamada volverá
    a entrar en la purga cuando caduque también la que retiene el archivo.
    """
    if dias <= 0:
        return []
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dias)
    caducadas = list(
        db.scalars(
            select(Call).where(
                Call.created_at < limite,
                Call.audio_deleted_at.is_(None),
            )
        ).all()
    )
    en_uso = set(
        db.scalars(
            select(Call.audio_url).where(
                Call.created_at >= limite,
                Call.audio_deleted_at.is_(None),
            )
        ).all()
    )
    retenidas = [c for c in caducadas if c.audio_url in en_uso]
    if retenidas:
        logger.info(
            "Retención: %s llamadas caducadas conservan su audio porque lo "
            "comparten con llamadas vigentes.",
            len(retenidas),
        )
    return [c for c in caducadas if c.audio_url not in en_uso]


def purge_expired_audio(db: Session) -> int:
    """
    Borra las grabaciones caducadas y devuelve cuántas.

    Si un archivo ya no está en el almacenamiento, la llamada se marca igual:
    el objetivo es que el estado de la base refleje la realidad, y la realidad
    es que ese audio ya no existe.
    """
    dias = get_retention_days(db)
    caducadas = expired_calls(db, dias)
    if not caducadas:
        return 0

    almacen = get_storage_provider()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    for call in caducadas:
        try:
            almacen.delete(call.audio_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "No se pudo borrar el audio de la llamada id=%s: %s", call.id, exc
            )
        call.audio_deleted_at = ahora
    db.commit()
    logger.info(
        "Retención: %s grabaciones borradas (política de %s días).", len(caducadas), dias
    )
    return len(caducadas)


def purge_if_due(db: Session) -> int:
    """Ejecuta la purga como mucho una vez cada `HORAS_ENTRE_PURGAS`."""
    global _ultima_purga
    ahora = datetime.now(timezone.utc)
    if _ultima_purga is not None and ahora - _ultima_purga < timedelta(
        hours=HORAS_ENTRE_PURGAS
    ):
        return 0
    _ultima_purga = ahora
    try:
        return purge_expired_audio(db)
    except Exception as exc:  # noqa: BLE001
        # Nunca romper la pantalla del usuario por la limpieza de fondo.
        logger.warning("La purga de retención falló: %s", exc)
        db.rollback()
        return 0


def delete_agent_data(db: Session, agent: Agent) -> dict:
    """
    Suprime todo lo de un ejecutivo: sus llamadas, audios y lo que cuelga de ellas.

    Devuelve el recuento de lo borrado, que es lo que se le enseña a quien lo
    pide y lo que se puede pegar en un registro de tratamiento de datos. La
    ficha del ejecutivo se conserva desactivada, para que los históricos
    agregados no se queden con un hueco sin nombre.
    """
    llamadas = list(db.scalars(select(Call).where(Call.agent_id == agent.id)).all())
    almacen = get_storage_provider()
    audios = 0
    for call in llamadas:
        if call.audio_deleted_at is None:
            try:
                almacen.delete(call.audio_url)
                audios += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudo borrar el audio id=%s: %s", call.id, exc)
        # El resto (transcripción, análisis, revisión, acuse) cae por cascada.
        db.delete(call)
    # Las sesiones de coaching no cuelgan de una llamada sino de la ficha, que se
    # conserva: sin borrarlas a mano, las notas sobre esa persona sobrevivirían
    # a la supresión.
    sesiones = list(
        db.scalars(select(CoachingSession).where(CoachingSession.agent_id == agent.id))
    )
    for sesion in sesiones:
        db.delete(sesion)
    agent.active = False
    db.commit()
    logger.info(
        "Supresión de datos del ejecutivo id=%s: %s llamadas, %s audios, "
        "%s sesiones de coaching.",
        agent.id,
        len(llamadas),
        audios,
        len(sesiones),
    )
    return {
        "calls_deleted": len(llamadas),
        "audios_deleted": audios,
        "coaching_sessions_deleted": len(sesiones),
    }
