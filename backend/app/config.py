"""
Configuración central de la aplicación.

Todas las opciones se leen de variables de entorno (archivo .env) usando
Pydantic Settings. Nunca se debe escribir una clave secreta directamente
en el código: siempre debe venir del entorno.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contenedor tipado de toda la configuración del backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Base de datos ---
    database_url: str = "postgresql://callveroqa:callveroqa@localhost:5432/callveroqa"
    redis_url: str = "redis://localhost:6379/0"

    # --- Almacenamiento de audios ---
    storage_provider: str = "local"          # local | s3
    storage_path: str = "/data/audios"
    aws_s3_bucket: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # --- Monitorización de errores (vacío = apagada) ---
    sentry_dsn: str = ""
    sentry_environment: str = "production"

    # --- Transcripción ---
    whisper_provider: str = "groq"           # groq | local | azure
    groq_api_key: str = ""

    # --- Análisis con IA ---
    ai_provider: str = "groq"                # groq | claude | openai | azure
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_model_claude: str = "claude-sonnet-5"
    ai_model_openai: str = "gpt-4o"
    # LLM gratis de Groq para el análisis. Ojo: el catálogo de Groq cambia y no
    # todas las cuentas tienen acceso a todos los modelos; si la API responde
    # 404 "model_not_found", hay que elegir otro de https://console.groq.com/docs/models.
    ai_model_groq: str = "openai/gpt-oss-120b"

    # --- Azure (migración futura) ---
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"

    # --- Autenticación ---
    jwt_secret: str = "cambia-esto-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    # --- Aplicación ---
    app_env: str = "production"
    app_default_language: str = "es"
    app_max_audio_size_mb: int = 100
    # Si es True, las llamadas se procesan en una tarea en segundo plano de la
    # propia API (sin worker Celery). Pensado para planes gratis que no ofrecen
    # workers (Render free, etc.). En local/Docker se deja en False (usa Celery).
    process_inline: bool = False
    cors_origins: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Render/Heroku entregan 'postgres://'; SQLAlchemy 2.0 exige 'postgresql://'."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Devuelve la lista de orígenes CORS a partir de la cadena separada por comas."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_audio_size_bytes(self) -> int:
        """Tamaño máximo de audio permitido, en bytes."""
        return self.app_max_audio_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración (cacheada para no releer el .env en cada uso)."""
    return Settings()


# Instancia global de configuración, lista para importar.
settings = get_settings()
