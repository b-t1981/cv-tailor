import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.models.schemas import (
    ApplicationKitRequest,
    ApplicationKitResponse,
    ApplyModificationsRequest,
    ApplyModificationsResponse,
    CoverLetterExportRequest,
    CoverLetterExportResponse,
    CVPreviewResponse,
    HealthResponse,
    JobAnalysisRequest,
    JobAnalysisResponse,
    LLMProvidersResponse,
    MatchScoreRequest,
    MatchScoreResponse,
    PromptConfig,
    PromptUpdateRequest,
    RetryModificationsRequest,
    RetryModificationsResponse,
    TailorRequest,
    TailorResponse,
    TranslateCVRequest,
    TranslateCVResponse,
)
from app.services.application_service import application_service
from app.services.cover_letter_exporter import export_cover_letter_docx, export_cover_letter_pdf
from app.services.cv_storage_service import cv_storage_service
from app.services.cv_tailor import cv_tailor_service
from app.services.llm_service import llm_service
from app.services.match_service import match_service
from app.services.prompt_service import prompt_service
from app.session import get_session_id

router = APIRouter()

ALLOWED_EXTENSIONS = {".docx", ".pdf"}


def _safe_upload_name(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def _enforce_upload_size(path: Path) -> None:
    if path.stat().st_size > settings.max_upload_bytes:
        path.unlink(missing_ok=True)
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File too large (max {max_mb} MB)")


def _require_prompt_admin(request: Request) -> None:
    if settings.allow_prompt_writes:
        return
    token = request.headers.get("X-Admin-Token")
    if settings.is_admin_token_valid(token):
        return
    raise HTTPException(status_code=403, detail="Prompt editing is disabled")


def _resolve_session_download(session_id: str, filename: str) -> Path:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    session_dir = settings.session_output_path(session_id).resolve()
    file_path = (session_dir / safe_name).resolve()
    try:
        file_path.relative_to(session_dir)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    providers_info = llm_service.list_providers()
    default = settings.default_model_for(settings.default_llm_provider)
    return HealthResponse(
        status="ok",
        default_provider=settings.default_llm_provider,
        default_model=default,
        prompts_loaded=prompt_service.exists(),
        providers=providers_info.providers,
    )


@router.get("/llm/providers", response_model=LLMProvidersResponse)
async def get_llm_providers() -> LLMProvidersResponse:
    return llm_service.list_providers()


@router.get("/prompts", response_model=PromptConfig)
async def get_prompts() -> PromptConfig:
    return prompt_service.load()


@router.put("/prompts", response_model=PromptConfig)
async def update_prompts(request: Request, payload: PromptUpdateRequest) -> PromptConfig:
    _require_prompt_admin(request)
    config = PromptConfig(
        system_prompt=payload.system_prompt,
        user_prompt=payload.user_prompt,
    )
    return prompt_service.save(config)


@router.post("/prompts/reset", response_model=PromptConfig)
async def reset_prompts(request: Request) -> PromptConfig:
    _require_prompt_admin(request)
    return prompt_service.reset()


@router.post("/application/cover-letter/docx", response_model=CoverLetterExportResponse)
async def export_cover_letter(
    request: Request,
    payload: CoverLetterExportRequest,
) -> CoverLetterExportResponse:
    session_id = get_session_id(request)
    try:
        filename, download_url = export_cover_letter_docx(
            session_id,
            payload.cover_letter,
            company_name=payload.company_name or "",
            job_title=payload.job_title or "",
        )
        pdf_result = export_cover_letter_pdf(
            session_id,
            payload.cover_letter,
            company_name=payload.company_name or "",
            job_title=payload.job_title or "",
        )
        pdf_url = pdf_result[1] if pdf_result else None
        return CoverLetterExportResponse(
            filename=filename,
            download_url=download_url,
            download_url_pdf=pdf_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cover letter export failed: {exc}") from exc


@router.post("/application/kit", response_model=ApplicationKitResponse)
async def generate_application_kit(
    request: Request,
    payload: ApplicationKitRequest,
) -> ApplicationKitResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    session_id = get_session_id(request)
    try:
        result = application_service.generate_kit(session_id, payload)
        return ApplicationKitResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/analyze", response_model=JobAnalysisResponse)
async def analyze_job(request: Request, payload: JobAnalysisRequest) -> JobAnalysisResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    session_id = get_session_id(request)
    try:
        if payload.paragraphs:
            result = match_service.analyze_from_paragraphs(
                job_description=payload.job_description,
                paragraphs=payload.paragraphs,
                output_language=payload.output_language,
                llm_provider=payload.llm_provider,
                llm_model=payload.llm_model,
            )
        else:
            result = match_service.analyze_from_stored_cv(
                session_id,
                job_description=payload.job_description,
                output_language=payload.output_language,
                llm_provider=payload.llm_provider,
                llm_model=payload.llm_model,
            )
        return JobAnalysisResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/tailor/retry", response_model=RetryModificationsResponse)
async def retry_tailor_modifications(
    request: Request,
    payload: RetryModificationsRequest,
) -> RetryModificationsResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    session_id = get_session_id(request)
    try:
        tailor_request = TailorRequest(
            job_description=payload.job_description,
            output_language=payload.output_language,
            llm_provider=payload.llm_provider,
            llm_model=payload.llm_model,
            tailor_intensity=payload.tailor_intensity,
        )
        result = cv_tailor_service.retry_rejected(
            session_id,
            request=tailor_request,
            rejected_block_ids=payload.rejected_block_ids,
            kept_modifications=payload.kept_modifications,
        )
        return RetryModificationsResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retry failed: {exc}") from exc


@router.post("/tailor/apply", response_model=ApplyModificationsResponse)
async def apply_tailor_modifications(
    request: Request,
    payload: ApplyModificationsRequest,
) -> ApplyModificationsResponse:
    session_id = get_session_id(request)
    try:
        result = cv_tailor_service.apply_to_stored_cv(session_id, payload.modifications)
        return ApplyModificationsResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Apply failed: {exc}") from exc


@router.post("/match", response_model=MatchScoreResponse)
async def compute_match(request: Request, payload: MatchScoreRequest) -> MatchScoreResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    session_id = get_session_id(request)
    try:
        if payload.paragraphs:
            result = match_service.score_from_paragraphs(
                job_description=payload.job_description,
                paragraphs=payload.paragraphs,
                output_language=payload.output_language,
                llm_provider=payload.llm_provider,
                llm_model=payload.llm_model,
            )
        else:
            result = match_service.score_from_stored_cv(
                session_id,
                job_description=payload.job_description,
                output_language=payload.output_language,
                llm_provider=payload.llm_provider,
                llm_model=payload.llm_model,
            )
        return MatchScoreResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/translate", response_model=TranslateCVResponse)
async def translate_cv(request: Request, payload: TranslateCVRequest) -> TranslateCVResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    try:
        result = cv_tailor_service.translate_paragraphs(
            paragraphs=payload.paragraphs,
            target_language=payload.target_language,
            llm_provider=payload.llm_provider,
            llm_model=payload.llm_model,
        )
        return TranslateCVResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/preview", response_model=CVPreviewResponse)
async def preview_cv(request: Request, file: UploadFile = File(...)) -> CVPreviewResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    safe_name = _safe_upload_name(file.filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

    session_id = get_session_id(request)
    preview_id = str(uuid.uuid4())
    upload_path = settings.upload_path / f"{session_id}_{preview_id}{suffix}"

    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        _enforce_upload_size(upload_path)

        result = cv_tailor_service.preview(
            file_path=upload_path,
            original_filename=safe_name,
        )
        cv_storage_service.save(session_id, upload_path, safe_name, result["paragraphs"])
        metadata = cv_storage_service.load_metadata(session_id)
        paragraphs = metadata["paragraphs"] if metadata else result["paragraphs"]
        return CVPreviewResponse(
            filename=safe_name,
            paragraphs=paragraphs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}") from exc
    finally:
        if upload_path.exists():
            upload_path.unlink()


@router.post("/tailor", response_model=TailorResponse)
async def tailor_cv(
    request: Request,
    job_description: str = Form(...),
    file: UploadFile | None = File(default=None),
    output_language: str = Form(default="fr"),
    llm_provider: str = Form(default="openai"),
    llm_model: str | None = Form(default=None),
    tailor_intensity: str = Form(default="strong"),
    custom_system_prompt: str | None = Form(default=None),
    custom_user_prompt: str | None = Form(default=None),
) -> TailorResponse:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    original_filename = _safe_upload_name(file.filename)
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Job description must be at least 20 characters")

    if output_language not in ("fr", "en"):
        raise HTTPException(status_code=400, detail="Output language must be 'fr' or 'en'")

    if llm_provider not in ("openai", "groq", "claude"):
        raise HTTPException(status_code=400, detail="LLM provider must be 'openai', 'groq', or 'claude'")

    if tailor_intensity not in ("light", "strong", "ats"):
        raise HTTPException(status_code=400, detail="Tailor intensity must be 'light', 'strong', or 'ats'")

    if not settings.is_provider_configured(llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{llm_provider}' is not configured")

    session_id = get_session_id(request)
    job_id = str(uuid.uuid4())
    upload_path = settings.upload_path / f"{session_id}_{job_id}{suffix}"

    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        _enforce_upload_size(upload_path)

        tailor_request = TailorRequest(
            job_description=job_description,
            output_language=output_language,
            llm_provider=llm_provider,
            llm_model=llm_model or None,
            tailor_intensity=tailor_intensity,
            custom_system_prompt=custom_system_prompt or None,
            custom_user_prompt=custom_user_prompt or None,
        )

        result = cv_tailor_service.process(
            file_path=upload_path,
            original_filename=original_filename,
            request=tailor_request,
        )

        result["match_score"] = None

        cv_storage_service.save(session_id, upload_path, original_filename, result["original_paragraphs"])

        return TailorResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message or "not configured" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink()


@router.get("/download/{filename}")
async def download_file(request: Request, filename: str) -> FileResponse:
    session_id = get_session_id(request)
    file_path = _resolve_session_download(session_id, filename)

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    suffix = file_path.suffix.lower()

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_types.get(suffix, "application/octet-stream"),
    )
