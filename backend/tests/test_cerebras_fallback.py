from app.services.llm_service import LLMService, _GROQ_TO_CEREBRAS_MODEL


def test_groq_to_cerebras_model_mapping():
    assert _GROQ_TO_CEREBRAS_MODEL["llama-3.3-70b-versatile"] == "llama-3.3-70b"
    assert _GROQ_TO_CEREBRAS_MODEL["llama-3.1-8b-instant"] == "llama3.1-8b"


def test_is_rate_limit_error_detects_429():
    exc = type("E", (), {"status_code": 429, "__str__": lambda s: "rate limit"})()
    assert LLMService._is_rate_limit_error(exc) is True


def test_is_rate_limit_error_detects_message():
    exc = ValueError("Groq request failed: Error code: 429 - rate_limit_exceeded")
    assert LLMService._is_rate_limit_error(exc) is True
