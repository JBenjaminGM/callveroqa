"""Prompt de análisis de llamadas en español (rúbrica dinámica con subcriterios)."""


def build_analysis_prompt(
    segments: list[dict],
    rubric: list[dict],
    product_note: str | None = None,
    topic_catalog: list[str] | None = None,
) -> str:
    """
    Construye el prompt que se envía al LLM para analizar una llamada.

    `segments`: lista de segmentos (cada uno con 'text', ya enmascarado). Se numeran
    para que el modelo atribuya el hablante de cada uno por su CONTENIDO.
    `rubric`: lista de dimensiones {dimension_key, dimension_name, description,
    criteria:[{name, enabled}]}. Solo los subcriterios ACTIVOS se incluyen como guía,
    y la estructura de salida `dimension_scores` se genera con las claves reales.
    `product_note`: texto de la nota de producto de la campaña asignada (la oferta
    que el ejecutivo debe presentar). Si se proporciona, la IA la usa como referencia.
    """
    rubric_lines = []
    for i, dim in enumerate(rubric, start=1):
        desc = dim.get("description") or ""
        line = f"{i}. {dim['dimension_name'].upper()} (clave: {dim['dimension_key']})"
        if desc:
            line += f": {desc}"
        enabled = [
            c.get("name")
            for c in (dim.get("criteria") or [])
            if c.get("enabled") and c.get("name")
        ]
        if enabled:
            line += "\n   Subcriterios a evaluar: " + "; ".join(enabled)
        if dim.get("allow_na"):
            cuando = (dim.get("na_condition") or "").strip()
            line += (
                "\n   PUEDE NO APLICAR"
                + (f" ({cuando})" if cuando else "")
                + ": si no aplica a esta llamada, su score es null."
            )
        rubric_lines.append(line)
    rubric_block = "\n".join(rubric_lines)

    # Criterios críticos (auto-fail): solo los activos y marcados como críticos.
    critical_lines = [
        f"- {c['name']} (dimensión: {dim['dimension_key']})"
        for dim in rubric
        for c in (dim.get("criteria") or [])
        if c.get("enabled") and c.get("critical") and c.get("name")
    ]
    critical_block = ""
    if critical_lines:
        critical_block = (
            "\n\nCRITERIOS CRÍTICOS (incumplir cualquiera SUSPENDE la llamada entera):\n"
            + "\n".join(critical_lines)
            + "\nRepórtalos en \"critical_failures\" SOLO si la transcripción muestra con "
            "claridad que se incumplieron. Ante la duda, no lo reportes."
        )

    # Catalogo de motivos ya usados: se le ensena para que REUTILICE en vez de
    # inventar una variante, que es lo que rompe la agregacion del panel.
    topic_block = ""
    if topic_catalog:
        topic_block = (
            "\n\nMOTIVOS YA USADOS (reutiliza uno EXACTO si encaja; solo inventa "
            "si ninguno sirve):\n- " + "\n- ".join(topic_catalog)
        )

    transcript = "\n".join(
        f"[{i}] {seg.get('text', '')}" for i, seg in enumerate(segments)
    )
    n = len(segments)
    score_lines = ",\n".join(
        f'    "{dim["dimension_key"]}": '
        + ("<int 0-100 o null si no aplica>" if dim.get("allow_na") else "<int 0-100>")
        for dim in rubric
    )

    product_note_block = ""
    if product_note:
        product_note_block = (
            "\n\nNOTA DE PRODUCTO DE LA CAMPAÑA (la oferta que el EJECUTIVO DEBE presentar):\n"
            f"{product_note}\n"
            "Ten MUY en cuenta esta nota al puntuar las dimensiones relacionadas con la "
            "oferta/promociones/productos y el cumplimiento normativo: penaliza si el "
            "ejecutivo NO ofreció lo que la nota indica, dio precios o condiciones "
            "incorrectos, omitió frases obligatorias o hizo afirmaciones prohibidas. "
            "Refleja los desajustes con la nota en el resumen y en las recomendaciones."
        )

    return f"""Eres un experto en Quality Assurance de call centers bancarios. Vas a evaluar la siguiente llamada entre un EJECUTIVO del banco y un CLIENTE.

TRANSCRIPCIÓN (cada línea es un segmento numerado [i]):
{transcript}

RÚBRICA DE EVALUACIÓN (score 0-100 por dimensión):

{rubric_block}{critical_block}{product_note_block}{topic_block}

INSTRUCCIONES:
- Evalúa CADA dimensión de la rúbrica de 0 a 100, teniendo en cuenta ÚNICAMENTE los
  subcriterios listados en ella. Basa cada score en evidencia concreta de la transcripción.
- NO APLICA: solo las dimensiones marcadas «PUEDE NO APLICAR» admiten null, y solo
  cuando la situación que evalúan no se dio en la llamada (no es lo mismo que hacerlo
  mal: si hubo una objeción y se manejó mal, puntúa bajo, no null). Explica en su
  "dimension_evidence" por qué no aplica. Las demás dimensiones llevan SIEMPRE nota.
- EVIDENCIA: para CADA dimensión, en "dimension_evidence" explica en UNA frase por qué
  pusiste esa nota y cita de 1 a 3 números de segmento [i] que la respaldan (lo que se
  dijo, o dónde debió decirse y no se dijo). Sin segmentos inventados.
- ATRIBUCIÓN DE HABLANTE (muy importante): la transcripción NO indica quién habla.
  Para CADA segmento [0..{n - 1}] decide "agent" (EJECUTIVO del banco) o "customer"
  (CLIENTE) SEGÚN EL CONTENIDO, no por el orden. Pistas:
  · "agent": saluda e identifica al banco; OFRECE productos/promociones/beneficios;
    pide datos al cliente; explica condiciones; cierra la llamada. Toda OFERTA o
    descripción de un producto/promoción ("le ofrezco", "tiene una promoción",
    "le explico los beneficios") es SIEMPRE del ejecutivo.
  · "customer": plantea su consulta o problema; da sus datos cuando se los piden;
    pregunta dudas; acepta o rechaza; agradece al final.
  Devuelve "diarization": lista de EXACTAMENTE {n} elementos ("agent" o "customer"),
  uno por segmento y en el mismo orden.
- Genera 3-5 recomendaciones accionables priorizadas (high/medium/low). El campo
  "dimension" de cada recomendación debe ser una de las claves de la rúbrica.
- El resumen debe ser de 2-3 frases.
- MOTIVO DE LA LLAMADA: en "topic", por qué llama el cliente (o por qué se le
  llama), en 2-5 palabras, como etiqueta reutilizable y no como frase. Ejemplos:
  "Oferta de tarjeta", "Reclamo por cobro", "Consulta de saldo". Si alguno de los
  motivos ya usados encaja, escríbelo EXACTAMENTE igual.
- IDENTIFICA EL NOMBRE DEL EJECUTIVO: al inicio el ejecutivo casi siempre se presenta
  ("Le atiende Juan Pérez", "Mi nombre es..."). Extrae ese nombre en
  "detected_agent_name"; si no estás seguro, usa null.

Responde EXCLUSIVAMENTE con un JSON válido con esta estructura exacta:

{{
  "detected_agent_name": "<nombre del ejecutivo o null>",
  "topic": "<motivo de la llamada, 2-5 palabras>",
  "diarization": ["agent o customer, un elemento por segmento, {n} en total"],
  "dimension_scores": {{
{score_lines}
  }},
  "dimension_evidence": {{
    "<dimension_key>": {{"justification": "<una frase>", "segments": [<i>, ...]}}
  }},
  "critical_failures": [
    {{"dimension": "<dimension_key>", "criterion": "<nombre exacto del criterio crítico>", "segment": <i o null>, "reason": "<qué pasó>"}}
  ],
  "summary": "<resumen ejecutivo de la llamada>",
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "dimension": "<dimension_key>",
      "title": "<título corto>",
      "description": "<recomendación específica accionable>"
    }}
  ]
}}
"""
