import uuid
from pathlib import Path

from docx import Document

from app.config import settings
from app.models.schemas import ParagraphInfo, TailorRequest
from app.services.cv_extractor import build_tailored_paragraphs, extract_cv_paragraphs
from app.services.cv_storage_service import cv_storage_service
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
from app.services.tailor_intensity import get_intensity_profile


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

    def _run_tailor_llm(
        self,
        request: TailorRequest,
        paragraphs: list[ParagraphInfo],
        cv_text: str,
        extra_user_suffix: str = "",
        block_filter: set[str] | None = None,
    ) -> tuple[dict[str, str], str]:
        profile = get_intensity_profile(request.tailor_intensity)
        prompts = prompt_service.load()
        if request.custom_system_prompt:
            prompts.system_prompt = request.custom_system_prompt
        if request.custom_user_prompt:
            prompts.user_prompt = request.custom_user_prompt

        prompts.user_prompt = prompts.user_prompt + profile.user_prompt_suffix + extra_user_suffix

        if block_filter:
            filtered_lines = [
                line
                for line in cv_text.split("\n")
                if any(block_id in line for block_id in block_filter)
            ]
            cv_text = "\n".join(filtered_lines) if filtered_lines else cv_text

        modifications, summary = llm_service.tailor_cv(
            prompts=prompts,
            job_description=request.job_description,
            cv_paragraphs=cv_text,
            output_language=request.output_language,
            provider=request.llm_provider,
            model=request.llm_model,
            temperature=profile.temperature,
        )
        modifications = sanitize_modifications(
            paragraphs,
            modifications,
            max_new_word_ratio=profile.max_new_word_ratio,
        )

        if (
            not block_filter
            and len(modifications) < profile.min_modifications_before_retry
            and request.job_description.strip()
        ):
            retry_prompts = prompts.model_copy()
            retry_prompts.user_prompt = retry_prompts.user_prompt + profile.retry_prompt_suffix
            retry_mods, retry_summary = llm_service.tailor_cv(
                prompts=retry_prompts,
                job_description=request.job_description,
                cv_paragraphs=paragraphs_to_prompt_text(paragraphs),
                output_language=request.output_language,
                provider=request.llm_provider,
                model=request.llm_model,
                temperature=profile.temperature,
            )
            retry_mods = sanitize_modifications(
                paragraphs,
                retry_mods,
                max_new_word_ratio=profile.max_new_word_ratio,
            )
            if len(retry_mods) > len(modifications):
                modifications = retry_mods
                summary = retry_summary

        return modifications, summary

    def process(
        self,
        file_path: Path,
        original_filename: str,
        request: TailorRequest,
    ) -> dict:
        job_id = str(uuid.uuid4())
        paragraphs = extract_cv_paragraphs(file_path)
        cv_text = paragraphs_to_prompt_text(paragraphs)
        modifications, summary = self._run_tailor_llm(request, paragraphs, cv_text)
        tailored_paragraphs = build_tailored_paragraphs(paragraphs, modifications)

        return {
            "job_id": job_id,
            "original_filename": original_filename,
            "output_filename": "",
            "download_url": None,
            "download_url_pdf": None,
            "modifications_count": len(modifications),
            "summary": summary,
            "modified_paragraphs": modifications,
            "original_paragraphs": paragraphs,
            "tailored_paragraphs": tailored_paragraphs,
            "llm_provider": request.llm_provider,
            "llm_model": request.llm_model or settings.default_model_for(request.llm_provider),
            "tailor_intensity": request.tailor_intensity,
            "match_score": None,
        }

    def retry_rejected(
        self,
        session_id: str,
        request: TailorRequest,
        rejected_block_ids: list[str],
        kept_modifications: dict[str, str],
    ) -> dict:
        stored_path = cv_storage_service.get_file_path(session_id)
        if not stored_path:
            raise ValueError("No CV in memory. Upload a CV first.")

        paragraphs = extract_cv_paragraphs(stored_path)
        cv_text = paragraphs_to_prompt_text(paragraphs)
        block_filter = set(rejected_block_ids)

        extra = (
            "\n\nIMPORTANT: Only return modifications for these block IDs: "
            + ", ".join(rejected_block_ids)
        )
        new_mods, summary = self._run_tailor_llm(
            request,
            paragraphs,
            cv_text,
            extra_user_suffix=extra,
            block_filter=block_filter,
        )

        merged = {**kept_modifications}
        for block_id, text in new_mods.items():
            if block_id in block_filter:
                merged[block_id] = text

        tailored_paragraphs = build_tailored_paragraphs(paragraphs, merged)
        return {
            "modified_paragraphs": merged,
            "tailored_paragraphs": tailored_paragraphs,
            "summary": summary,
            "modifications_count": len(merged),
        }

    def apply_to_stored_cv(
        self,
        session_id: str,
        modifications: dict[str, str],
        export_pdf: bool = True,
    ) -> dict:
        stored_path = cv_storage_service.get_file_path(session_id)
        metadata = cv_storage_service.load_metadata(session_id)
        if not stored_path or not metadata:
            raise ValueError("No CV in memory. Upload a CV first.")

        if not modifications:
            raise ValueError("No modifications to apply")

        suffix = stored_path.suffix.lower()
        job_id = str(uuid.uuid4())
        paragraphs = extract_cv_paragraphs(stored_path)
        tailored_paragraphs = build_tailored_paragraphs(paragraphs, modifications)
        session_output = settings.session_output_path(session_id)

        if suffix == ".docx":
            doc = load_docx(str(stored_path))
            applied = apply_modifications(doc, modifications)
            output_filename = f"{job_id}_tailored.docx"
            output_path = session_output / output_filename
            save_docx(doc, str(output_path))
        elif suffix == ".pdf":
            output_filename = f"{job_id}_tailored.docx"
            output_path = session_output / output_filename
            _build_pdf_docx(tailored_paragraphs, output_path)
            applied = len(modifications)
        else:
            raise ValueError("Unsupported file format. Use .docx or .pdf")

        download_url_pdf = None
        if export_pdf:
            pdf_filename = f"{job_id}_tailored.pdf"
            pdf_path = session_output / pdf_filename
            if export_docx_to_pdf(output_path, pdf_path, fallback_paragraphs=tailored_paragraphs):
                download_url_pdf = f"/api/download/{pdf_filename}"

        return {
            "download_url": f"/api/download/{output_filename}",
            "download_url_pdf": download_url_pdf,
            "modifications_count": applied,
            "tailored_paragraphs": tailored_paragraphs,
        }


cv_tailor_service = CVTailorService()
