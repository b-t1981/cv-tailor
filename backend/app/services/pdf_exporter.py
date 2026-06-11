import shutil
import subprocess
from pathlib import Path

import fitz

from app.config import settings
from app.models.schemas import ParagraphInfo


def _convert_with_docx2pdf(docx_path: Path, pdf_path: Path) -> bool:
    try:
        from docx2pdf import convert

        convert(str(docx_path), str(pdf_path))
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def _convert_with_libreoffice(docx_path: Path, pdf_path: Path) -> bool:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return False

    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf_path.parent),
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        generated = pdf_path.parent / f"{docx_path.stem}.pdf"
        if generated.exists() and generated != pdf_path:
            generated.replace(pdf_path)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def _write_paragraphs_pdf(paragraphs: list[ParagraphInfo], pdf_path: Path) -> bool:
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        margin_x = 50
        y = 50
        line_height = 14
        bottom = 800

        for paragraph in paragraphs:
            if not paragraph.text.strip():
                continue
            if y > bottom:
                page = doc.new_page(width=595, height=842)
                y = 50
            fontsize = 12 if paragraph.is_heading else 10
            page.insert_text((margin_x, y), paragraph.text, fontsize=fontsize)
            y += line_height + (2 if paragraph.is_heading else 0)

        doc.save(str(pdf_path))
        doc.close()
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def export_docx_to_pdf(
    docx_path: Path,
    pdf_path: Path,
    fallback_paragraphs: list[ParagraphInfo] | None = None,
) -> bool:
    # LibreOffice (headless) puis PyMuPDF — pas de fenêtre système.
    if _convert_with_libreoffice(docx_path, pdf_path):
        return True
    if fallback_paragraphs and _write_paragraphs_pdf(fallback_paragraphs, pdf_path):
        return True
    # docx2pdf pilote Word via COM → peut afficher « Attente imprimante » sur Windows.
    if settings.pdf_use_word and _convert_with_docx2pdf(docx_path, pdf_path):
        return True
    return False
