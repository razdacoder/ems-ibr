"""Shared institution-branding helpers for generated documents.

Both the attendance-sheet generator (``ems.views``) and the seat-arrangement
exporter (``ems.csv_gen``) print the same institution header on every Word
document: the configured logo, institution name/heading/address/contact, and
the active session & semester. This module centralises that so the two stay in
sync and read from ``SystemSettings``. The logo is the uploaded one only (on
Cloudinary in production); there is no bundled fallback image.
"""

import io
import logging

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

logger = logging.getLogger(__name__)

# Default for ``add_document_branding(logo=...)``: fetch the logo itself.
_LOAD = object()


def load_logo(settings_obj) -> bytes | None:
    """The uploaded ``SystemSettings.logo`` as bytes, or None.

    Read through the field's storage, so it works whether the logo is on
    Cloudinary or the local disk. A bulk export calls this once and passes
    the bytes to every document instead of downloading the logo per sheet.
    """
    logo = getattr(settings_obj, "logo", None)
    if not logo:
        return None
    try:
        with logo.storage.open(logo.name, "rb") as f:
            return f.read()
    except Exception:
        logger.warning("Institution logo %s could not be read", logo.name, exc_info=True)
        return None


def add_document_branding(doc, settings_obj, logo=_LOAD) -> None:
    """Prepend the institution header (logo + metadata + session) to ``doc``.

    Mirrors the previous inline header layout: left-aligned logo, then a
    centred institution block, then the session/semester line. ``logo`` is
    the image bytes from :func:`load_logo`; left out, it is loaded here.
    """
    if logo is _LOAD:
        logo = load_logo(settings_obj)

    # Logo (or a text placeholder when no image is available).
    logo_paragraph = doc.add_paragraph()
    logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if logo:
        try:
            run = logo_paragraph.add_run()
            run.add_picture(io.BytesIO(logo), width=Inches(1.0))
        except Exception:
            placeholder = logo_paragraph.add_run("[INSTITUTION LOGO]")
            placeholder.bold = True
    else:
        placeholder = logo_paragraph.add_run("[INSTITUTION LOGO]")
        placeholder.bold = True

    # Institution block — only render the lines that are configured.
    exam_heading = (getattr(settings_obj, "exam_heading", "") or "").strip()
    name = (getattr(settings_obj, "institution_name", "") or "").strip()
    address = (getattr(settings_obj, "institution_address", "") or "").strip()
    email = (getattr(settings_obj, "contact_email", "") or "").strip()
    phone = (getattr(settings_obj, "contact_phone", "") or "").strip()

    if exam_heading:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(exam_heading.upper())
        r.bold = True
        r.font.size = Pt(12)

    if name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name.upper())
        r.bold = True
        r.font.size = Pt(14)

    contact_bits = [bit for bit in (address, email, phone) if bit]
    if contact_bits:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for i, bit in enumerate(contact_bits):
            run = p.add_run(bit)
            if i < len(contact_bits) - 1:
                run.add_break()

    # Session / semester line.
    session_paragraph = doc.add_paragraph()
    session_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    session_run = session_paragraph.add_run(
        f"SESSION: {settings_obj.session}"
    )
    session_run.bold = True
    session_run.add_break()
    semester_run = session_paragraph.add_run(
        f"SEMESTER: {settings_obj.semester}"
    )
    semester_run.bold = True

    # Spacer before the document body.
    doc.add_paragraph()
