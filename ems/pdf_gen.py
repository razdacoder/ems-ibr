"""reportlab PDF builders for the Hall Directory and VISA documents.

Each slot in the payload (see :func:`ems.directory.build_payload`) renders to
its own page. Both documents carry the configured institution branding header.
"""

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from ems.branding import resolve_logo_path


def _styles():
    base = getSampleStyleSheet()["Normal"]
    return {
        "inst": ParagraphStyle(
            "Inst", parent=base, fontName="Helvetica-Bold",
            fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title", parent=base, fontName="Helvetica-Bold",
            fontSize=13, leading=16, alignment=TA_CENTER, spaceBefore=4,
            spaceAfter=8,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base, fontName="Helvetica-Bold",
            fontSize=9, leading=11,
        ),
        "visa": ParagraphStyle(
            "Visa", parent=base, fontName="Helvetica-Bold",
            fontSize=12, leading=20, alignment=TA_JUSTIFY,
        ),
    }


def _branding(settings_obj, styles) -> list:
    flow = []
    path = resolve_logo_path(settings_obj)
    if path:
        try:
            img = Image(path)
            ratio = (img.imageWidth or 1) / (img.imageHeight or 1)
            img.drawHeight = 14 * mm
            img.drawWidth = 14 * mm * ratio
            img.hAlign = "CENTER"
            flow.append(img)
        except Exception:
            pass
    name = (getattr(settings_obj, "institution_name", "") or "").strip()
    if name:
        flow.append(Paragraph(name.upper(), styles["inst"]))
    return flow


def _hall_flowables(slot, settings_obj, styles) -> list:
    flow = _branding(settings_obj, styles)
    flow.append(Paragraph(slot["title"], styles["title"]))
    cell = styles["cell"]
    data = [["Hall", "Class Name", "No. Of Students", "Matric Numbers"]]
    for r in slot["rows"]:
        data.append([
            Paragraph(r["hall"], cell),
            Paragraph(r["class_name"], cell),
            str(r["count"]),
            Paragraph(r["matric_range"], cell),
        ])
    if not slot["rows"]:
        data.append([
            Paragraph("No seat allocation generated for this slot.", cell),
            "", "", "",
        ])
    tbl = Table(
        data, colWidths=[28 * mm, 58 * mm, 33 * mm, 67 * mm], repeatRows=1
    )
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(tbl)
    return flow


def _visa_flowables(slot, settings_obj, styles) -> list:
    flow = _branding(settings_obj, styles)
    flow.append(Paragraph(slot["title"], styles["title"]))
    text = (
        ", ".join(slot["codes"])
        if slot["codes"]
        else "No classes scheduled for this slot."
    )
    box = Table([[Paragraph(text, styles["visa"])]], colWidths=[176 * mm])
    box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    flow.append(box)
    return flow


def build_pdf(doc_type: str, payload: list[dict], settings_obj) -> bytes:
    """Render the payload to a multi-page PDF (one page per slot)."""
    buf = io.BytesIO()
    document = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=14 * mm, bottomMargin=14 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Hall Directory" if doc_type == "hall" else "VISA",
    )
    styles = _styles()
    story = []
    for i, slot in enumerate(payload):
        if i > 0:
            story.append(PageBreak())
        if doc_type == "hall":
            story += _hall_flowables(slot, settings_obj, styles)
        else:
            story += _visa_flowables(slot, settings_obj, styles)
    if not payload:
        story.append(Paragraph("No data for the selected scope.", styles["title"]))
    document.build(story)
    return buf.getvalue()
