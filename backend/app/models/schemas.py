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


class JobAnalysisRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    paragraphs: list[ParagraphInfo] | None = None


class JobAnalysisResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    summary: str
    strengths: list[str]
    gaps: list[str]
    present_keywords: list[str]
    missing_keywords: list[str]
    keyword_suggestions: list[str] = Field(default_factory=list)
    writing_score: int = Field(default=0, ge=0, le=100)
    writing_summary: str = ""
    writing_strengths: list[str] = Field(default_factory=list)
    writing_improvements: list[str] = Field(default_factory=list)
    profile_confidence: str = Field(default="moderate", pattern="^(high|moderate|low)$")
    cv_confidence: str = Field(default="moderate", pattern="^(high|moderate|low)$")
    confidence_reason: str = ""
    role_content_ratio: int = Field(default=50, ge=0, le=100)


class ApplyModificationsRequest(BaseModel):
    modifications: dict[str, str] = Field(..., min_length=1)


class ApplyModificationsResponse(BaseModel):
    download_url: str
    download_url_pdf: str | None = None
    modifications_count: int
    tailored_paragraphs: list[ParagraphInfo]


class AnalysisGuidance(BaseModel):
    """Recommendations from /api/analyze to apply during tailoring."""

    writing_improvements: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    keyword_suggestions: list[str] = Field(default_factory=list)

    def has_content(self) -> bool:
        return bool(
            self.writing_improvements
            or self.gaps
            or self.missing_keywords
            or self.keyword_suggestions
        )


class TailorRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    tailor_intensity: str = Field(default="strong", pattern="^(light|strong|ats)$")
    custom_system_prompt: str | None = None
    custom_user_prompt: str | None = None
    analysis_guidance: AnalysisGuidance | None = None


class CoverLetterExportRequest(BaseModel):
    cover_letter: str = Field(..., min_length=50)
    company_name: str | None = None
    job_title: str | None = None


class CoverLetterExportResponse(BaseModel):
    filename: str
    download_url: str
    download_url_pdf: str | None = None


class LLMProviderInfo(BaseModel):
    id: str
    name: str
    models: list[str]
    default_model: str
    configured: bool


class LLMProvidersResponse(BaseModel):
    providers: list[LLMProviderInfo]
    default_provider: str


class RetryModificationsRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    output_language: str = Field(default="fr", pattern="^(fr|en)$")
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None
    tailor_intensity: str = Field(default="strong", pattern="^(light|strong|ats)$")
    rejected_block_ids: list[str] = Field(..., min_length=1)
    kept_modifications: dict[str, str] = Field(default_factory=dict)
    analysis_guidance: AnalysisGuidance | None = None


class RetryModificationsResponse(BaseModel):
    modified_paragraphs: dict[str, str]
    tailored_paragraphs: list[ParagraphInfo]
    summary: str
    modifications_count: int


class TailorResponse(BaseModel):
    job_id: str
    original_filename: str
    output_filename: str = ""
    download_url: str | None = None
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


class TranslateCVRequest(BaseModel):
    paragraphs: list[ParagraphInfo] = Field(..., min_length=1)
    target_language: str = Field(..., pattern="^(fr|en)$")
    llm_provider: str = Field(default="openai", pattern="^(openai|groq|claude)$")
    llm_model: str | None = None


class TranslateCVResponse(BaseModel):
    paragraphs: list[ParagraphInfo]
    source_language: str
    target_language: str
    translated: bool


class HealthResponse(BaseModel):
    status: str
    default_provider: str
    default_model: str
    prompts_loaded: bool
    providers: list[LLMProviderInfo]
    cerebras_fallback_enabled: bool = False
    groq_in_cooldown: bool = False
    libreoffice_available: bool = False
    pdf_prefer_libreoffice: bool = False
