from app.api.http_errors import exception_to_http
from app.services.llm_service import LLMService


def test_old_groq_value_error_is_sanitized():
    exc = ValueError(
        "Groq request failed: Error code: 429 - "
        "{'error': {'message': 'Rate limit reached. Please try again in 33m46.944s.'}}"
    )
    http_exc = exception_to_http(exc, "groq")
    assert http_exc.status_code == 429
    assert "Quota Groq" in http_exc.detail
    assert "34 minutes" in http_exc.detail or "environ 34 minutes" in http_exc.detail


def test_format_provider_error_from_429_message():
    exc = ValueError("Groq request failed: Error code: 429 - Rate limit reached. Please try again in 19m51s.")
    message = LLMService._format_provider_error(exc, "groq")
    assert "Quota Groq" in message
    assert "20 minutes" in message
