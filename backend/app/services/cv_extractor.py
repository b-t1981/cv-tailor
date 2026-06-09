from pathlib import Path

from app.models.schemas import ParagraphInfo
from app.services.docx_processor import extract_paragraphs, load_docx
from app.services.pdf_processor import extract_paragraphs_from_pdf


def extract_cv_paragraphs(file_path: Path) -> list[ParagraphInfo]:
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        return extract_paragraphs(load_docx(str(file_path)))
    if suffix == ".pdf":
        return extract_paragraphs_from_pdf(str(file_path))
    raise ValueError("Unsupported file format. Use .docx or .pdf")


def build_tailored_paragraphs(
    paragraphs: list[ParagraphInfo],
    modifications: dict[str, str],
) -> list[ParagraphInfo]:
    tailored: list[ParagraphInfo] = []
    for paragraph in paragraphs:
        if paragraph.id in modifications:
            tailored.append(
                ParagraphInfo(
                    id=paragraph.id,
                    text=modifications[paragraph.id],
                    style=paragraph.style,
                    is_heading=paragraph.is_heading,
                    modified=True,
                )
            )
        else:
            tailored.append(paragraph.model_copy())
    return tailored
