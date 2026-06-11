function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (configured) {
    return configured.endsWith("/api") ? configured : `${configured}/api`;
  }
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api-backend`;
  }
  const backend = process.env.BACKEND_URL?.replace(/\/$/, "");
  if (backend) {
    return `${backend}/api`;
  }
  return "http://127.0.0.1:8001/api";
}

function apiUrl(path: string): string {
  return `${getApiBase()}/${path.replace(/^\//, "")}`;
}

function apiFetch(input: string, init?: RequestInit, timeoutMs = 120_000): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  return fetch(input, {
    credentials: "include",
    ...init,
    headers: init?.headers,
    signal: controller.signal,
  })
    .catch((err: unknown) => {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new Error(
          "Délai dépassé — le backend met trop de temps à répondre (Render gratuit : jusqu'à 1 min au 1er appel). Réessayez.",
        );
      }
      if (err instanceof TypeError) {
        throw new Error(
          "Connexion au backend impossible — vérifiez NEXT_PUBLIC_API_URL, CORS_ORIGINS sur Render, et que l'API est en ligne.",
        );
      }
      throw err;
    })
    .finally(() => {
      window.clearTimeout(timer);
    });
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null);
  if (payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  if (response.status === 404) {
    const onVercel =
      typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");
    if (onVercel && !process.env.NEXT_PUBLIC_API_URL) {
      return "Backend non relié : ajoutez NEXT_PUBLIC_API_URL et BACKEND_URL sur Vercel (URL Render), puis redéployez.";
    }
    return "API introuvable — vérifiez que le backend Render est en ligne et que NEXT_PUBLIC_API_URL est correct.";
  }
  if (response.status >= 500) {
    return fallback;
  }
  return fallback;
}

export interface PromptConfig {
  system_prompt: string;
  user_prompt: string;
}

export interface CVParagraph {
  id: string;
  text: string;
  style?: string | null;
  is_heading: boolean;
  modified?: boolean;
}

export interface CVPreviewResult {
  filename: string;
  paragraphs: CVParagraph[];
}

export interface MatchScoreResult {
  score: number;
  summary: string;
  strengths: string[];
  gaps: string[];
}

export interface JobAnalysisResult extends MatchScoreResult {
  present_keywords: string[];
  missing_keywords: string[];
  keyword_suggestions: string[];
}

export interface ApplyModificationsResult {
  download_url: string;
  download_url_pdf?: string | null;
  modifications_count: number;
  tailored_paragraphs: CVParagraph[];
}

export interface ApplicationKitResult {
  cover_letter: string;
  email_subject: string;
  recruiter_message: string;
  linkedin_message: string;
  application_tips: string[];
  checklist: string[];
  summary: string;
}

export type TailorIntensity = "light" | "strong" | "ats";

export interface TailorResult {
  job_id: string;
  original_filename: string;
  output_filename: string;
  download_url?: string | null;
  download_url_pdf?: string | null;
  modifications_count: number;
  summary: string;
  modified_paragraphs: Record<string, string>;
  original_paragraphs: CVParagraph[];
  tailored_paragraphs: CVParagraph[];
  llm_provider: string;
  llm_model: string;
  match_score?: number | null;
}

export interface LLMProviderInfo {
  id: string;
  name: string;
  models: string[];
  default_model: string;
  configured: boolean;
}

export interface LLMProvidersResponse {
  providers: LLMProviderInfo[];
  default_provider: string;
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await apiFetch(apiUrl("health"), undefined, 25_000);
    if (!response.ok) return false;
    const payload = await response.json();
    return payload?.status === "ok";
  } catch {
    return false;
  }
}

export async function fetchPrompts(): Promise<PromptConfig> {
  const response = await apiFetch(apiUrl("prompts"));
  if (!response.ok) {
    throw new Error("Failed to load prompts");
  }
  return response.json();
}

