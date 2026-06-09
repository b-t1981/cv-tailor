import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.models.schemas import (
    ApplicationKitRequest,
    ApplicationKitResponse,
    CVPreviewResponse,
    HealthResponse,
    LLMProvidersResponse,
    MatchScoreRequest,
    MatchScoreResponse,
    PromptConfig,
    PromptUpdateRequest,
    StoredCVResponse,
    TailorRequest,
    TailorResponse,
)
from app.services.application_service import application_service
from app.services.cv_extractor import extract_cv_paragraphs
from app.services.cv_storage_service import cv_storage_service
from app.services.cv_tailor import cv_tailor_service
from app.services.llm_service import llm_service
from app.services.match_service import match_service
from app.services.prompt_service import prompt_service

router = APIRouter()

ALLOWED_EXTENSIONS = {".docx", ".pdf"}


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
async def update_prompts(payload: PromptUpdateRequest) -> PromptConfig:
    config = PromptConfig(
        system_prompt=payload.system_prompt,
        user_prompt=payload.user_prompt,
    )
    return prompt_service.save(config)


@router.post("/prompts/reset", response_model=PromptConfig)
async def reset_prompts() -> PromptConfig:
    return prompt_service.reset()


@router.get("/cv/last", response_model=StoredCVResponse)
async def get_last_cv() -> StoredCVResponse:
    metadata = cv_storage_service.load_metadata()
    if not metadata:
        raise HTTPException(status_code=404, detail="No CV in memory")

    file_path = cv_storage_service.get_file_path()
    paragraphs = metadata["paragraphs"]
    if file_path:
        fresh_paragraphs = extract_cv_paragraphs(file_path)
        if fresh_paragraphs:
            paragraphs = fresh_paragraphs

    return StoredCVResponse(
        filename=metadata["filename"],
        paragraphs=paragraphs,
        saved_at=metadata.get("saved_at"),
    )


@router.get("/cv/last/file")
async def get_last_cv_file() -> FileResponse:
    file_path = cv_storage_service.get_file_path()
    metadata = cv_storage_service.load_metadata()
    if not file_path or not metadata:
        raise HTTPException(status_code=404, detail="No CV file in memory")

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    return FileResponse(
        path=file_path,
        filename=metadata["filename"],
        media_type=media_types.get(file_path.suffix.lower(), "application/octet-stream"),
    )


@router.post("/application/kit", response_model=ApplicationKitResponse)
async def generate_application_kit(payload: ApplicationKitRequest) -> ApplicationKitResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

    try:
        result = application_service.generate_kit(payload)
        return ApplicationKitResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "API key" in message else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/match", response_model=MatchScoreResponse)
async def compute_match(payload: MatchScoreRequest) -> MatchScoreResponse:
    if not settings.is_provider_configured(payload.llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{payload.llm_provider}' is not configured")

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


@router.post("/preview", response_model=CVPreviewResponse)
async def preview_cv(file: UploadFile = File(...)) -> CVPreviewResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

    preview_id = str(uuid.uuid4())
    upload_path = settings.upload_path / f"{preview_id}{suffix}"

    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = cv_tailor_service.preview(
            file_path=upload_path,
            original_filename=file.filename,
        )
        cv_storage_service.save(upload_path, file.filename, result["paragraphs"])
        metadata = cv_storage_service.load_metadata()
        paragraphs = metadata["paragraphs"] if metadata else result["paragraphs"]
        return CVPreviewResponse(
            filename=file.filename,
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
    job_description: str = Form(...),
    file: UploadFile | None = File(default=None),
    output_language: str = Form(default="fr"),
    llm_provider: str = Form(default="openai"),
    llm_model: str | None = Form(default=None),
    custom_system_prompt: str | None = Form(default=None),
    custom_user_prompt: str | None = Form(default=None),
) -> TailorResponse:
    stored_path = cv_storage_service.get_file_path()
    stored_meta = cv_storage_service.load_metadata()

    if file and file.filename:
        suffix = Path(file.filename).suffix.lower()
        original_filename = file.filename
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")
    elif stored_path and stored_meta:
        suffix = stored_path.suffix.lower()
        original_filename = stored_meta["filename"]
    else:
        raise HTTPException(status_code=400, detail="No file provided and no CV in memory")

    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Job description must be at least 20 characters")

    if output_language not in ("fr", "en"):
        raise HTTPException(status_code=400, detail="Output language must be 'fr' or 'en'")

    if llm_provider not in ("openai", "groq", "claude"):
        raise HTTPException(status_code=400, detail="LLM provider must be 'openai', 'groq', or 'claude'")

    if not settings.is_provider_configured(llm_provider):
        raise HTTPException(status_code=400, detail=f"API key for '{llm_provider}' is not configured")

    job_id = str(uuid.uuid4())
    upload_path = settings.upload_path / f"{job_id}{suffix}"
    copied_from_storage = False

    try:
        if file and file.filename:
            with open(upload_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        else:
            shutil.copy2(stored_path, upload_path)
            copied_from_storage = True

        request = TailorRequest(
            job_description=job_description,
            output_language=output_language,
            llm_provider=llm_provider,
            llm_model=llm_model or None,
            custom_system_prompt=custom_system_prompt or None,
            custom_user_prompt=custom_user_prompt or None,
        )

        result = cv_tailor_service.process(
            file_path=upload_path,
            original_filename=original_filename,
            request=request,
        )

        try:
            match = match_service.score_from_paragraphs(
                job_description=job_description,
                paragraphs=result["original_paragraphs"],
                output_language=output_language,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            result["match_score"] = match["score"]
        except Exception:
            result["match_score"] = None

        if not copied_from_storage or (file and file.filename):
            cv_storage_service.save(upload_path, original_filename, result["original_paragraphs"])

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
async def download_file(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    file_path = settings.output_path / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    suffix = file_path.suffix.lower()

    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=media_types.get(suffix, "application/octet-stream"),
    )
