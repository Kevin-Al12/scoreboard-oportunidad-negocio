"""Generación del reporte PDF de top sectores.

Usa reportlab (según el stack pedido) para armar un documento simple:
tabla de ranking + una sección por sector con su score y un resumen
narrativo basado en las notas cargadas y los criterios que más pesaron.
"""

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape as _esc

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.scoring import ResultadoScore


@dataclass
class SectorParaReporte:
    nombre: str
    descripcion: str
    notas: str
    fecha_evaluacion: date
    resultado: ResultadoScore


def generar_pdf_top_sectores(sectores: list[SectorParaReporte]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    titulo_style = styles["Title"]
    subtitulo_style = ParagraphStyle(
        "Subtitulo", parent=styles["Normal"], textColor=colors.grey, spaceAfter=12
    )
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]
    nota_style = ParagraphStyle("Nota", parent=styles["BodyText"], textColor=colors.HexColor("#444444"))

    story = []
    story.append(Paragraph("Scoreboard de Oportunidad de Negocio", titulo_style))
    story.append(
        Paragraph(
            f"Reporte generado el {datetime.now():%d/%m/%Y %H:%M} — Top {len(sectores)} sectores",
            subtitulo_style,
        )
    )

    tabla_data = [["#", "Sector", "Score (0-100)", "Fecha evaluación"]]
    for i, s in enumerate(sectores, start=1):
        tabla_data.append(
            [str(i), _esc(s.nombre), f"{s.resultado.score_0_a_100:.1f}", s.fecha_evaluacion.strftime("%d/%m/%Y")]
        )

    tabla = Table(tabla_data, colWidths=[1.2 * cm, 7 * cm, 3.5 * cm, 3.5 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]
        )
    )
    story.append(tabla)
    story.append(Spacer(1, 1 * cm))

    for i, s in enumerate(sectores, start=1):
        story.append(Paragraph(f"{i}. {_esc(s.nombre)} — {s.resultado.score_0_a_100:.1f}/100", heading_style))
        if s.descripcion:
            story.append(Paragraph(_esc(s.descripcion), body_style))
        story.append(Paragraph(_esc(s.resultado.resumen_texto()), body_style))

        detalle_data = [["Criterio", "Calificación", "Peso", "Contribución"]]
        for d in s.resultado.detalle:
            detalle_data.append(
                [_esc(d.criterio_nombre), f"{d.valor}/5", f"{d.peso_normalizado:.0%}", f"{d.contribucion:.2f}"]
            )
        detalle_tabla = Table(detalle_data, colWidths=[6 * cm, 3 * cm, 2.5 * cm, 3.5 * cm])
        detalle_tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(Spacer(1, 0.2 * cm))
        story.append(detalle_tabla)

        if s.notas:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(f"<b>Notas:</b> {_esc(s.notas)}", nota_style))

        story.append(Spacer(1, 0.8 * cm))

    doc.build(story)
    return buffer.getvalue()
