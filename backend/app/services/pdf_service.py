"""Generación de reportes PDF del análisis de una llamada."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.call import Call

# Nombres legibles de cada dimensión de la rúbrica.
DIMENSION_LABELS = {
    "greeting": "Saludo y protocolo",
    "assertiveness": "Asertividad y tono",
    "promotions": "Promociones / productos",
    "compliance": "Cumplimiento normativo",
    "resolution": "Resolución efectiva",
    "objections": "Manejo de objeciones",
    "sentiment": "Sentimiento del cliente",
}


def _classify(score: int) -> str:
    """Clasifica un score según la regla de negocio RN-03."""
    if score >= 80:
        return "Excelente"
    if score >= 60:
        return "Aceptable"
    return "Requiere atención"


def generate_call_report(call: Call) -> bytes:
    """
    Genera el PDF del reporte de una llamada y lo devuelve como bytes.

    Incluye metadata, score global, scores por dimensión, recomendaciones
    y la transcripción completa.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Reporte llamada #{call.id}")
    styles = getSampleStyleSheet()
    story: list = []

    # --- Encabezado ---
    story.append(Paragraph("CallVeroQA — Reporte de llamada", styles["Title"]))
    story.append(Paragraph(
        "<i>Vista previa para evaluación. Documento generado automáticamente; "
        "no utilizar con datos reales de clientes sin aprobación de Compliance.</i>",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # --- Metadata ---
    # Nombre a mostrar: ejecutivo registrado o, si no, el detectado por la IA.
    if call.agent:
        agent_name = call.agent.name
    elif call.detected_agent_name:
        agent_name = f"{call.detected_agent_name} (no registrado)"
    else:
        agent_name = "Sin identificar"

    meta = [
        ["Llamada #", str(call.id)],
        ["Ejecutivo", agent_name],
        ["Fecha de llamada", str(call.call_date or "-")],
        ["Duración (s)", str(call.duration_seconds or "-")],
        ["Campaña", call.campaign_type or "-"],
        ["Estado", call.status.value],
    ]
    meta_table = Table(meta, colWidths=[5 * cm, 11 * cm])
    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    analysis = call.analysis
    if analysis is not None:
        # --- Score global ---
        story.append(Paragraph(
            f"Score Global: <b>{analysis.global_score}/100</b> "
            f"({_classify(analysis.global_score)})",
            styles["Heading2"],
        ))
        story.append(Spacer(1, 0.3 * cm))

        # --- Scores por dimensión ---
        dim_rows = [["Dimensión", "Score", "Clasificación"]]
        for key, score in (analysis.dimension_scores or {}).items():
            dim_rows.append([
                DIMENSION_LABELS.get(key, key),
                str(score),
                _classify(int(score)),
            ])
        # Las que no aplicaban se listan igual: si desaparecieran del informe,
        # quien lo lea pensaría que la rúbrica tenía una dimensión menos.
        for key in analysis.not_applicable or []:
            dim_rows.append([DIMENSION_LABELS.get(key, key), "—", "No aplica"])
        dim_table = Table(dim_rows, colWidths=[8 * cm, 3 * cm, 5 * cm])
        dim_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b8441f")),  # Rust (acento de marca)
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 0.5 * cm))

        # --- Resumen ---
        if analysis.summary:
            story.append(Paragraph("Resumen", styles["Heading3"]))
            story.append(Paragraph(analysis.summary, styles["Normal"]))
            story.append(Spacer(1, 0.4 * cm))

        # --- Recomendaciones ---
        if analysis.recommendations:
            story.append(Paragraph("Recomendaciones", styles["Heading3"]))
            for rec in analysis.recommendations:
                story.append(Paragraph(
                    f"<b>[{rec.get('priority', '-').upper()}] {rec.get('title', '')}</b>: "
                    f"{rec.get('description', '')}",
                    styles["Normal"],
                ))
                story.append(Spacer(1, 0.2 * cm))
            story.append(Spacer(1, 0.4 * cm))
    else:
        story.append(Paragraph(
            "Esta llamada aún no tiene análisis disponible.", styles["Normal"]
        ))

    # --- Transcripción ---
    if call.transcription is not None:
        story.append(Paragraph("Transcripción", styles["Heading3"]))
        story.append(Paragraph(call.transcription.full_text, styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
