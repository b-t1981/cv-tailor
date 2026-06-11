from unittest.mock import MagicMock, patch

from openai import RateLimitError

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


def test_get_cerebras_api_key_reads_env(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("CEREBAS_API_KEY", raising=False)
    monkeypatch.setenv("CEREBRAS_API_KEY", "csk-test-key-12345678901234567890")
    cfg = Settings()
    assert cfg.get_cerebras_api_key().startswith("csk-test")


def test_call_llm_falls_back_to_cerebras_on_groq_429():
    service = LLMService()
    rate_exc = RateLimitError(
        "rate limit",
        response=MagicMock(status_code=429),
        body={"error": {"message": "Please try again in 10m0s"}},
    )

    with patch.object(service, "_call_openai_compatible") as mock_call:
        mock_call.side_effect = [rate_exc, '{"score": 80}']
        with patch("app.services.llm_service.settings") as settings:
            settings.is_cerebras_fallback_available.return_value = True
            settings.cerebras_model = "llama-3.3-70b"
            result = service._call_llm("groq", "llama-3.3-70b-versatile", "sys", "user")

    assert mock_call.call_count == 2
    assert mock_call.call_args_list[1].kwargs["provider"] == "cerebras"
    assert result == '{"score": 80}'
