import secrets
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["openai", "groq", "claude"]

_DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
_DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str = ""
    cerebras_model: str = "llama-3.3-70b"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    default_llm_provider: LLMProvider = "openai"
    prompts_file: str = "prompts/default_prompts.json"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    stored_cv_dir: str = "stored_cv"
    cors_origins: str = "http://localhost:3000"
    # docx2pdf ouvre Microsoft Word (dialogue imprimante sur Windows) — désactivé par défaut
    pdf_use_word: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024
    output_ttl_hours: int = 48
    rate_limit_per_minute: int = 60
    session_ttl_hours: int = 168
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    allow_prompt_writes: bool = False
    admin_api_token: str = ""
    deepl_api_key: str = ""
    deepl_use_free_api: bool = True

    @property
    def deepl_api_url(self) -> str:
        return _DEEPL_FREE_URL if self.deepl_use_free_api else _DEEPL_PRO_URL

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def prompts_path(self) -> Path:
        path = Path(self.prompts_file)
        if not path.is_absolute():
            path = self.base_dir / path
        return path

    @property
    def upload_path(self) -> Path:
        path = self.base_dir / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_path(self) -> Path:
        path = self.base_dir / self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def session_storage_path(self, session_id: str) -> Path:
        path = self.base_dir / self.stored_cv_dir / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def session_output_path(self, session_id: str) -> Path:
        path = self.output_path / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def is_admin_token_valid(self, token: str | None) -> bool:
        expected = self.admin_api_token.strip()
        if not expected:
            return False
        return bool(token and secrets.compare_digest(token, expected))

    @staticmethod
    def _is_valid_api_key(key: str) -> bool:
        cleaned = key.strip()
        if len(cleaned) < 20:
            return False

        placeholder_markers = (
            "your-key",
            "your-openai",
            "your-claude",
            "your-groq",
            "your-cerebras",
            "csk-your",
            "sk-your",
            "gsk-your",
            "sk-ant-your",
            "changeme",
            "example",
            "placeholder",
        )
        lowered = cleaned.lower()
        return not any(marker in lowered for marker in placeholder_markers)

    def is_deepl_configured(self) -> bool:
        key = self.deepl_api_key.strip()
        if len(key) < 20:
            return False
        lowered = key.lower()
        return not any(marker in lowered for marker in ("your-deepl", "changeme", "example", "placeholder"))

    def is_provider_configured(self, provider: str) -> bool:
        keys = {
            "openai": self.openai_api_key,
            "groq": self.groq_api_key,
            "cerebras": self.cerebras_api_key,
            "claude": self.anthropic_api_key,
        }
        key = keys.get(provider, "")
        return self._is_valid_api_key(key)

    def first_configured_provider(self) -> LLMProvider | None:
        for provider in ("openai", "groq", "claude"):
            if self.is_provider_configured(provider):
                return provider
        return None

    def default_model_for(self, provider: LLMProvider) -> str:
        models = {
            "openai": self.openai_model,
            "groq": self.groq_model,
            "cerebras": self.cerebras_model,
            "claude": self.anthropic_model,
        }
        return models[provider]


settings = Settings()
