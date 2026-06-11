"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { CVCompareView } from "@/components/CVCompareView";
import { FileUpload } from "@/components/FileUpload";
import { LLMSelector, type LLMProviderId } from "@/components/LLMSelector";
import { MatchScorePanel } from "@/components/MatchScorePanel";
import { PromptEditor } from "@/components/PromptEditor";
import { ResultPanel } from "@/components/ResultPanel";
import { useI18n } from "@/i18n/context";
import {
  computeMatchScore,
  fetchLastCVFile,
  fetchPrompts,
  previewCV,
  tailorCV,
  type CVParagraph,
  type MatchScoreResult,
  type PromptConfig,
  type TailorResult,
} from "@/lib/api";

const JOB_STORAGE_KEY = "cv-tailor-job-description";

export default function HomePage() {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [outputLanguage, setOutputLanguage] = useState<"fr" | "en">("fr");
  const [llmProvider, setLlmProvider] = useState<LLMProviderId>("groq");
  const [llmModel, setLlmModel] = useState("llama-3.3-70b-versatile");
  const [prompts, setPrompts] = useState<PromptConfig>({
    system_prompt: "",
    user_prompt: "",
  });
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [originalParagraphs, setOriginalParagraphs] = useState<CVParagraph[]>([]);
  const [previewFilename, setPreviewFilename] = useState<string>("");
  const [hasLlmConfigured, setHasLlmConfigured] = useState(true);
  const [cvRestored, setCvRestored] = useState(false);
  const [matchScore, setMatchScore] = useState<MatchScoreResult | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  useEffect(() => {
    fetchPrompts()
      .then(setPrompts)
      .catch(() => setError(t("error")));
  }, [t]);

  useEffect(() => {
    const saved = sessionStorage.getItem(JOB_STORAGE_KEY);
    if (saved) {
      setJobDescription(saved);
    }
  }, []);

  useEffect(() => {
    if (jobDescription.trim()) {
      sessionStorage.setItem(JOB_STORAGE_KEY, jobDescription);
    }
  }, [jobDescription]);

  const loadCvPreview = useCallback(
    async (selected: File, filename?: string) => {
      const preview = await previewCV(selected);
      setOriginalParagraphs(preview.paragraphs);
      setPreviewFilename(filename ?? preview.filename);
      if (preview.paragraphs.length > 0) {
        setTimeout(() => {
          document.getElementById("cv-compare-section")?.scrollIntoView({ behavior: "smooth" });
        }, 200);
      }
      return preview;
    },
    [],
  );

  const restoreLastCV = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const restoredFile = await fetchLastCVFile();
      setFile(restoredFile);
      await loadCvPreview(restoredFile, restoredFile.name);
      setCvRestored(true);
    } catch (err) {
      setCvRestored(false);
      const message = err instanceof Error ? err.message : t("error");
      if (!message.toLowerCase().includes("no cv")) {
        setError(message);
      }
    } finally {
      setPreviewLoading(false);
    }
  }, [loadCvPreview, t]);

  useEffect(() => {
    restoreLastCV();
  }, [restoreLastCV]);

  useEffect(() => {
    if (!hasLlmConfigured || originalParagraphs.length === 0 || jobDescription.trim().length < 20) {
      setMatchScore(null);
      setMatchError(null);
      return;
    }

    const timer = setTimeout(async () => {
      setMatchLoading(true);
      setMatchError(null);
      try {
        const score = await computeMatchScore({
          jobDescription,
          outputLanguage,
          llmProvider,
          llmModel,
          paragraphs: originalParagraphs,
        });
        setMatchScore(score);
      } catch (err) {
        setMatchScore(null);
        setMatchError(err instanceof Error ? err.message : t("error"));
      } finally {
        setMatchLoading(false);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [
    jobDescription,
    originalParagraphs,
    outputLanguage,
    llmProvider,
    llmModel,
    hasLlmConfigured,
    t,
  ]);

  const handleFileSelect = async (selected: File | null) => {
    setFile(selected);
    setResult(null);
    setMatchScore(null);
    setCvRestored(false);

    if (!selected) {
      setOriginalParagraphs([]);
      setPreviewFilename("");
      return;
    }

    setPreviewLoading(true);
    setError(null);

    try {
      await loadCvPreview(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
      setOriginalParagraphs([]);
      setPreviewFilename("");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleTailor = async () => {
    if ((!file && originalParagraphs.length === 0) || jobDescription.trim().length < 20) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await tailorCV({
        file,
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        customSystemPrompt: prompts.system_prompt,
        customUserPrompt: prompts.user_prompt,
      });
      setResult(response);
      if (response.match_score != null) {
        setMatchScore((current) =>
          current?.score === response.match_score
            ? current
            : {
                score: response.match_score!,
                summary: response.summary,
                strengths: current?.strengths ?? [],
                gaps: current?.gaps ?? [],
              },
        );
      }

      setTimeout(() => {
        document.getElementById("cv-compare-section")?.scrollIntoView({ behavior: "smooth" });
      }, 200);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  };

  const hasCv = Boolean(file) || originalParagraphs.length > 0;
  const canSubmit = hasCv && jobDescription.trim().length >= 20 && !loading && hasLlmConfigured;
  const compareOriginal = result?.original_paragraphs ?? originalParagraphs;

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-slate-100">
      <AppHeader active="cv" />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <FileUpload file={file} restored={cvRestored} onFileSelect={handleFileSelect} />

        <div className="card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">{t("jobTitle")}</h2>
          <textarea
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder={t("jobPlaceholder")}
            rows={8}
            className="input-field"
          />

          <div className="mt-4">
            <MatchScorePanel
              match={matchScore}
              loading={matchLoading}
              waitingForCv={originalParagraphs.length === 0}
              waitingForJob={originalParagraphs.length > 0 && jobDescription.trim().length < 20}
              error={matchError}
            />
          </div>

          <div className="mt-4">
            <label className="label">{t("outputLang")}</label>
            <div className="flex gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="outputLang"
                  checked={outputLanguage === "fr"}
                  onChange={() => setOutputLanguage("fr")}
                  className="text-brand-600"
                />
                {t("french")}
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="outputLang"
                  checked={outputLanguage === "en"}
                  onChange={() => setOutputLanguage("en")}
                  className="text-brand-600"
                />
                {t("english")}
              </label>
            </div>
          </div>

          <LLMSelector
            hidden
            provider={llmProvider}
            model={llmModel}
            onChange={(nextProvider, nextModel) => {
              setLlmProvider(nextProvider);
              setLlmModel(nextModel);
            }}
            onConfiguredChange={setHasLlmConfigured}
          />

          {!hasLlmConfigured && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t("noLlmConfigured")}
            </p>
          )}
        </div>

        <PromptEditor
          systemPrompt={prompts.system_prompt}
          userPrompt={prompts.user_prompt}
          onChange={setPrompts}
          defaultOpen={false}
        />

        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleTailor}
            disabled={!canSubmit}
            className="btn-primary px-8 py-3 text-base"
          >
            {loading ? t("processing") : t("tailorBtn")}
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <ResultPanel result={result} matchScore={matchScore?.score ?? result?.match_score} />

        <div id="cv-compare-section">
          {hasCv && !previewLoading && (
            <CVCompareView
              hidden
              originalParagraphs={compareOriginal}
              tailoredParagraphs={result?.tailored_paragraphs ?? null}
              filename={previewFilename || file?.name}
              downloadUrl={result?.download_url}
              downloadUrlPdf={result?.download_url_pdf}
              modificationsCount={result?.modifications_count}
              summary={result?.summary}
            />
          )}
        </div>
      </main>
    </div>
  );
}
