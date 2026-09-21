"""
Servicio de transcripción de audio (speech-to-text).

Usa un patrón factory con 3 proveedores, seleccionables por WHISPER_PROVIDER:
- groq:  Groq API (Whisper large v3) — el usado por defecto.
- local: Whisper local — stub para el futuro.
- azure: Azure AI Speech — stub preparado para la migración a Indra.

Cada proveedor devuelve un dict: {"text": str, "segments": [{start, end, text}]}.
"""

import logging
import os
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger("callveroqa.transcription")

# Pausa (en segundos) a partir de la cual se considera un cambio de hablante.
SPEAKER_SWITCH_GAP = 1.5


class TranscriptionProvider(ABC):
    """Interfaz común de los proveedores de transcripción."""

    @abstractmethod
    async def transcribe(self, audio_path: str, language: str) -> dict:
        """Transcribe el audio y devuelve {'text': ..., 'segments': [...]}."""


class GroqProvider(TranscriptionProvider):
    """Transcripción mediante Groq API (Whisper large v3)."""

    URL = "https://api.groq.com/openai/v1/audio/transcriptions"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "Falta GROQ_API_KEY. Configure su clave de Groq en las variables de entorno."
            )
        self.api_key = api_key

    async def transcribe(self, audio_path: str, language: str) -> dict:
        filename = os.path.basename(audio_path)
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (filename, audio_bytes)},
                data={
                    "model": "whisper-large-v3",
                    "response_format": "verbose_json",
                    "language": language,
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Error de transcripción en Groq (HTTP {response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        segments = [
            {
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "text": (s.get("text") or "").strip(),
            }
            for s in data.get("segments", [])
        ]
        return {"text": data.get("text", "").strip(), "segments": segments}


class LocalWhisperProvider(TranscriptionProvider):
    """Whisper local. Stub: no disponible en el deploy del MVP."""

    async def transcribe(self, audio_path: str, language: str) -> dict:
        raise NotImplementedError(
            "Whisper local no está disponible en este despliegue. "
            "Use WHISPER_PROVIDER=groq."
        )


class AzureSpeechProvider(TranscriptionProvider):
    """Azure AI Speech. Stub preparado para la migración a infraestructura Indra."""

    def __init__(self) -> None:
        self.key = settings.azure_speech_key
        self.region = settings.azure_speech_region

    async def transcribe(self, audio_path: str, language: str) -> dict:
        if not self.key or not self.region:
            raise NotImplementedError(
                "Azure Speech no está configurado. Defina AZURE_SPEECH_KEY y "
                "AZURE_SPEECH_REGION para habilitar este proveedor."
            )
        # Implementación futura con el SDK azure-cognitiveservices-speech.
        raise NotImplementedError("Proveedor Azure Speech aún no implementado en el MVP.")


def add_speaker_diarization(segments: list[dict]) -> list[dict]:
    """
    Asigna un hablante a cada segmento mediante una heurística de pausas.

    NOTA: Esta heurística es solo un FALLBACK. La diarización principal la hace
    el LLM por contenido durante el análisis (ver call_tasks._run_pipeline), que
    reasigna los hablantes según lo que realmente dice cada turno. Estas
    etiquetas iniciales solo se conservan cuando el LLM no devuelve diarización.

    - El primer segmento es del ejecutivo ('agent'), que es quien saluda.
    - Si la pausa respecto al segmento anterior supera SPEAKER_SWITCH_GAP,
      se considera un cambio de turno y se alterna el hablante.
    """
    speakers = ["agent", "customer"]
    current = 0
    result: list[dict] = []
    prev_end = 0.0

    for i, seg in enumerate(segments):
        if i > 0 and (seg["start"] - prev_end) > SPEAKER_SWITCH_GAP:
            current = 1 - current  # alterna entre 0 y 1
        result.append({**seg, "speaker": speakers[current]})
        prev_end = seg["end"]

    return result


def get_transcription_provider() -> TranscriptionProvider:
    """Factory: devuelve el proveedor de transcripción según la configuración."""
    provider = settings.whisper_provider
    if provider == "groq":
        return GroqProvider(settings.groq_api_key)
    if provider == "local":
        return LocalWhisperProvider()
    if provider == "azure":
        return AzureSpeechProvider()
    raise ValueError(f"Proveedor de transcripción desconocido: {provider}")
