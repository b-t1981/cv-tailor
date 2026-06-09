from pathlib import Path

from app.models.schemas import ApplicationKitRequest, ParagraphInfo
from app.services.cv_extractor import extract_cv_paragraphs
from app.services.cv_storage_service import cv_storage_service
from app.services.docx_processor import paragraphs_to_readable_cv
from app.services.llm_service import llm_service


class ApplicationService:
    def _resolve_cv_text(self, paragraphs: list[ParagraphInfo] | None) -> str:
        if paragraphs:
            return paragraphs_to_readable_cv(paragraphs)

        metadata = cv_storage_service.load_metadata()
        if metadata and metadata.get("paragraphs"):
            return paragraphs_to_readable_cv(metadata["paragraphs"])

        file_path = cv_storage_service.get_file_path()
        if file_path:
            extracted = extract_cv_paragraphs(Path(file_path))
            if extracted:
                return paragraphs_to_readable_cv(extracted)

        raise ValueError("No CV available. Upload a CV on the home page first.")

    def generate_kit(self, request: ApplicationKitRequest) -> dict:
        cv_text = self._resolve_cv_text(request.paragraphs)
        return llm_service.generate_application_kit(
            cv_text=cv_text,
            job_description=request.job_description,
            output_language=request.output_language,
            provider=request.llm_provider,
            model=request.llm_model,
            company_name=request.company_name or "",
            job_title=request.job_title or "",
            recruiter_name=request.recruiter_name or "",
            tone=request.tone,
        )


application_service = ApplicationService()
