"""
Motivos de llamada: por qué llama el cliente, no solo cómo lo hizo el asesor.

Es el salto de "control de calidad" a "inteligencia de cliente", y es lo que
venden CallMiner o Level AI: un jefe puede arreglar a un asesor flojo, pero si
el 30 % de las llamadas son por un cobro mal explicado, eso no se arregla con
coaching, se arregla en el producto.

**El problema real no es detectar el motivo, es que no se fragmente.** Un LLM
suelto escribe "cobro duplicado", "Cobro duplicado", "duplicidad de cobro" y
"cobro repetido" para lo mismo, y la agregación deja de servir. Aquí se ataca
por dos lados:

1. Al analizar, se le pasa a la IA el **catálogo de motivos ya usados** y se le
   pide que reutilice uno si encaja; solo inventa si de verdad es nuevo.
2. Al guardar, el motivo se **normaliza** (espacios, mayúsculas, acentos) y se
   busca un equivalente en el catálogo. Si lo hay, se guarda el que ya existía.

Con eso el vocabulario crece cuando el negocio cambia, pero no se duplica.
"""

import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.call import Call

# Tope de longitud del motivo. Un motivo es una etiqueta, no un resumen: si la
# IA devuelve una frase larga, se recorta y se queda en algo agrupable.
MAX_TOPIC_CHARS = 60

# Cuántos motivos del catálogo se le enseñan a la IA. Suficiente para que
# reutilice, sin inflar el prompt de cada llamada.
CATALOGO_EN_PROMPT = 25


def _plegar(texto: str) -> str:
    """Clave de comparación: sin acentos, sin mayúsculas y sin dobles espacios."""
    sin_acentos = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_acentos.lower().split())


def clean_topic(raw) -> str | None:
    """Motivo listo para guardar, o None si no vale nada."""
    if not isinstance(raw, str):
        return None
    texto = " ".join(raw.strip().split())
    # La IA a veces devuelve "Motivo: cobro duplicado" o lo entrecomilla.
    texto = re.sub(r"^(motivo|tema|topic)\s*[:\-]\s*", "", texto, flags=re.I)
    texto = texto.strip(" .\"'“”")
    if len(texto) < 3:
        return None
    if len(texto) > MAX_TOPIC_CHARS:
        texto = texto[:MAX_TOPIC_CHARS].rsplit(" ", 1)[0].rstrip(" ,;")
    # Mayúscula inicial y el resto tal cual: respeta siglas como TEA o CTS.
    return texto[0].upper() + texto[1:]


def catalog(db: Session, limit: int = CATALOGO_EN_PROMPT) -> list[str]:
    """Motivos ya usados, de más a menos frecuente."""
    filas = db.execute(
        select(Call.topic, func.count(Call.id).label("n"))
        .where(Call.topic.is_not(None))
        .group_by(Call.topic)
        .order_by(func.count(Call.id).desc())
        .limit(limit)
    ).all()
    return [fila[0] for fila in filas if fila[0]]


def resolve_topic(db: Session, raw) -> str | None:
    """
    Normaliza el motivo devuelto por la IA y lo unifica con el catálogo.

    Si ya existe un motivo equivalente (misma clave plegada), se guarda **el que
    ya estaba**: así "Cobro duplicado" y "cobro duplicado" son la misma barra en
    el panel en vez de dos.
    """
    limpio = clean_topic(raw)
    if limpio is None:
        return None
    clave = _plegar(limpio)
    for existente in catalog(db, limit=200):
        if _plegar(existente) == clave:
            return existente
    return limpio


def topic_breakdown(
    rows: list[tuple[Call, "Analysis"]],  # noqa: F821
    red_threshold: int,
    limit: int = 10,
) -> list[dict]:
    """
    Agrupa las llamadas del periodo por motivo.

    Devuelve volumen, nota media, porcentaje en banda roja y suspendidas por
    motivo: la tabla que contesta "¿en qué nos está costando más la calidad?".
    """
    grupos: dict[str, list] = {}
    for call, analysis in rows:
        if not call.topic:
            continue
        grupos.setdefault(call.topic, []).append((call, analysis))

    resultado = []
    for motivo, grupo in grupos.items():
        notas = [a.global_score for _, a in grupo]
        rojas = sum(1 for n in notas if n < red_threshold)
        criticas = sum(1 for _, a in grupo if a.critical_failures)
        resultado.append(
            {
                "topic": motivo,
                "total_calls": len(grupo),
                "avg_score": round(sum(notas) / len(notas), 1),
                "red_calls": rojas,
                "red_pct": round(rojas / len(grupo) * 100, 1),
                "critical_calls": criticas,
            }
        )
    # Por volumen: el motivo que más entra es el que más cuesta atender.
    resultado.sort(key=lambda r: (-r["total_calls"], r["avg_score"]))
    return resultado[:limit]
