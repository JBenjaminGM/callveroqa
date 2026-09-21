# ============================================================
# CallVeroQA - Dockerfile multi-stage
# ============================================================

# ---- Etapa 1: builder (instala dependencias) ----
FROM python:3.11-slim AS builder

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# ---- Etapa 2: imagen final ----
FROM python:3.11-slim

# libpq es necesaria en runtime para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root por seguridad
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Copia las dependencias instaladas desde la etapa builder
COPY --from=builder /install/deps /usr/local

# Copia el código de la aplicación
COPY . .

# Carpeta para audios (montada como volumen en producción)
RUN mkdir -p /data/audios && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

# Arranque por defecto (usado por Render): migraciones + datos iniciales + servidor.
# El puerto lo define el host con $PORT (8000 por defecto en local).
# En docker-compose local este CMD se sobreescribe con su propio `command`.
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_data.py && python scripts/seed_demo.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
