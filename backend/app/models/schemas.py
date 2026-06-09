from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    system_prompt: str
    user_prompt: str


class PromptUpdateRequest(BaseModel):
    system_prompt: str = Field(..., min_length=10)
    user_prompt: str = Field(..., min_length=10)


class ParagraphInfo(BaseModel):
    id: str
    text: str
    style: str | None = None
    is_heading: bool = False
    modified: bool = False


class CVPreviewResponse(BaseModel):
    filename: str
    paragraphs: list[ParagraphInfo]
    restored: bool = False


class StoredCVResponse(BaseModel):
    filename: str
    paragraphs: list[ParagraphInfo]
    saved_at: str | None = None


class MatchScoreRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    paragraphs: list[ParagraphInfo] | None = None


class MatchScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    summary: str
    strengths: list[str]
    gaps: list[str]


class TailorRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    custom_system_prompt: str | None = None
    custom_user_prompt: str | None = None


class LLMProviderInfo(BaseModel):
    id: str
    name: str
    models: list[str]
    default_model: str
    configured: bool


class LLMProvidersResponse(BaseModel):
    providers: list[LLMProviderInfo]
    default_provider: str


class TailorResponse(BaseModel):
    job_id: str
    original_filename: str
    output_filename: str
    download_url: str
    download_url_pdf: str | None = None
    modifications_count: int
    summary: str
    modified_paragraphs: dict[str, str]
    original_paragraphs: list[ParagraphInfo]
    tailored_paragraphs: list[ParagraphInfo]
    llm_provider: str
    llm_model: str
    match_score: int | None = None


class ApplicationKitRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    company_name: str | None = None
    job_title: str | None = None
    recruiter_name: str | None = None
    tone: str = Field(default="professional", pattern="^(professional|friendly)$")
    paragraphs: list[ParagraphInfo] | None = None


class ApplicationKitResponse(BaseModel):
    cover_letter: str
    email_subject: str
    recruiter_message: str
    linkedin_message: str
    application_tips: list[str]
    checklist: list[str]
    summary: str


class HealthResponse(BaseModel):
    status: str
    default_provider: str
    default_model: str
    prompts_loaded: bool
    providers: list[LLMProviderInfo]