export async function savePrompts(config: PromptConfig): Promise<PromptConfig> {
  const response = await apiFetch(apiUrl("prompts"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error("Failed to save prompts");
  }
  return response.json();
}

export async function resetPrompts(): Promise<PromptConfig> {
  const response = await apiFetch(apiUrl("prompts/reset"), { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to reset prompts");
  }
  return response.json();
}

export async function fetchLLMProviders(): Promise<LLMProvidersResponse> {
  const response = await apiFetch(apiUrl("llm/providers"));
  if (!response.ok) {
    throw new Error("Failed to load LLM providers");
  }
  return response.json();
}

export async function generateApplicationKit(params: {
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  companyName?: string;
  jobTitle?: string;
  recruiterName?: string;
  tone?: "professional" | "friendly";
  paragraphs?: CVParagraph[];
}): Promise<ApplicationKitResult> {
  const response = await apiFetch(apiUrl("application/kit"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: params.jobDescription,
      output_language: params.outputLanguage,
      llm_provider: params.llmProvider,
      llm_model: params.llmModel,
      company_name: params.companyName,
      job_title: params.jobTitle,
      recruiter_name: params.recruiterName,
      tone: params.tone ?? "professional",
      paragraphs: params.paragraphs,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Application kit failed"));
  }

  return response.json();
}

export interface TranslateCVResult {
  paragraphs: CVParagraph[];
  source_language: "fr" | "en";
  target_language: "fr" | "en";
  translated: boolean;
}

export async function translateCV(params: {
  paragraphs: CVParagraph[];
  targetLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
}): Promise<TranslateCVResult> {
  const response = await apiFetch(apiUrl("translate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paragraphs: params.paragraphs,
      target_language: params.targetLanguage,
      llm_provider: params.llmProvider,
      llm_model: params.llmModel,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "CV translation failed"));
  }

  return response.json();
}

export async function analyzeJob(params: {
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  paragraphs?: CVParagraph[];
}): Promise<JobAnalysisResult> {
  const response = await apiFetch(apiUrl("analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: params.jobDescription,
      output_language: params.outputLanguage,
      llm_provider: params.llmProvider,
      llm_model: params.llmModel,
      paragraphs: params.paragraphs,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Analysis failed"));
  }

  return response.json();
}

export async function retryModifications(params: {
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  tailorIntensity: TailorIntensity;
  rejectedBlockIds: string[];
  keptModifications: Record<string, string>;
}): Promise<RetryModificationsResult> {
  const response = await apiFetch(apiUrl("tailor/retry"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: params.jobDescription,
      output_language: params.outputLanguage,
      llm_provider: params.llmProvider,
      llm_model: params.llmModel,
      tailor_intensity: params.tailorIntensity,
      rejected_block_ids: params.rejectedBlockIds,
      kept_modifications: params.keptModifications,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Retry failed"));
  }

  return response.json();
}

export async function applyModifications(
  modifications: Record<string, string>,
): Promise<ApplyModificationsResult> {
  const response = await apiFetch(apiUrl("tailor/apply"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modifications }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Apply modifications failed"));
  }

  return response.json();
}

export async function computeMatchScore(params: {
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  paragraphs?: CVParagraph[];
}): Promise<MatchScoreResult> {
  const response = await apiFetch(apiUrl("match"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: params.jobDescription,
      output_language: params.outputLanguage,
      llm_provider: params.llmProvider,
      llm_model: params.llmModel,
      paragraphs: params.paragraphs,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Match failed"));
  }

  return response.json();
}

export async function previewCV(file: File): Promise<CVPreviewResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(
    apiUrl("preview"),
    {
      method: "POST",
      body: formData,
    },
    120_000,
  );

  if (!response.ok) {
    throw new Error(await readApiError(response, "Preview failed"));
  }

  return response.json();
}

export interface CoverLetterExportResult {
  filename: string;
  download_url: string;
  download_url_pdf?: string | null;
}

export interface RetryModificationsResult {
  modified_paragraphs: Record<string, string>;
  tailored_paragraphs: CVParagraph[];
  summary: string;
  modifications_count: number;
}

export async function exportCoverLetterDocx(params: {
  coverLetter: string;
  companyName?: string;
  jobTitle?: string;
}): Promise<CoverLetterExportResult> {
  const response = await apiFetch(apiUrl("application/cover-letter/docx"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cover_letter: params.coverLetter,
      company_name: params.companyName,
      job_title: params.jobTitle,
    }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Cover letter export failed"));
  }

  return response.json();
}

export async function tailorCV(params: {
  file: File | null;
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  tailorIntensity?: TailorIntensity;
  customSystemPrompt?: string;
  customUserPrompt?: string;
}): Promise<TailorResult> {
  const formData = new FormData();
  if (params.file) {
    formData.append("file", params.file);
  }
  formData.append("job_description", params.jobDescription);
  formData.append("output_language", params.outputLanguage);
  formData.append("llm_provider", params.llmProvider);
  formData.append("llm_model", params.llmModel);
  formData.append("tailor_intensity", params.tailorIntensity ?? "strong");

  if (params.customSystemPrompt) {
    formData.append("custom_system_prompt", params.customSystemPrompt);
  }
  if (params.customUserPrompt) {
    formData.append("custom_user_prompt", params.customUserPrompt);
  }

  const response = await apiFetch(apiUrl("tailor"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Tailoring failed"));
  }

  return response.json();
}

export function getDownloadUrl(downloadPath: string): string {
  const relative = downloadPath.replace(/^\/api\//, "");
  return apiUrl(relative);
}
