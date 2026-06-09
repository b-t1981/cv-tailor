import uuid
from pathlib import Path

from docx import Document

from app.config import settings
from app.models.schemas import ParagraphInfo, TailorRequest
from app.services.cv_extractor import build_tailored_paragraphs, extract_cv_paragraphs
from app.services.docx_processor import (
    apply_modifications,
    load_docx,
    paragraphs_to_prompt_text,
    save_docx,
)
from app.services.llm_service import llm_service
from app.services.modification_sanitizer import sanitize_modifications
from app.services.pdf_exporter import export_docx_to_pdf
from app.services.prompt_service import prompt_service


def _build_pdf_docx(paragraphs: list[ParagraphInfo], output_path: Path) -> None:
    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph.text)
    save_docx(doc, str(output_path))


class CVTailorService:
    def preview(self, file_path: Path, original_filename: str) -> dict:
        paragraphs = extract_cv_paragraphs(file_path)
        return {
            "filename": original_filename,
            "paragraphs": paragraphs,
        }

    def process(
        self,
        file_path: Path,
        original_filename: str,
        request: TailorRequest,
    ) -> dict:
        suffix = file_path.suffix.lower()
        job_id = str(uuid.uuid4())

        prompts = prompt_service.load()
        if request.custom_system_prompt:
            prompts.system_prompt = request.custom_system_prompt
        if request.custom_user_prompt:
            prompts.user_prompt = request.custom_user_prompt

        paragraphs = extract_cv_paragraphs(file_path)
        cv_text = paragraphs_to_prompt_text(paragraphs)

        modifications, summary = llm_service.tailor_cv(
            prompts=prompts,
            job_description=request.job_description,
            cv_paragraphs=cv_text,
            output_language=request.output_language,
            provider=request.llm_provider,
            model=request.llm_model,
        )
        modifications = sanitize_modifications(paragraphs, modifications)

        tailored_paragraphs = build_tailored_paragraphs(paragraphs, modifications)

        if suffix == ".docx":
            doc = load_docx(str(file_path))
            applied = apply_modifications(doc, modifications)
            output_filename = f"{job_id}_tailored.docx"
            output_path = settings.output_path / output_filename
            save_docx(doc, str(output_path))
        elif suffix == ".pdf":
            output_filename = f"{job_id}_tailored.docx"
            output_path = settings.output_path / output_filename
            _build_pdf_docx(tailored_paragraphs, output_path)
            applied = len(modifications)
        else:
            raise ValueError("Unsupported file format. Use .docx or .pdf")

        pdf_filename = f"{job_id}_tailored.pdf"
        pdf_path = settings.output_path / pdf_filename
        download_url_pdf = None
        if export_docx_to_pdf(output_path, pdf_path, fallback_paragraphs=tailored_paragraphs):
            download_url_pdf = f"/api/download/{pdf_filename}"

        return {
            "job_id": job_id,
            "original_filename": original_filename,
            "output_filename": output_filename,
            "download_url": f"/api/download/{output_filename}",
            "download_url_pdf": download_url_pdf,
            "modifications_count": applied,
            "summary": summary,
            "modified_paragraphs": modifications,
            "original_paragraphs": paragraphs,
            "tailored_paragraphs": tailored_paragraphs,
            "llm_provider": request.llm_provider,
            "llm_model": request.llm_model or settings.default_model_for(request.llm_provider),
        }


cv_tailor_service = CVTailorService()
