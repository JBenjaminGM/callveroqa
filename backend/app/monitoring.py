"""
Monitorización de errores (Sentry), apagada mientras no haya `SENTRY_DSN`.

Sin esto, un error en producción solo se ve si alguien lo reporta y además
alguien busca en los logs de Render, que el plan gratuito guarda poco tiempo.
Con el DSN puesto, cada error no controlado llega a Sentry con el mismo
`request_id` que ve el usuario y que aparece en los logs, para cruzarlos.

Nunca se envían datos personales: ni cuerpos de petición (llevan
transcripciones y notas), ni cabeceras de autorización, ni IPs.
"""

import logging

from app.config import settings

logger = logging.getLogger("callveroqa")

_activo = False


def init_sentry(**extra) -> bool:
    """Arranca Sentry si hay DSN. Devuelve si quedó activo.

    `extra` se pasa tal cual a `sentry_sdk.init`; los tests lo usan para
    capturar los eventos en memoria en vez de enviarlos.
    """
    global _activo
    if not settings.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        # Sin datos personales: IPs, cookies ni usuarios.
        send_default_pii=False,
        # Los cuerpos de petición llevan transcripciones y notas de clientes.
        max_request_body_size="never",
        # Sin las variables locales de cada línea de la traza: por defecto se
        # envían, y ahí iba el token de la petición entero (lo cazó un test) y
        # podrían ir transcripciones.
        include_local_variables=False,
        # Solo errores; el rendimiento no hace falta y consume la cuota gratis.
        traces_sample_rate=0.0,
        **extra,
    )
    _activo = True
    logger.info("Sentry activo (entorno %s).", settings.sentry_environment)
    return True


def tag_request(request_id: str) -> None:
    """
    Etiqueta la petición en curso con su id.

    Se hace al entrar y no al capturar: la integración de FastAPI captura el
    error por su cuenta, y la deduplicación de Sentry descarta el segundo envío,
    así que la etiqueta tiene que estar ya en el ámbito de la petición.
    """
    if not _activo:
        return
    import sentry_sdk

    sentry_sdk.get_isolation_scope().set_tag("request_id", request_id)


def capture(exc: BaseException, request_id: str | None) -> None:
    """Envía un error no controlado, etiquetado con el id de la petición."""
    if not _activo:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        if request_id:
            scope.set_tag("request_id", request_id)
        sentry_sdk.capture_exception(exc)
