import logging
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import fitz

from app.config import settings
from app.models.schemas import ParagraphInfo
from app.services.docx_pdf_html import convert_docx_to_pdf_via_html
from app.services.docx_pdf_renderer import render_docx_to_pdf

logger = logging.getLogger(__name__)

_PAGE_WIDTH = 595
_PAGE_HEIGHT = 842
_MARGIN_X = 50
_MARGIN_TOP = 50
_MARGIN_BOTTOM = 50
_WRAP_WIDTH = 88


def libreoffice_available() -> bool:
    return bool(shutil.which("soffice") or shutil.which("libreoffice"))


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

    profile_dir = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    env["TMPDIR"] = "/tmp"

    cmd = [
        soffice,
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--norestore",
        f"-env:UserInstallation=file://{profile_dir.as_posix()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(pdf_path.parent),
        str(docx_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=180,
            env=env,
            text=True,
        )
        if result.stderr:
            logger.debug("LibreOffice stderr: %s", result.stderr[:300])
        generated = pdf_path.parent / f"{docx_path.stem}.pdf"
        if generated.exists() and generated != pdf_path:
            generated.replace(pdf_path)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc))[:500]
        logger.warning("LibreOffice PDF conversion failed (exit %s): %s", exc.returncode, detail)
        return False
    except Exception as exc:
        logger.warning("LibreOffice PDF conversion failed: %s", exc)
        return False
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def _wrap_lines(text: str, width: int = _WRAP_WIDTH) -> list[str]:
    lines: list[str] = []
    for block in text.split("\n"):
        stripped = block.strip()
        if not stripped:
            lines.append("")
            continue
        wrapped = textwrap.wrap(stripped, width=width, break_long_words=True, replace_whitespace=False)
        lines.extend(wrapped or [""])
    return lines


def _write_paragraphs_pdf(paragraphs: list[ParagraphInfo], pdf_path: Path) -> bool:
    """Last-resort linear text — layout is not preserved."""
    try:
        doc = fitz.open()
        page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        y = _MARGIN_TOP
        bottom = _PAGE_HEIGHT - _MARGIN_BOTTOM

        for paragraph in paragraphs:
            text = paragraph.text.strip()
            if not text:
                y += 6
                continue

            fontsize = 12 if paragraph.is_heading else 10
            line_height = fontsize * 1.35
            fontname = "hebo" if paragraph.is_heading else "helv"

            for line in _wrap_lines(text):
                if y + line_height > bottom:
                    page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
                    y = _MARGIN_TOP

                if line:
                    page.insert_text(
                        (_MARGIN_X, y + fontsize),
                        line,
                        fontsize=fontsize,
                        fontname=fontname,
                    )
                y += line_height

            y += 6 if paragraph.is_heading else 4

        doc.save(str(pdf_path))
        doc.close()
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logger.warning("Linear PDF fallback failed: %s", exc)
        return False


def _try_embedded_converters(docx_path: Path, pdf_path: Path) -> bool:
    if render_docx_to_pdf(docx_path, pdf_path):
        logger.info("PDF generated via embedded OOXML renderer")
        return True
    if convert_docx_to_pdf_via_html(docx_path, pdf_path):
        logger.info("PDF generated via mammoth/xhtml2pdf")
        return True
    return False


def export_docx_to_pdf(
    docx_path: Path,
    pdf_path: Path,
    fallback_paragraphs: list[ParagraphInfo] | None = None,
) -> bool:
    """
    DOCX → PDF (first success wins).
    If PDF_PREFER_LIBREOFFICE=true (Render Docker): LibreOffice → embedded OOXML → Word → linear.
    Default: embedded OOXML (columns/tables) → LibreOffice → Word → linear text.
    """
    if settings.pdf_prefer_libreoffice and libreoffice_available():
        if _convert_with_libreoffice(docx_path, pdf_path):
            logger.info("PDF generated via LibreOffice (preferred)")
            return True
        logger.warning("LibreOffice preferred but conversion failed — trying embedded converters")

    if _try_embedded_converters(docx_path, pdf_path):
        return True

    if libreoffice_available() and _convert_with_libreoffice(docx_path, pdf_path):
        logger.info("PDF generated via LibreOffice")
        return True

    if settings.pdf_use_word and _convert_with_docx2pdf(docx_path, pdf_path):
        logger.info("PDF generated via Microsoft Word")
        return True

    if fallback_paragraphs and _write_paragraphs_pdf(fallback_paragraphs, pdf_path):
        logger.warning(
            "PDF generated as linear text only — all converters failed. Prefer DOCX download."
        )
        return True

    return False
