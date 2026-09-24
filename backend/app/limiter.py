"""
Rate limiter compartido (slowapi).

Se define en su propio módulo para que tanto `main.py` como los routers
puedan importarlo sin provocar importaciones circulares.

**La clave del límite del login es IP + email, no la IP sola.** Un call center
entero sale a internet por una única IP pública: con la IP como clave, cinco
intentos fallidos de una persona dejaban fuera a todo el equipo durante quince
minutos. Contando por cuenta se sigue frenando la fuerza bruta —que va contra
una cuenta concreta— sin castigar a los compañeros.
"""

import json

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Límite del login: intentos por IP+cuenta y ventana de tiempo.
LOGIN_RATE_LIMIT = "10/15minutes"


def login_rate_key(request: Request) -> str:
    """
    Clave del límite: IP + email del intento.

    El cuerpo ya se ha leído cuando slowapi evalúa la clave, así que se lee del
    caché que Starlette guarda en `request._body`. Si no se puede leer el email
    (cuerpo raro o malformado), se cae a la IP sola: prudente, porque ese caso
    es justamente el de un cliente que no se está comportando.
    """
    ip = get_remote_address(request)
    body = getattr(request, "_body", None)
    if body:
        try:
            email = json.loads(body).get("email")
            if isinstance(email, str) and email.strip():
                return f"{ip}|{email.strip().lower()}"
        except (ValueError, AttributeError):
            pass
    return ip


limiter = Limiter(key_func=get_remote_address)
