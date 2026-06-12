"""Secondary embedded path: DOCX → HTML (mammoth) → PDF (xhtml2pdf)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_HTML_SHELL = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  @page {{ size: A4; margin: 1.2cm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.35; color: #111; }}
  h1,h2,h3 {{ margin: 0.4em 0 0.2em; }}
  p {{ margin: 0.2em 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.3em 0; }}
  td, th {{ vertical-align: top; padding: 3px 5px; }}
  strong {{ font-weight: bold; }}
</style></head><body>{body}</body></html>"""


def convert_docx_to_pdf_via_html(docx_path: Path, pdf_path: Path) -> bool:
    try:
        import mammoth
        from xhtml2pdf import pisa
    except ImportError:
        logger.warning("mammoth/xhtml2pdf not installed — HTML PDF path unavailable")
        return False

    try:
        with open(docx_path, "rb") as handle:
            result = mammoth.convert_to_html(handle)
        html = _HTML_SHELL.format(body=result.value)
        with open(pdf_path, "wb") as output:
            status = pisa.CreatePDF(html.encode("utf-8"), dest=output, encoding="utf-8")
        if status.err:
            return False
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logger.warning("mammoth/xhtml2pdf conversion failed: %s", exc)
        return False
