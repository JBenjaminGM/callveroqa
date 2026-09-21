"""
Configuración de la aplicación Celery.

Celery usa Redis como broker (cola) y backend de resultados.
El worker se arranca con:  celery -A app.tasks.celery_app worker --loglevel=info
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "callveroqa",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.call_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    timezone="UTC",
    # Cada audio se procesa de principio a fin; con 50 en paralelo el límite
    # es la concurrencia de los workers desplegados.
    task_acks_late=True,
)
