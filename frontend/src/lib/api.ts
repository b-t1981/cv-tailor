function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (configured) {
    return configured.endsWith("/api") ? configured : `${configured}/api`;
  }
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api-backend`;
  }
  return "http://127.0.0.1:8001/api";
}

function apiUrl(path: string): string {
  return `${getApiBase()}/${path.replace(/^\//, "")}`;
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null);
  if (payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  if (response.status === 404) {
    return "API introuvable — vérifiez que le backend est démarré (port 8001).";
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

export interface StoredCVResult {
  filename: string;
  paragraphs: CVParagraph[];
  saved_at?: string | null;
}

export interface MatchScoreResult {
  score: number;
  summary: string;
  strengths: string[];
  gaps: string[];
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

export interface TailorResult {
  job_id: string;
  original_filename: string;
  output_filename: string;
  download_url: string;
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

export async function fetchPrompts(): Promise<PromptConfig> {
  const response = await fetch(apiUrl("prompts"));
  if (!response.ok) {
    throw new Error("Failed to load prompts");
  }
  return response.json();
}

export async function savePrompts(config: PromptConfig): Promise<PromptConfig> {
  const response = await fetch(apiUrl("prompts"), {
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
  const response = await fetch(apiUrl("prompts/reset"), { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to reset prompts");
  }
  return response.json();
}

export async function fetchLLMProviders(): Promise<LLMProvidersResponse> {
  const response = await fetch(apiUrl("llm/providers"));
  if (!response.ok) {
    throw new Error("Failed to load LLM providers");
  }
  return response.json();
}

export async function fetchLastCV(): Promise<StoredCVResult> {
  const response = await fetch(apiUrl("cv/last"));
  if (!response.ok) {
    throw new Error("No CV in memory");
  }
  return response.json();
}

export async function fetchLastCVFile(): Promise<File> {
  const response = await fetch(apiUrl("cv/last/file"));
  if (!response.ok) {
    throw new Error("No CV file in memory");
  }
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] ?? "last_cv.docx";
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || "application/octet-stream" });
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
  const response = await fetch(apiUrl("application/kit"), {
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

export async function computeMatchScore(params: {
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
  paragraphs?: CVParagraph[];
}): Promise<MatchScoreResult> {
  const response = await fetch(apiUrl("match"), {
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

  const response = await fetch(apiUrl("preview"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readApiError(response, "Preview failed"));
  }

  return response.json();
}

export async function tailorCV(params: {
  file: File | null;
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: "openai" | "groq" | "claude";
  llmModel: string;
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

  if (params.customSystemPrompt) {
    formData.append("custom_system_prompt", params.customSystemPrompt);
  }
  if (params.customUserPrompt) {
    formData.append("custom_user_prompt", params.customUserPrompt);
  }

  const response = await fetch(apiUrl("tailor"), {
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
