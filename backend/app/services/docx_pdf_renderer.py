"""Convert DOCX to PDF by reading OOXML (word/document.xml) — pure Python, no LibreOffice."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{W_NS}}}"


def _local(tag: str) -> str:
    return tag.replace(f"{{{W_NS}}}", "") if tag.startswith("{") else tag


def _text_from_t_nodes(parent: ET.Element) -> str:
    return "".join(node.text or "" for node in parent.iter(f"{_W}t"))


def _run_is_bold(run: ET.Element) -> bool:
    rpr = run.find(f"{_W}rPr")
    if rpr is None:
        return False
    bold = rpr.find(f"{_W}b")
    if bold is None:
        return False
    val = bold.get(f"{_W}val")
    return val is None or val.lower() not in ("0", "false")


def _paragraph_markup(paragraph: ET.Element) -> str:
    chunks: list[str] = []
    for child in paragraph:
        if _local(child.tag) != "r":
            continue
        text = _text_from_t_nodes(child)
        if not text:
            continue
        safe = escape(text)
        chunks.append(f"<b>{safe}</b>" if _run_is_bold(child) else safe)
    if chunks:
        return "".join(chunks)
    plain = _text_from_t_nodes(paragraph).strip()
    return escape(plain)


def _paragraph_has_thick_bottom_border(paragraph: ET.Element) -> bool:
    ppr = paragraph.find(f"{_W}pPr")
    if ppr is None:
        return False
    pbdr = ppr.find(f"{_W}pBdr")
    if pbdr is None:
        return False
    bottom = pbdr.find(f"{_W}bottom")
    if bottom is None:
        return False
    sz = bottom.get(f"{_W}sz")
    try:
        return int(sz) >= 12 if sz else False
    except ValueError:
        return False


def _color_from_hex_attr(value: str | None) -> str | None:
    if not value or value.lower() in ("auto", "ffffff", "none"):
        return None
    value = value.strip().lstrip("#")
    if len(value) == 6:
        return f"#{value.upper()}"
    return None


def _cell_background(tc: ET.Element) -> str | None:
    tcpr = tc.find(f"{_W}tcPr")
    if tcpr is None:
        return None
    shd = tcpr.find(f"{_W}shd")
    if shd is None:
        return None
    return _color_from_hex_attr(shd.get(f"{_W}fill"))


def _cell_colspan(tc: ET.Element) -> int:
    tcpr = tc.find(f"{_W}tcPr")
    if tcpr is None:
        return 1
    grid_span = tcpr.find(f"{_W}gridSpan")
    if grid_span is None:
        return 1
    try:
        return max(1, int(grid_span.get(f"{_W}val", "1")))
    except ValueError:
        return 1


def _twips_to_points(value: str | None) -> float | None:
    if not value:
        return None
    try:
        twips = int(value)
    except ValueError:
        return None
    return twips / 20.0


def _table_col_widths(table: ET.Element, usable_width: float) -> list[float] | None:
    grid = table.find(f"{_W}tblGrid")
    if grid is None:
        return None
    raw: list[float] = []
    for col in grid.findall(f"{_W}gridCol"):
        width = _twips_to_points(col.get(f"{_W}w"))
        if width and width > 0:
            raw.append(width)
    if not raw:
        return None
    total = sum(raw)
    if total <= 0:
        return None
    return [usable_width * (w / total) for w in raw]


def _cell_paragraphs_markup(tc: ET.Element) -> str:
    parts: list[str] = []
    for paragraph in tc.findall(f"{_W}p"):
        markup = _paragraph_markup(paragraph).strip()
        if markup:
            parts.append(markup)
    return "<br/>".join(parts) if parts else "&nbsp;"


def render_docx_to_pdf(docx_path: Path, pdf_path: Path) -> bool:
    """Render DOCX body (paragraphs + tables) to PDF via ReportLab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        logger.warning("ReportLab not installed — embedded DOCX PDF export unavailable")
        return False

    try:
        with zipfile.ZipFile(docx_path, "r") as archive:
            document_xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        logger.warning("Could not read DOCX archive: %s", exc)
        return False

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        logger.warning("Invalid document.xml: %s", exc)
        return False

    body = root.find(f".//{_W}body")
    if body is None:
        return False

    margin = 1.4 * cm
    page_width, _page_height = A4
    usable_width = page_width - 2 * margin

    base_styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "CvNormal",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        spaceAfter=3,
    )
    heading = ParagraphStyle(
        "CvHeading",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=4,
        spaceAfter=4,
    )
    centered = ParagraphStyle(
        "CvCentered",
        parent=heading,
        alignment=TA_CENTER,
        fontSize=12,
    )

    story: list = []

    def paragraph_style_for(text: str, markup: str, centered_block: bool) -> ParagraphStyle:
        if centered_block:
            return centered
        plain = text.strip()
        if len(plain) < 90 and plain.isupper() and any(c.isalpha() for c in plain):
            return heading
        return normal

    for element in list(body):
        tag = _local(element.tag)
        if tag == "sectPr":
            continue

        if tag == "p":
            markup = _paragraph_markup(element).strip()
            plain = _text_from_t_nodes(element).strip()
            if not plain and not markup:
                story.append(Spacer(1, 4))
                continue

            ppr = element.find(f"{_W}pPr")
            jc = ppr.find(f"{_W}jc") if ppr is not None else None
            align_val = jc.get(f"{_W}val") if jc is not None else None
            is_center = align_val == "center"

            style = paragraph_style_for(plain, markup, is_center)
            story.append(Paragraph(markup or escape(plain), style))

            if _paragraph_has_thick_bottom_border(element):
                story.append(Spacer(1, 2))
                story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2E7D32")))
                story.append(Spacer(1, 6))
            continue

        if tag != "tbl":
            continue

        col_widths = _table_col_widths(element, usable_width)
        table_rows: list[list] = []
        span_commands: list[tuple] = []
        cell_styles: list[tuple] = []

        for row_idx, tr in enumerate(element.findall(f"{_W}tr")):
            row_cells: list = []
            col_cursor = 0
            for tc in tr.findall(f"{_W}tc"):
                markup = _cell_paragraphs_markup(tc)
                row_cells.append(Paragraph(markup, normal))
                colspan = _cell_colspan(tc)
                if colspan > 1:
                    span_commands.append(("SPAN", (col_cursor, row_idx), (col_cursor + colspan - 1, row_idx)))
                bg = _cell_background(tc)
                if bg:
                    cell_styles.append(("BACKGROUND", (col_cursor, row_idx), (col_cursor, row_idx), colors.HexColor(bg)))
                col_cursor += colspan
            if row_cells:
                table_rows.append(row_cells)

        if not table_rows:
            continue

        table = Table(table_rows, colWidths=col_widths, hAlign="LEFT")
        style_commands = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        style_commands.extend(span_commands)
        style_commands.extend(cell_styles)
        table.setStyle(TableStyle(style_commands))
        story.append(table)
        story.append(Spacer(1, 6))

    if not story:
        return False

    try:
        pdf = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            title=docx_path.stem,
        )
        pdf.build(story)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logger.warning("ReportLab DOCX PDF render failed: %s", exc)
        return False
