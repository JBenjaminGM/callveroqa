"""
Punto de entrada de la aplicación FastAPI de CallVeroQA.

Configura CORS, logging estructurado, rate limiting, los routers de la API
y un middleware que añade el header de aviso de prototipo a cada respuesta.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from sqlalchemy import text

from app.config import settings
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.monitoring import capture, init_sentry, tag_request
from app.routers import (
    agents,
    auth,
    calibration,
    calls,
    campaigns,
    coaching,
    config,
    dashboard,
    users,
)

# Salvaguarda interna: recuerda que el entorno es de evaluación.
PROTOTYPE_NOTICE = "Evaluation environment - Do not use with real customer data"


# --- Logging estructurado en JSON ---
# Identificador de la petición en curso. Un ContextVar y no un parámetro
# porque tiene que llegar a logs escritos en cualquier capa (servicios, tareas)
# sin arrastrarlo por toda la firma de las funciones.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Formatea cada log como una línea JSON con el campo environment="evaluation"."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": "evaluation",
        }
        # Permite seguir un error concreto: el usuario ve el id en la respuesta
        # y con él se encuentran en el log todas las líneas de esa petición.
        request_id = request_id_var.get()
        if request_id:
            log["request_id"] = request_id
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def _configure_logging() -> None:
    """Configura el logging raíz para emitir JSON por stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


_configure_logging()
logger = logging.getLogger("callveroqa")


# Valor de ejemplo de JWT_SECRET. Sirve en desarrollo; en producción firmaría los
# tokens con un secreto que cualquiera puede leer en el repositorio.
DEFAULT_JWT_SECRET = "cambia-esto-en-produccion"


def verify_production_secrets() -> None:
    """
    Aborta el arranque si producción usa el JWT_SECRET de ejemplo.

    Con un secreto conocido cualquiera puede firmar tokens válidos y suplantar a
    un administrador, así que es preferible no arrancar a servir tráfico inseguro.
    """
    if settings.app_env == "production" and settings.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET tiene el valor de ejemplo y APP_ENV=production. "
            "Define un JWT_SECRET largo y aleatorio antes de arrancar la API."
        )


verify_production_secrets()
init_sentry()

app = FastAPI(
    title="CallVeroQA - API",
    description=(
        "Backend de la plataforma de Quality Assurance automatizado con IA para "
        "call centers. Vista previa para evaluación — no utilizar con datos reales de clientes."
    ),
    version="1.0.0-mvp",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: solo se permiten los orígenes definidos en la configuración.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Prototype-Notice"],
)


@app.middleware("http")
async def add_prototype_header(request: Request, call_next):
    """Marca la petición con un id, añade el aviso de prototipo y la loggea."""
    start = time.time()
    # Se respeta el id del proxy si viene, para poder cruzar logs con Render.
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    tag_request(request_id)
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        # Se responde aquí y no en el manejador global: ese corre fuera de este
        # middleware, cuando el id ya se ha limpiado, y el 500 salía con
        # `request_id: null` y sin la cabecera X-Request-ID.
        response = _error_500(request, exc, request_id)
    finally:
        request_id_var.reset(token)
    response.headers["X-Prototype-Notice"] = PROTOTYPE_NOTICE
    response.headers["X-Request-ID"] = request_id
    elapsed_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def _error_500(request: Request, exc: Exception, request_id: str | None) -> JSONResponse:
    """Registra un error no controlado y devuelve un mensaje claro en español."""
    logger.exception(
        "Error no controlado en %s %s", request.method, request.url.path, exc_info=exc
    )
    capture(exc, request_id)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ocurrió un error interno. Inténtelo de nuevo más tarde.",
            # Se devuelve para que quien reporte el fallo pueda decir cuál fue:
            # con este id se encuentran en el log todas sus líneas.
            "request_id": request_id,
        },
        headers={
            "X-Prototype-Notice": PROTOTYPE_NOTICE,
            **({"X-Request-ID": request_id} if request_id else {}),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Red de seguridad para lo que no pase por el middleware de arriba."""
    return _error_500(request, exc, request_id_var.get())


@app.get("/", tags=["health"])
def root() -> dict:
    """Endpoint raíz: confirma que la API está viva."""
    return {
        "service": "CallVeroQA",
        "status": "ok",
        "notice": PROTOTYPE_NOTICE,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    """
    Health check para Render (`healthCheckPath`) y el keepalive de GitHub Actions.

    Comprueba **también la base de datos**: un proceso vivo que no puede
    consultar nada está caído para el usuario, y esa diferencia es justo la que
    dejó pasar dos meses de caída en producción sin que saltara ninguna alarma.
    """
    try:
        # Con la sesión de la aplicación, no con un motor aparte: así se
        # comprueba exactamente la conexión que usan los endpoints.
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Health check: la base de datos no responde: %s", exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "database": "unreachable"}


# --- Registro de routers de la API (todos bajo /api/v1) ---
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(campaigns.router, prefix=API_PREFIX)
app.include_router(calls.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(config.router, prefix=API_PREFIX)
app.include_router(calibration.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(coaching.router, prefix=API_PREFIX)
