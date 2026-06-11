from anthropic import AuthenticationError as AnthropicAuthError
from fastapi import HTTPException
from openai import APIStatusError

from app.services.llm_service import LLMService, PROVIDER_LABELS


def _infer_provider(message: str) -> str:
    lower = message.lower()
    for provider_id, label in PROVIDER_LABELS.items():
        if provider_id in lower or label.lower() in lower:
            return provider_id
    if "cerebras" in lower:
        return "cerebras"
    return "groq"


def _looks_like_raw_provider_error(message: str) -> bool:
    lower = message.lower()
    return any(
        marker in lower
        for marker in (
            "request failed: error code",
            "rate_limit_exceeded",
            "rate limit reached",
            "error code: 429",
            "invalid_api_key",
        )
    )


def exception_to_http(exc: Exception, provider: str | None = None) -> HTTPException:
    if isinstance(exc, ValueError):
        detail = str(exc)
        if _looks_like_raw_provider_error(detail):
            selected = provider or _infer_provider(detail)
            status = 429 if "429" in detail else 400
            return HTTPException(
                status_code=status,
                detail=LLMService._format_provider_error(exc, selected),
            )
        return HTTPException(status_code=400, detail=detail)

    if isinstance(exc, (AuthenticationError, AnthropicAuthError, APIStatusError)):
        selected = provider or _infer_provider(str(exc))
        status = getattr(exc, "status_code", None) or 400
        if status not in (400, 401, 403, 429, 502, 503, 504):
            status = 400
        return HTTPException(
            status_code=status,
            detail=LLMService._format_provider_error(exc, selected),
        )

    message = str(exc)
    if _looks_like_raw_provider_error(message):
        selected = provider or _infer_provider(message)
        status = 429 if "429" in message or "rate_limit" in message.lower() else 400
        return HTTPException(
            status_code=status,
            detail=LLMService._format_provider_error(exc, selected),
        )

    status_code = 400 if "API key" in message or "not configured" in message else 500
    return HTTPException(status_code=status_code, detail=message)


def raise_as_http(exc: Exception, provider: str | None = None) -> None:
    raise exception_to_http(exc, provider) from exc
