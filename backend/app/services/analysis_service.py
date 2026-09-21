"""
Servicio de análisis IA de transcripciones.

Patrón factory con 4 proveedores, seleccionables por AI_PROVIDER:
- groq:   Llama 3.3 70B (API compatible con OpenAI) — el usado por defecto (coste $0).
- claude: Anthropic Claude API.
- openai: OpenAI GPT-4o.
- azure:  Azure OpenAI — stub preparado para la migración a Indra.

Cada proveedor recibe un prompt y devuelve un dict ya parseado con
dimension_scores, summary y recommendations.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger("callveroqa.analysis")

TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 3


def _extract_json(text: str) -> dict:
    """
    Extrae el primer objeto JSON de un texto.

    Los LLMs a veces envuelven el JSON en texto o bloques markdown;
    esta función localiza el objeto delimitado por llaves.
    """
    text = text.strip()
    # Quita posibles fences de markdown ```json ... ```
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("La respuesta de la IA no contenía un JSON válido.")


class AnalysisProvider(ABC):
    """Interfaz común de los proveedores de análisis IA."""

    @abstractmethod
    async def _call_api(self, prompt: str) -> tuple[str, int]:
        """Llama a la API y devuelve (texto_respuesta, tokens_usados)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo usado (para auditoría)."""

    async def analyze(self, prompt: str) -> dict:
        """
        Ejecuta el análisis con reintentos y backoff exponencial.

        Devuelve un dict con dimension_scores, summary, recommendations,
        ai_model y tokens_used.
        """
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                text, tokens = await self._call_api(prompt)
                result = _extract_json(text)
                result["ai_model"] = self.model_name
                result["tokens_used"] = tokens
                logger.info(
                    "Análisis IA completado (modelo=%s, tokens=%s)",
                    self.model_name,
                    tokens,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Intento %s/%s de análisis IA falló: %s", attempt, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)  # backoff exponencial: 2s, 4s

        raise RuntimeError(f"El análisis IA falló tras {MAX_RETRIES} intentos: {last_error}")


class ClaudeProvider(AnalysisProvider):
    """Análisis mediante la API de Anthropic Claude."""

    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "Falta ANTHROPIC_API_KEY. Configure su clave de Anthropic."
            )
        self.api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def _call_api(self, prompt: str) -> tuple[str, int]:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                self.URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Error en Anthropic (HTTP {response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return text, tokens


class OpenAIProvider(AnalysisProvider):
    """Análisis mediante la API de OpenAI (GPT-4o)."""

    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("Falta OPENAI_API_KEY. Configure su clave de OpenAI.")
        self.api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def _call_api(self, prompt: str) -> tuple[str, int]:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                self.URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 4000,
                },
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Error en OpenAI (HTTP {response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


class GroqLLMProvider(OpenAIProvider):
    """
    Análisis con un LLM servido por Groq (gratis, API compatible con OpenAI).

    Reutiliza la lógica de OpenAIProvider cambiando solo el endpoint, de modo
    que una única GROQ_API_KEY sirve tanto para transcribir (Whisper) como
    para analizar. Es el proveedor por defecto (coste $0).
    """

    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "Falta GROQ_API_KEY para el análisis con Groq. Configure su clave de Groq."
            )
        self.api_key = api_key
        self._model = model


class AzureOpenAIProvider(AnalysisProvider):
    """Azure OpenAI. Stub preparado para la migración a infraestructura Indra."""

    def __init__(self) -> None:
        self.endpoint = settings.azure_openai_endpoint
        self.api_key = settings.azure_openai_api_key
        self.deployment = settings.azure_openai_deployment
        self.api_version = settings.azure_openai_api_version
        if not self.endpoint or not self.api_key:
            raise NotImplementedError(
                "Azure OpenAI no está configurado. Defina AZURE_OPENAI_ENDPOINT y "
                "AZURE_OPENAI_API_KEY para habilitar este proveedor."
            )

    @property
    def model_name(self) -> str:
        return f"azure/{self.deployment}"

    async def _call_api(self, prompt: str) -> tuple[str, int]:
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers={"api-key": self.api_key, "content-type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 4000,
                },
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Error en Azure OpenAI (HTTP {response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


def get_analysis_provider() -> AnalysisProvider:
    """Factory: devuelve el proveedor de análisis IA según la configuración."""
    provider = settings.ai_provider
    if provider == "claude":
        return ClaudeProvider(settings.anthropic_api_key, settings.ai_model_claude)
    if provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.ai_model_openai)
    if provider == "groq":
        return GroqLLMProvider(settings.groq_api_key, settings.ai_model_groq)
    if provider == "azure":
        return AzureOpenAIProvider()
    raise ValueError(f"Proveedor de IA desconocido: {provider}")


def calculate_global_score(dimension_scores: dict[str, int], rubric: dict[str, float]) -> int:
    """
    Calcula el score global ponderado a partir de los scores por dimensión.

    global_score = Σ (score_dimensión * peso_dimensión / 100)

    Si una dimensión no tiene peso definido en la rúbrica, se ignora.
    El resultado se redondea a entero y se acota al rango 0-100.
    """
    total = 0.0
    for key, score in dimension_scores.items():
        weight = rubric.get(key, 0.0)
        total += score * weight / 100.0
    return max(0, min(100, round(total)))
