from app.models.schemas import ParagraphInfo
from app.services.cv_storage_service import cv_storage_service
from app.services.docx_processor import paragraphs_to_readable_cv
from app.services.llm_service import llm_service


class MatchService:
    def score_from_stored_cv(
        self,
        session_id: str,
        job_description: str,
        output_language: str,
        llm_provider: str,
        llm_model: str | None,
    ) -> dict:
        metadata = cv_storage_service.load_metadata(session_id)
        if not metadata:
            raise ValueError("No CV in memory. Upload a CV first.")

        paragraphs: list[ParagraphInfo] = metadata["paragraphs"]
        cv_text = paragraphs_to_readable_cv(paragraphs)
        return llm_service.compute_match_score(
            job_description=job_description,
            cv_paragraphs=cv_text,
            output_language=output_language,
            provider=llm_provider,  # type: ignore[arg-type]
            model=llm_model,
        )

    def score_from_paragraphs(
        self,
        job_description: str,
        paragraphs: list[ParagraphInfo],
        output_language: str,
        llm_provider: str,
        llm_model: str | None,
    ) -> dict:
        cv_text = paragraphs_to_readable_cv(paragraphs)
        return llm_service.compute_match_score(
            job_description=job_description,
            cv_paragraphs=cv_text,
            output_language=output_language,
            provider=llm_provider,  # type: ignore[arg-type]
            model=llm_model,
        )

    def analyze_from_paragraphs(
        self,
        job_description: str,
        paragraphs: list[ParagraphInfo],
        output_language: str,
        llm_provider: str,
        llm_model: str | None,
    ) -> dict:
        cv_text = paragraphs_to_readable_cv(paragraphs)
        return llm_service.analyze_job_fit(
            job_description=job_description,
            cv_paragraphs=cv_text,
            output_language=output_language,
            provider=llm_provider,  # type: ignore[arg-type]
            model=llm_model,
        )

    def analyze_from_stored_cv(
        self,
        session_id: str,
        job_description: str,
        output_language: str,
        llm_provider: str,
        llm_model: str | None,
    ) -> dict:
        metadata = cv_storage_service.load_metadata(session_id)
        if not metadata:
            raise ValueError("No CV in memory. Upload a CV first.")
        return self.analyze_from_paragraphs(
            job_description=job_description,
            paragraphs=metadata["paragraphs"],
            output_language=output_language,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )


match_service = MatchService()
