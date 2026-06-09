import json
import re
from typing import Literal

from anthropic import Anthropic, AuthenticationError as AnthropicAuthError
from openai import APIStatusError, AuthenticationError, OpenAI

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
    "claude": "Claude (Anthropic)",
}


class LLMService:
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

        try:
            if selected_provider == "claude":
                content = self._call_claude(system_prompt, user_prompt, selected_model)
            else:
                content = self._call_openai_compatible(
                    provider=selected_provider,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=selected_model,
                )
        except (AuthenticationError, AnthropicAuthError, APIStatusError) as exc:
            if getattr(exc, "status_code", None) == 401 or "invalid" in str(exc).lower():
                raise ValueError(
                    f"{PROVIDER_LABELS[selected_provider]} API key is invalid. "
                    f"Check {selected_provider.upper()}_API_KEY in backend/.env"
                ) from exc
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} request failed: {exc}") from exc

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

        try:
            if selected_provider == "claude":
                content = self._call_claude(system_prompt, user_prompt, selected_model)
            else:
                content = self._call_openai_compatible(
                    provider=selected_provider,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=selected_model,
                )
        except (AuthenticationError, AnthropicAuthError, APIStatusError) as exc:
            if getattr(exc, "status_code", None) == 401 or "invalid" in str(exc).lower():
                raise ValueError(
                    f"{PROVIDER_LABELS[selected_provider]} API key is invalid. "
                    f"Check {selected_provider.upper()}_API_KEY in backend/.env"
                ) from exc
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} request failed: {exc}") from exc

        return self._parse_match_response(content)

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

        try:
            if selected_provider == "claude":
                content = self._call_claude(system_prompt, user_prompt, selected_model, temperature=0.4)
            else:
                content = self._call_openai_compatible(
                    provider=selected_provider,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=selected_model,
                    temperature=0.4,
                )
        except (AuthenticationError, AnthropicAuthError, APIStatusError) as exc:
            if getattr(exc, "status_code", None) == 401 or "invalid" in str(exc).lower():
                raise ValueError(
                    f"{PROVIDER_LABELS[selected_provider]} API key is invalid. "
                    f"Check {selected_provider.upper()}_API_KEY in backend/.env"
                ) from exc
            raise ValueError(f"{PROVIDER_LABELS[selected_provider]} request failed: {exc}") from exc

        return self._parse_application_kit(content)

    def _call_openai_compatible(
        self,
        provider: Literal["openai", "groq"],
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.1,
    ) -> str:
        if provider == "openai":
            client = OpenAI(api_key=settings.openai_api_key)
        else:
            client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )

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


llm_service = LLMService()
