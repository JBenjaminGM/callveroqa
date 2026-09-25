"""Call analysis prompt in English (dynamic rubric with subcriteria)."""


def build_analysis_prompt(
    segments: list[dict],
    rubric: list[dict],
    product_note: str | None = None,
    topic_catalog: list[str] | None = None,
) -> str:
    """Build the prompt sent to the LLM to analyze a call (English version).

    `segments`: transcript segments (each with already-masked 'text'), numbered so
    the model attributes the speaker by CONTENT. `rubric`: dimensions with
    {dimension_key, dimension_name, description, criteria:[{name, enabled}]}. Only
    ENABLED subcriteria are included, and `dimension_scores` is generated from the
    real keys. `product_note`: the assigned campaign's product note (the offer the
    agent must present); when provided, the AI uses it as the reference.
    """
    rubric_lines = []
    for i, dim in enumerate(rubric, start=1):
        desc = dim.get("description") or ""
        line = f"{i}. {dim['dimension_name'].upper()} (key: {dim['dimension_key']})"
        if desc:
            line += f": {desc}"
        enabled = [
            c.get("name")
            for c in (dim.get("criteria") or [])
            if c.get("enabled") and c.get("name")
        ]
        if enabled:
            line += "\n   Sub-criteria to evaluate: " + "; ".join(enabled)
        rubric_lines.append(line)
    rubric_block = "\n".join(rubric_lines)

    # Critical (auto-fail) criteria: only enabled ones flagged as critical.
    critical_lines = [
        f"- {c['name']} (dimension: {dim['dimension_key']})"
        for dim in rubric
        for c in (dim.get("criteria") or [])
        if c.get("enabled") and c.get("critical") and c.get("name")
    ]
    critical_block = ""
    if critical_lines:
        critical_block = (
            "\n\nCRITICAL CRITERIA (failing any of them FAILS the whole call):\n"
            + "\n".join(critical_lines)
            + "\nReport them in \"critical_failures\" ONLY if the transcript clearly "
            "shows they were breached. When in doubt, do not report."
        )

    # Existing topics, so the model REUSES one instead of inventing a variant.
    topic_block = ""
    if topic_catalog:
        topic_block = (
            "\n\nTOPICS ALREADY IN USE (reuse one EXACTLY if it fits; only invent "
            "a new one if none does):\n- " + "\n- ".join(topic_catalog)
        )

    transcript = "\n".join(
        f"[{i}] {seg.get('text', '')}" for i, seg in enumerate(segments)
    )
    n = len(segments)
    score_lines = ",\n".join(
        f'    "{dim["dimension_key"]}": <int 0-100>' for dim in rubric
    )

    product_note_block = ""
    if product_note:
        product_note_block = (
            "\n\nCAMPAIGN PRODUCT NOTE (the offer the AGENT MUST present):\n"
            f"{product_note}\n"
            "Take this note strongly into account when scoring the dimensions related "
            "to the offer/promotions/products and regulatory compliance: penalize if "
            "the agent did NOT offer what the note states, gave wrong prices/terms, "
            "omitted mandatory phrases or made prohibited claims. Reflect any mismatch "
            "with the note in the summary and the recommendations."
        )

    return f"""You are an expert in Quality Assurance for banking call centers. You will evaluate the following call between a bank AGENT and a CUSTOMER.

TRANSCRIPT (each line is a numbered segment [i]):
{transcript}

EVALUATION RUBRIC (score 0-100 per dimension):

{rubric_block}{critical_block}{product_note_block}{topic_block}

INSTRUCTIONS:
- Score EACH rubric dimension 0-100, considering ONLY the sub-criteria listed in it.
  Base each score on concrete evidence from the transcript.
- EVIDENCE: for EACH dimension, in "dimension_evidence" explain in ONE sentence why you
  gave that score and cite 1 to 3 segment numbers [i] backing it (what was said, or where
  it should have been said and wasn't). Do not invent segments.
- SPEAKER ATTRIBUTION (very important): the transcript is NOT pre-labeled. For EACH
  segment [0..{n - 1}] decide "agent" (bank AGENT) or "customer" (CUSTOMER) based on
  CONTENT, not order. Cues:
  · "agent": greets and identifies the bank; OFFERS products/promotions/benefits;
    asks the customer for data; explains terms; closes the call. Any product or
    promotion OFFER is ALWAYS the agent.
  · "customer": states their query/problem; gives data when asked; asks questions;
    accepts or declines; thanks at the end.
  Return "diarization": a list of EXACTLY {n} elements ("agent" or "customer"), one
  per segment in the same order.
- Generate 3-5 prioritized actionable recommendations (high/medium/low). Each
  recommendation's "dimension" must be one of the rubric keys.
- The summary must be 2-3 sentences.
- CALL TOPIC: in "topic", why the customer is calling (or being called), in 2-5
  words, as a reusable label and not a sentence. If one of the topics already in
  use fits, write it EXACTLY as listed.
- IDENTIFY THE AGENT'S NAME into "detected_agent_name"; use null if unsure.

Respond EXCLUSIVELY with valid JSON in this exact structure:

{{
  "detected_agent_name": "<agent name or null>",
  "topic": "<call topic, 2-5 words>",
  "diarization": ["agent or customer, one element per segment, {n} total"],
  "dimension_scores": {{
{score_lines}
  }},
  "dimension_evidence": {{
    "<dimension_key>": {{"justification": "<one sentence>", "segments": [<i>, ...]}}
  }},
  "critical_failures": [
    {{"dimension": "<dimension_key>", "criterion": "<exact critical criterion name>", "segment": <i or null>, "reason": "<what happened>"}}
  ],
  "summary": "<executive summary of the call>",
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "dimension": "<dimension_key>",
      "title": "<short title>",
      "description": "<specific actionable recommendation>"
    }}
  ]
}}
"""
