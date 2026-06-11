import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

from anthropic import Anthropic, AuthenticationError as AnthropicAuthError
from openai import APIStatusError, AuthenticationError, OpenAI, RateLimitError

from app.config import LLMProvider, settings
from app.models.schemas import LLMProviderInfo, LLMProvidersResponse, PromptConfig

AVAILABLE_MODELS: dict[LLMProvider, list[str]] = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "claude": [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ],
}

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "claude": "Claude (Anthropic)",
}

OpenAICompatibleProvider = Literal["openai", "groq", "cerebras"]

_GROQ_TO_CEREBRAS_MODEL: dict[str, str] = {
    "llama-3.3-70b-versatile": "llama-3.3-70b",
    "llama-3.1-8b-instant": "llama3.1-8b",
    "mixtral-8x7b-32768": "llama-3.3-70b",
    "gemma2-9b-it": "llama3.1-8b",
}

_groq_cooldown_until: float = 0.0


def _groq_cooldown_path() -> Path:
    return settings.base_dir / ".groq_cooldown"

# Ordre = priorité (le plus spécifique en premier). Pas de "mission" seul (matche "Our Purpose and Mission").
_CORE_JOB_MARKERS = (
    "specification of core function",
    "core function",
    "key responsibilities",
    "principal responsibilities",
    "responsibilities",
    "requirements",
    "qualifications",
    "profil recherché",
    "profil recherche",
    "vos missions",
    "mission du poste",
    "votre mission",
)

_NOISE_KEYWORDS = frozenset({
    "geneva",
    "genève",
    "zurich",
    "lausanne",
    "paris",
    "london",
    "location",
    "switzerland",
    "accountability",
    "hands-on",
    "passionate",
    "partnership",
    "teamwork",
    "networking",
    "leadership",
    "communication",
    "feedback",
    "coaching",
    "mindset",
    "innovation",
    "creativity",
    "diversity",
    "excellence",
    "negotiation",
    "entrepreneurial",
    "integrity",
    "compliance",
    "ownership",
    "proactive",
    "curious",
    "availability",
    "flexibility",
    "reactivity",
    "rigor",
    "methodology",
    "private banking",
    "asset management",
    "employer",
    "values",
    "competencies",
    "purpose",
    "company",
    "efg",
    "2x8",
    "teams",
    "operators",
    "banking",
    "corporate",
    "department",
    "reporting",
})

_NOISE_SUBSTRINGS = (
    "mindset",
    "competenc",
    "our value",
    "our company",
    "client-centric",
    "growth mindset",
    "future-oriented",
    "sustainable performance",
    "mutual respect",
    "employer of choice",
)

# Concepts métier : si le CV contient un marqueur du groupe, le besoin est couvert.
_SKILL_CONCEPTS: dict[str, dict[str, tuple[str, ...]]] = {
    "scheduling": {
        "keyword_triggers": (
            "scheduler",
            "planification",
            "orchestr",
            "automic",
            "uc4",
            "control-m",
            "control m",
            "opcon",
        ),
        "cv_markers": (
            "scheduler",
            "planification",
            "planifi",
            "automic",
            "uc4",
            "control-m",
            "controlm",
            "opcon",
            "orchestr",
            "job scheduling",
        ),
    },
    "batches": {
        "keyword_triggers": ("batch", "batches", "flux"),
        "cv_markers": ("batch", "batches", "automic", "uc4", "control-m", "scheduler", "flux"),
    },
    "alarms": {
        "keyword_triggers": ("alarm", "alerte"),
        "cv_markers": ("alarm", "alerte", "alerting", "monitoring", "supervision", "splunk", "dynatrace"),
    },
    "hotlines": {
        "keyword_triggers": ("hotline", "dispatch", "escalade"),
        "cv_markers": (
            "hotline",
            "dispatch",
            "escalade",
            "l1",
            "l2",
            "niveau 1",
            "level 1",
            "astreinte",
            "on-call",
            "on call",
        ),
    },
    "it_ops": {
        "keyword_triggers": (
            "it operations",
            "operations it",
            "opérations it",
            "exploitation",
            "support applicatif",
        ),
        "cv_markers": (
            "it operations",
            "operations it",
            "exploitation",
            "support applicatif",
            "application support",
            "production applicative",
            "equipe run",
            "équipe run",
            "middleware",
            "run ",
        ),
    },
}


class LLMService:
    @staticmethod
    def _is_api_key_error(exc: Exception) -> bool:
        if isinstance(exc, (AuthenticationError, AnthropicAuthError)):
            return True
        if getattr(exc, "status_code", None) == 401:
            return True
        msg = str(exc).lower()
        return any(
            marker in msg
            for marker in (
                "invalid_api_key",
                "incorrect api key",
                "invalid x-api-key",
                "authentication",
                "unauthorized",
            )
        )

    @staticmethod
    def _extract_retry_seconds(text: str) -> int | None:
        match = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)?s", text, re.I)
        if match:
            return int(match.group(1)) * 60 + int(float(match.group(2) or 0))
        match = re.search(r"try again in (\d+(?:\.\d+)?)\s*s(?:ec)?", text, re.I)
        if match:
            return max(1, int(float(match.group(1))))
        return None

    @staticmethod
    def _format_wait_hint(seconds: int) -> str:
        if seconds < 60:
            return "quelques instants"
        minutes = max(1, round(seconds / 60))
        if minutes == 1:
            return "environ 1 minute"
        return f"environ {minutes} minutes"

    @classmethod
    def _format_provider_error(cls, exc: Exception, provider: str) -> str:
        label = PROVIDER_LABELS.get(provider, provider)
        status = getattr(exc, "status_code", None)
        msg = str(exc).lower()

        if cls._is_api_key_error(exc):
            return f"Clé API {label} invalide. Contactez l'administrateur du service."

        if status == 429 or "rate_limit" in msg or "rate limit" in msg:
            wait = cls._extract_retry_seconds(str(exc))
            if wait:
                return (
                    f"Quota {label} atteint pour aujourd'hui. "
                    f"Réessayez dans {cls._format_wait_hint(wait)}."
                )
            return (
                f"Quota {label} atteint. "
                "Réessayez dans quelques minutes ou plus tard dans la journée."
            )

        if status == 503 or "overloaded" in msg or "capacity" in msg:
            return f"Le service {label} est temporairement surchargé. Réessayez dans un instant."

        if status in (502, 504) or "timeout" in msg:
            return f"Le service {label} ne répond pas. Réessayez dans quelques minutes."

        return f"Le service {label} est momentanément indisponible. Réessayez dans quelques minutes."

    @staticmethod
    def _is_raw_provider_api_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(
            marker in msg
            for marker in (
                "request failed: error code",
                "rate_limit_exceeded",
                "rate limit reached",
                "error code: 429",
            )
        )

    @classmethod
    def _raise_provider_error(cls, exc: Exception, provider: str) -> None:
        raise ValueError(cls._format_provider_error(exc, provider)) from exc

    @classmethod
    def _handle_provider_exception(cls, exc: Exception, provider: str) -> None:
        if isinstance(exc, (AuthenticationError, AnthropicAuthError, APIStatusError)):
            cls._raise_provider_error(exc, provider)
        if cls._is_raw_provider_api_error(exc):
            cls._raise_provider_error(exc, provider)
        raise exc

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        if isinstance(exc, RateLimitError):
            return True
        if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429:
            return True
        if getattr(exc, "status_code", None) == 429:
            return True
        msg = str(exc).lower()
        return "rate_limit_exceeded" in msg or "rate limit" in msg or "error code: 429" in msg

    @classmethod
    def load_groq_cooldown(cls) -> None:
        global _groq_cooldown_until
        path = _groq_cooldown_path()
        if not path.is_file():
            return
        try:
            stored = float(path.read_text(encoding="utf-8").strip())
            if stored > time.monotonic():
                _groq_cooldown_until = stored
                logger.info("Groq cooldown loaded from disk")
        except (OSError, ValueError):
            pass

    @classmethod
    def _mark_groq_rate_limited(cls, exc: Exception) -> None:
        global _groq_cooldown_until
        wait = cls._extract_retry_seconds(str(exc))
        _groq_cooldown_until = time.monotonic() + (wait if wait else 3600)
        logger.warning("Groq rate limit — cooldown %ss", wait or 3600)
        try:
            _groq_cooldown_path().write_text(str(_groq_cooldown_until), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def is_groq_in_cooldown() -> bool:
        return time.monotonic() < _groq_cooldown_until

    def _is_groq_quota_error(self, exc: Exception) -> bool:
        return self._is_rate_limit_error(exc) or (
            self._is_raw_provider_api_error(exc) and "429" in str(exc)
        )

    def _cerebras_model_for(self, groq_model: str) -> str:
        return _GROQ_TO_CEREBRAS_MODEL.get(groq_model, settings.cerebras_model)

    def _call_cerebras_fallback(
        self,
        groq_model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        fallback_model = self._cerebras_model_for(groq_model)
        logger.warning("Falling back to Cerebras model %s", fallback_model)
        return self._call_openai_compatible(
            provider="cerebras",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=fallback_model,
            temperature=temperature,
        )

    def _call_groq_with_cerebras_fallback(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        if self.is_groq_in_cooldown():
            logger.info("Groq in cooldown — using Cerebras directly")
            return self._call_cerebras_fallback(model, system_prompt, user_prompt, temperature)

        try:
            return self._call_openai_compatible(
                provider="groq",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
            )
        except Exception as exc:
            if not self._is_groq_quota_error(exc):
                self._handle_provider_exception(exc, "groq")

            self._mark_groq_rate_limited(exc)
            if not settings.is_cerebras_fallback_available():
                logger.error("Groq quota reached but CEREBRAS_API_KEY is missing or invalid")
                wait = self._extract_retry_seconds(str(exc))
                wait_hint = self._format_wait_hint(wait) if wait else "quelques minutes"
                raise ValueError(
                    f"Quota Groq atteint pour aujourd'hui. Réessayez dans {wait_hint}. "
                    "Repli Cerebras non actif : ajoutez CEREBRAS_API_KEY sur Render."
                ) from exc

            try:
                return self._call_cerebras_fallback(model, system_prompt, user_prompt, temperature)
            except Exception as fallback_exc:
                self._handle_provider_exception(fallback_exc, "cerebras")

    def _call_llm(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        if provider == "groq" and settings.is_cerebras_fallback_available():
            return self._call_groq_with_cerebras_fallback(
                model, system_prompt, user_prompt, temperature
            )

        try:
            if provider == "claude":
                return self._call_claude(system_prompt, user_prompt, model, temperature=temperature)
            return self._call_openai_compatible(
                provider=provider,  # type: ignore[arg-type]
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
            )
        except Exception as exc:
            if provider == "groq" and self._is_groq_quota_error(exc):
                self._mark_groq_rate_limited(exc)
                wait = self._extract_retry_seconds(str(exc))
                wait_hint = self._format_wait_hint(wait) if wait else "quelques minutes"
                raise ValueError(
                    f"Quota Groq atteint pour aujourd'hui. Réessayez dans {wait_hint}. "
                    "Repli Cerebras non actif : ajoutez CEREBRAS_API_KEY sur Render."
                ) from exc
            self._handle_provider_exception(exc, provider)

    def list_providers(self) -> LLMProvidersResponse:
        providers = [
            LLMProviderInfo(
                id=provider,
                name=PROVIDER_LABELS[provider],
                models=AVAILABLE_MODELS[provider],
                default_model=settings.default_model_for(provider),
                configured=settings.is_provider_configured(provider),
            )
            for provider in ("openai", "groq", "claude")
        ]
        configured = settings.first_configured_provider()
        default_provider = (
            settings.default_llm_provider
            if settings.is_provider_configured(settings.default_llm_provider)
            else configured or settings.default_llm_provider
        )
        return LLMProvidersResponse(
            providers=providers,
            default_provider=default_provider,
        )

    def tailor_cv(
        self,
        prompts: PromptConfig,
        job_description: str,
        cv_paragraphs: str,
        output_language: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float = 0.35,
    ) -> tuple[dict[str, str], str]:
        selected_provider = provider or settings.default_llm_provider
        selected_model = model or settings.default_model_for(selected_provider)

        if not settings.is_provider_configured(selected_provider):
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} API key is not configured")

        if selected_model not in AVAILABLE_MODELS[selected_provider]:
            raise ValueError(f"Model '{selected_model}' is not available for {selected_provider}")

        language_label = "French" if output_language == "fr" else "English"
        system_prompt = prompts.system_prompt.replace("{output_language}", language_label)
        user_prompt = (
            prompts.user_prompt.replace("{job_description}", job_description)
            .replace("{cv_paragraphs}", cv_paragraphs)
            .replace("{output_language}", language_label)
        )

        content = self._call_llm(
            provider=selected_provider,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        return self._parse_response(content)

    def compute_match_score(
        self,
        job_description: str,
        cv_paragraphs: str,
        output_language: str = "fr",
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> dict:
        selected_provider = provider or settings.default_llm_provider
        selected_model = model or settings.default_model_for(selected_provider)

        if not settings.is_provider_configured(selected_provider):
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} API key is not configured")

        language_label = "French" if output_language == "fr" else "English"
        system_prompt = (
            "You are an expert recruiter. Evaluate how well a CV matches a job description.\n"
            "The CV text is extracted line-by-line from a Word document (possibly from a table layout).\n"
            "Read the ENTIRE CV carefully before answering.\n\n"
            "RULES:\n"
            "- If you see experience sections, job titles, companies, dates, skills, or diplomas in the CV, "
            "do NOT claim they are missing.\n"
            "- Score realistically: 0-30 poor fit, 40-60 partial fit, 70-85 good fit, 90-100 excellent.\n"
            "- strengths: what in the CV aligns with the job\n"
            "- gaps: only genuine missing requirements, not extraction artifacts\n\n"
            "Respond ONLY with valid JSON: "
            '{"score": 72, "summary": "brief explanation", "strengths": ["..."], "gaps": ["..."]}'
        )
        user_prompt = (
            f"Language for summary/strengths/gaps: {language_label}\n\n"
            f"## Job Description\n{job_description}\n\n"
            f"## CV Content (full text)\n{cv_paragraphs}\n\n"
            "Evaluate the match between this CV and the job. Score 0-100."
        )

        content = self._call_llm(
            provider=selected_provider,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return self._parse_match_response(content)

    def analyze_job_fit(
        self,
        job_description: str,
        cv_paragraphs: str,
        output_language: str = "fr",
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> dict:
        selected_provider = provider or settings.default_llm_provider
        selected_model = model or settings.default_model_for(selected_provider)

        if not settings.is_provider_configured(selected_provider):
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} API key is not configured")

        language_label = "French" if output_language == "fr" else "English"
        system_prompt = (
            "You are an expert recruiter and ATS analyst. Evaluate CV vs job description.\n"
            "Read the ENTIRE CV before answering.\n\n"
            "RULES:\n"
            "- score: 0-100 realistic match\n"
            "- strengths: CV elements aligned with the job\n"
            "- gaps: genuine missing requirements only\n"
            "- present_keywords: concrete skills/tools/technologies in BOTH core role requirements "
            "AND the CV (max 10)\n"
            "- missing_keywords: concrete skills/tools/technologies from CORE ROLE REQUIREMENTS only, "
            "that are NOT in the CV (max 6)\n"
            "- IGNORE for keywords: company presentation, values, competency frameworks, locations, "
            "soft skills, schedules (2x8), generic HR vocabulary\n"
            "- NEVER put a keyword in missing_keywords if it appears anywhere in the CV text\n"
            "- NEVER put a keyword in missing_keywords if it does NOT appear in core role requirements\n"
            "- NEVER list CV-only skills/tools in missing_keywords\n"
            "- NEVER invent tools (Jira, ServiceNow, Pentaho, Automic…) unless they appear "
            "verbatim in core role requirements\n"
            "- keyword_suggestions: only for validated missing_keywords (max 4)\n"
            "- gaps: 2-4 concrete job requirements from the core function NOT evidenced in the CV\n"
            "- Only list concrete skills, tools, technologies, certifications, or domain terms\n"
            "- Do NOT invent CV content\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"score": 72, "summary": "...", "strengths": ["..."], "gaps": ["..."], '
            '"present_keywords": ["..."], "missing_keywords": ["..."], '
            '"keyword_suggestions": ["..."]}'
        )
        core_job = self._extract_core_job_text(job_description)
        user_prompt = (
            f"Language for all text fields: {language_label}\n\n"
            f"## Core role requirements (USE THIS SECTION FOR KEYWORDS)\n{core_job}\n\n"
            f"## Full job description (context only)\n{job_description}\n\n"
            f"## CV Content\n{cv_paragraphs}\n\n"
            "Analyze match score and keyword coverage."
        )

        content = self._call_llm(
            provider=selected_provider,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        result = self._parse_analysis_response(content)
        result = self._sanitize_analysis_keywords(job_description, cv_paragraphs, result)
        result["gaps"] = self._sanitize_gaps(result.get("gaps", []), cv_paragraphs)
        return result

    def generate_application_kit(
        self,
        cv_text: str,
        job_description: str,
        output_language: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
        company_name: str = "",
        job_title: str = "",
        recruiter_name: str = "",
        tone: str = "professional",
    ) -> dict:
        selected_provider = provider or settings.default_llm_provider
        selected_model = model or settings.default_model_for(selected_provider)

        if not settings.is_provider_configured(selected_provider):
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} API key is not configured")

        language_label = "French" if output_language == "fr" else "English"
        tone_label = "professional and warm" if tone == "friendly" else "professional and formal"

        system_prompt = (
            "You are an expert career coach helping a candidate apply for a job.\n"
            "Generate practical application materials in JSON only.\n\n"
            "RULES:\n"
            "- Use ONLY facts from the CV — never invent experience, skills, or degrees.\n"
            "- Write in the requested language.\n"
            "- Cover letter: 3-4 short paragraphs, ready to send.\n"
            "- Recruiter message: short email body (max 120 words).\n"
            "- LinkedIn message: very short (max 300 characters).\n"
            "- Tips and checklist: actionable, specific to this candidate and job.\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"cover_letter":"...","email_subject":"...","recruiter_message":"...",'
            '"linkedin_message":"...","application_tips":["..."],"checklist":["..."],"summary":"..."}'
        )

        details = []
        if company_name:
            details.append(f"Company: {company_name}")
        if job_title:
            details.append(f"Target role: {job_title}")
        if recruiter_name:
            details.append(f"Recruiter name: {recruiter_name}")

        user_prompt = (
            f"Language: {language_label}\n"
            f"Tone: {tone_label}\n"
            f"{chr(10).join(details)}\n\n"
            f"## Job Description\n{job_description}\n\n"
            f"## Candidate CV\n{cv_text}\n\n"
            "Generate the application kit."
        )

        content = self._call_llm(
            provider=selected_provider,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        return self._parse_application_kit(content)

    @staticmethod
    def _prepare_groq_messages(system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """Groq requires the literal word 'json' in messages when using response_format json_object."""
        if not user_prompt.rstrip().lower().endswith("respond in json."):
            user_prompt = f"{user_prompt.rstrip()}\n\nRespond in json."
        return system_prompt, user_prompt

    def _call_openai_compatible(
        self,
        provider: OpenAICompatibleProvider,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.1,
    ) -> str:
        if provider == "openai":
            client = OpenAI(api_key=settings.openai_api_key)
        elif provider == "groq":
            client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            system_prompt, user_prompt = self._prepare_groq_messages(system_prompt, user_prompt)
        else:
            client = OpenAI(
                api_key=settings.get_cerebras_api_key(),
                base_url="https://api.cerebras.ai/v1",
            )
            system_prompt, user_prompt = self._prepare_groq_messages(system_prompt, user_prompt)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    def _call_claude(self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.1) -> str:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )

        parts = [block.text for block in response.content if block.type == "text"]
        return "".join(parts) or "{}"

    @staticmethod
    def _parse_application_kit(content: str) -> dict:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("LLM returned invalid JSON") from None
            data = json.loads(match.group())

        return {
            "cover_letter": str(data.get("cover_letter", "")).strip(),
            "email_subject": str(data.get("email_subject", "")).strip(),
            "recruiter_message": str(data.get("recruiter_message", "")).strip(),
            "linkedin_message": str(data.get("linkedin_message", "")).strip(),
            "application_tips": [str(item).strip() for item in data.get("application_tips", []) if item],
            "checklist": [str(item).strip() for item in data.get("checklist", []) if item],
            "summary": str(data.get("summary", "")).strip(),
        }

    @staticmethod
    def _parse_response(content: str) -> tuple[dict[str, str], str]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("LLM returned invalid JSON") from None
            data = json.loads(match.group())

        modifications = data.get("modifications", {})
        summary = data.get("summary", "CV adapted successfully.")
        if not isinstance(modifications, dict):
            raise ValueError("LLM response missing 'modifications' object")

        cleaned = {str(key): str(value) for key, value in modifications.items() if value}
        return cleaned, summary

    @staticmethod
    def _extract_core_job_text(job_description: str) -> str:
        lower = job_description.lower()
        for marker in _CORE_JOB_MARKERS:
            idx = lower.find(marker)
            if idx >= 0:
                return job_description[idx:].strip()
        if len(job_description) > 1800:
            return job_description[-1800:].strip()
        return job_description.strip()

    @staticmethod
    def _is_noise_keyword(keyword: str) -> bool:
        normalized = keyword.strip().lower()
        if not normalized or len(normalized) <= 3:
            return True
        if normalized in _NOISE_KEYWORDS:
            return True
        return any(fragment in normalized for fragment in _NOISE_SUBSTRINGS)

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text.lower())
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")

    @classmethod
    def _keyword_concept(cls, keyword: str) -> str | None:
        normalized = cls._normalize_for_match(keyword)
        for concept, data in _SKILL_CONCEPTS.items():
            if any(trigger in normalized for trigger in data["keyword_triggers"]):
                return concept
        return None

    @classmethod
    def _cv_has_concept(cls, concept: str, cv_paragraphs: str) -> bool:
        cv_normalized = cls._normalize_for_match(cv_paragraphs)
        markers = _SKILL_CONCEPTS.get(concept, {}).get("cv_markers", ())
        return any(cls._normalize_for_match(marker) in cv_normalized for marker in markers)

    @classmethod
    def _cv_covers_keyword(cls, keyword: str, cv_paragraphs: str) -> bool:
        if cls._term_in_text(keyword, cv_paragraphs):
            return True
        concept = cls._keyword_concept(keyword)
        return bool(concept and cls._cv_has_concept(concept, cv_paragraphs))

    @classmethod
    def _sanitize_gaps(cls, gaps: list[str], cv_paragraphs: str) -> list[str]:
        filtered: list[str] = []
        for gap in gaps:
            gap_normalized = cls._normalize_for_match(gap)
            skip = False
            for concept, data in _SKILL_CONCEPTS.items():
                if not any(trigger in gap_normalized for trigger in data["keyword_triggers"]):
                    continue
                if cls._cv_has_concept(concept, cv_paragraphs):
                    skip = True
                    break
            if not skip:
                filtered.append(gap)
        return filtered[:4]

    @staticmethod
    def _keyword_search_variants(keyword: str) -> list[str]:
        cleaned = keyword.strip().lower()
        variants = [cleaned] if cleaned else []
        variants.extend(match.lower() for match in re.findall(r"\(([^)]+)\)", keyword))
        for part in re.split(r"[,/|]+", keyword):
            part = part.strip().lower()
            if len(part) > 2:
                variants.append(part)
        deduped: list[str] = []
        for variant in variants:
            if variant and variant not in deduped:
                deduped.append(variant)
        return deduped

    @classmethod
    def _term_in_text(cls, keyword: str, text: str) -> bool:
        text_normalized = cls._normalize_for_match(text)
        return any(
            cls._normalize_for_match(variant) in text_normalized
            for variant in cls._keyword_search_variants(keyword)
        )

    @classmethod
    def _sanitize_analysis_keywords(
        cls,
        job_description: str,
        cv_paragraphs: str,
        result: dict,
    ) -> dict:
        core_job = cls._extract_core_job_text(job_description)
        present: list[str] = []
        missing: list[str] = []
        seen: set[str] = set()
        missing_concepts: set[str] = set()

        for keyword in result.get("present_keywords", []):
            key = keyword.strip().lower()
            if not key or key in seen or cls._is_noise_keyword(keyword):
                continue
            if not cls._term_in_text(keyword, job_description):
                continue
            if cls._cv_covers_keyword(keyword, cv_paragraphs):
                present.append(keyword)
                seen.add(key)

        for keyword in result.get("missing_keywords", []):
            key = keyword.strip().lower()
            if not key or key in seen or cls._is_noise_keyword(keyword):
                continue

            if cls._cv_covers_keyword(keyword, cv_paragraphs):
                if (
                    not cls._is_noise_keyword(keyword)
                    and cls._term_in_text(keyword, core_job)
                    and key not in seen
                ):
                    present.append(keyword)
                    seen.add(key)
                elif key not in seen:
                    seen.add(key)
                continue

            if not cls._term_in_text(keyword, core_job):
                continue

            concept = cls._keyword_concept(keyword)
            if concept and concept in missing_concepts:
                continue

            missing.append(keyword)
            seen.add(key)
            if concept:
                missing_concepts.add(concept)

        result["present_keywords"] = present[:10]
        result["missing_keywords"] = missing[:6]
        result["keyword_suggestions"] = cls._sanitize_keyword_suggestions(
            result.get("keyword_suggestions", []),
            result["missing_keywords"],
            cv_paragraphs,
            core_job,
        )
        return result

    @classmethod
    def _sanitize_keyword_suggestions(
        cls,
        suggestions: list[str],
        missing_keywords: list[str],
        cv_paragraphs: str,
        core_job: str,
    ) -> list[str]:
        if not missing_keywords:
            return []
        filtered: list[str] = []
        for suggestion in suggestions:
            text = suggestion.strip()
            if not text:
                continue
            normalized = cls._normalize_for_match(text)
            refers_to_missing = any(
                cls._normalize_for_match(keyword) in normalized
                for keyword in missing_keywords
            )
            if not refers_to_missing:
                continue
            if any(
                cls._cv_covers_keyword(keyword, cv_paragraphs)
                for keyword in missing_keywords
                if cls._normalize_for_match(keyword) in normalized
            ):
                continue
            filtered.append(text)
        return filtered[:4]

    @staticmethod
    def _parse_analysis_response(content: str) -> dict:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("LLM returned invalid JSON") from None
            data = json.loads(match.group())

        score = int(data.get("score", 0))
        score = max(0, min(100, score))
        return {
            "score": score,
            "summary": str(data.get("summary", "")),
            "strengths": [str(item) for item in data.get("strengths", []) if item],
            "gaps": [str(item) for item in data.get("gaps", []) if item],
            "present_keywords": [str(item) for item in data.get("present_keywords", []) if item],
            "missing_keywords": [str(item) for item in data.get("missing_keywords", []) if item],
            "keyword_suggestions": [
                str(item) for item in data.get("keyword_suggestions", []) if item
            ],
        }

    @staticmethod
    def _parse_match_response(content: str) -> dict:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("LLM returned invalid JSON") from None
            data = json.loads(match.group())

        score = int(data.get("score", 0))
        score = max(0, min(100, score))
        summary = str(data.get("summary", ""))
        strengths = [str(item) for item in data.get("strengths", []) if item]
        gaps = [str(item) for item in data.get("gaps", []) if item]
        return {"score": score, "summary": summary, "strengths": strengths, "gaps": gaps}

    def translate_cv(
        self,
        cv_paragraphs: str,
        target_language: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> dict:
        selected_provider = provider or settings.default_llm_provider
        selected_model = model or settings.default_model_for(selected_provider)

        if not settings.is_provider_configured(selected_provider):
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} API key is not configured")

        target_label = "French" if target_language == "fr" else "English"
        system_prompt = (
            "You are a professional CV translator.\n"
            "Detect the main language of the CV (fr or en).\n"
            f"If the CV is already in {target_label}, return an empty translations object.\n"
            "Otherwise translate each line to "
            f"{target_label}.\n\n"
            "RULES:\n"
            "- Translate [TEXT] lines and standard section [HEADING] titles.\n"
            "- Do NOT translate: person names, company names, emails, URLs, phone numbers, "
            "dates, job titles at companies, city/country names when used as locations.\n"
            "- Keep one line per ID; never merge lines.\n"
            "- Preserve facts and metrics exactly.\n\n"
            "Respond ONLY with valid json:\n"
            '{"source_language": "fr", "translations": {"block_id": "translated text"}}'
        )
        user_prompt = (
            f"Target language: {target_label}\n\n"
            f"## CV Content\n{cv_paragraphs}\n\n"
            "Detect language and translate lines that need translation."
        )

        content = self._call_llm(
            provider=selected_provider,
            model=selected_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        return self._parse_translate_response(content, target_language)

    @staticmethod
    def _parse_translate_response(content: str, target_language: str) -> dict:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("LLM returned invalid JSON") from None
            data = json.loads(match.group())

        source_language = str(data.get("source_language", "")).lower()
        if source_language not in ("fr", "en"):
            source_language = "fr" if target_language == "en" else "en"

        raw_translations = data.get("translations", {})
        if not isinstance(raw_translations, dict):
            raw_translations = {}

        translations = {str(key): str(value) for key, value in raw_translations.items() if value}
        translated = source_language != target_language and len(translations) > 0
        if source_language == target_language:
            translations = {}
            translated = False

        return {
            "source_language": source_language,
            "target_language": target_language,
            "translations": translations,
            "translated": translated,
        }


llm_service = LLMService()
