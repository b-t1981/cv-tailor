"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { BackendConnectionBanner } from "@/components/BackendConnectionBanner";
import { ApplicationHistoryPanel } from "@/components/ApplicationHistoryPanel";
import { CVCompareView } from "@/components/CVCompareView";
import { FileUpload } from "@/components/FileUpload";
import { JobAnalysisPanel } from "@/components/JobAnalysisPanel";
import { LLMSelector, type LLMProviderId } from "@/components/LLMSelector";
import { ModificationReviewPanel } from "@/components/ModificationReviewPanel";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { PromptEditor } from "@/components/PromptEditor";
import { ResultPanel } from "@/components/ResultPanel";
import { useI18n } from "@/i18n/context";
import {
  analyzeJob,
  fetchPrompts,
  previewCV,
  tailorCV,
  type CVParagraph,
  type JobAnalysisResult,
  type PromptConfig,
  type TailorIntensity,
  type TailorResult,
} from "@/lib/api";
import { saveAdaptedCv, saveHistoryEntry } from "@/lib/history";

const JOB_STORAGE_KEY = "cv-tailor-job-description";

export default function HomePage() {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [outputLanguage, setOutputLanguage] = useState<"fr" | "en">("fr");
  const [llmProvider, setLlmProvider] = useState<LLMProviderId>("groq");
  const [llmModel, setLlmModel] = useState("llama-3.3-70b-versatile");
  const [prompts, setPrompts] = useState<PromptConfig>({ system_prompt: "", user_prompt: "" });
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [originalParagraphs, setOriginalParagraphs] = useState<CVParagraph[]>([]);
  const [previewFilename, setPreviewFilename] = useState<string>("");
  const [hasLlmConfigured, setHasLlmConfigured] = useState(true);
  const [analysis, setAnalysis] = useState<JobAnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [tailorIntensity, setTailorIntensity] = useState<TailorIntensity>("strong");
  const [acceptedModifications, setAcceptedModifications] = useState<Record<string, string>>({});
  const [exportUrls, setExportUrls] = useState<{
    downloadUrl: string;
    downloadUrlPdf?: string | null;
  } | null>(null);
  const [scoreBefore, setScoreBefore] = useState<number | null>(null);
  const [scoreAfter, setScoreAfter] = useState<number | null>(null);
  const [showAdvancedLlm, setShowAdvancedLlm] = useState(false);
  const [invalidFileError, setInvalidFileError] = useState<string | null>(null);
  const [previewSlowHint, setPreviewSlowHint] = useState(false);

  useEffect(() => {
    fetchPrompts().then(setPrompts).catch(() => setError(t("error")));
  }, [t]);

  useEffect(() => {
    if (!previewLoading) {
      setPreviewSlowHint(false);
      return;
    }
    const timer = window.setTimeout(() => setPreviewSlowHint(true), 8_000);
    return () => window.clearTimeout(timer);
  }, [previewLoading]);

  useEffect(() => {
    const saved = sessionStorage.getItem(JOB_STORAGE_KEY);
    if (saved) setJobDescription(saved);
  }, []);

  useEffect(() => {
    if (jobDescription.trim()) sessionStorage.setItem(JOB_STORAGE_KEY, jobDescription);
  }, [jobDescription]);

  useEffect(() => {
    setAnalysis(null);
    setAnalysisError(null);
    setScoreBefore(null);
    setScoreAfter(null);
  }, [jobDescription, originalParagraphs]);

  useEffect(() => {
    if (result?.modified_paragraphs) {
      setAcceptedModifications(result.modified_paragraphs);
      setExportUrls(null);
    }
  }, [result]);

  const loadCvPreview = useCallback(async (selected: File, filename?: string) => {
    const preview = await previewCV(selected);
    setOriginalParagraphs(preview.paragraphs);
    setPreviewFilename(filename ?? preview.filename);
    if (preview.paragraphs.length > 0) {
      setTimeout(() => {
        document.getElementById("cv-compare-section")?.scrollIntoView({ behavior: "smooth" });
      }, 200);
    }
    return preview;
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (originalParagraphs.length === 0 || jobDescription.trim().length < 20) return;
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const data = await analyzeJob({
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        paragraphs: originalParagraphs,
      });
      setAnalysis(data);
      setScoreBefore(data.score);
      setScoreAfter(null);
    } catch (err) {
      setAnalysis(null);
      setAnalysisError(err instanceof Error ? err.message : t("error"));
    } finally {
      setAnalysisLoading(false);
    }
  }, [jobDescription, outputLanguage, llmProvider, llmModel, originalParagraphs, t]);

  useEffect(() => {
    if (
      previewLoading ||
      originalParagraphs.length === 0 ||
      jobDescription.trim().length < 20 ||
      !hasLlmConfigured
    ) {
      return;
    }
    const timer = window.setTimeout(() => {
      void handleAnalyze();
    }, 700);
    return () => window.clearTimeout(timer);
  }, [
    jobDescription,
    originalParagraphs,
    hasLlmConfigured,
    previewLoading,
    handleAnalyze,
  ]);

  const handleAcceptedChange = useCallback((accepted: Record<string, string>) => {
    setAcceptedModifications(accepted);
    setExportUrls(null);
  }, []);

  const displayTailoredParagraphs = useMemo(() => {
    if (!result) return null;
    return result.original_paragraphs.map((paragraph) => {
      const newText = acceptedModifications[paragraph.id];
      if (newText) return { ...paragraph, text: newText, modified: true };
      return paragraph;
    });
  }, [result, acceptedModifications]);

  const handleExportReady = useCallback(
    async (urls: { downloadUrl: string; downloadUrlPdf?: string | null }) => {
      setExportUrls(urls);
      if (!result || !displayTailoredParagraphs) return;

      const fname = previewFilename || file?.name || "cv.docx";
      saveAdaptedCv(displayTailoredParagraphs, fname);
      saveHistoryEntry({
        id: result.job_id,
        date: new Date().toISOString(),
        jobTitleSnippet: jobDescription.slice(0, 60) + (jobDescription.length > 60 ? "…" : ""),
        scoreBefore,
        scoreAfter: null,
        modificationsCount: Object.keys(acceptedModifications).length,
        downloadUrl: urls.downloadUrl,
        tailoredParagraphs: displayTailoredParagraphs,
      });

      try {
        const after = await analyzeJob({
          jobDescription,
          outputLanguage,
          llmProvider,
          llmModel,
          paragraphs: displayTailoredParagraphs,
        });
        setScoreAfter(after.score);
        setAnalysis(after);
      } catch {
        /* optional */
      }
    },
    [
      result,
      displayTailoredParagraphs,
      previewFilename,
      file,
      jobDescription,
      scoreBefore,
      acceptedModifications,
      outputLanguage,
      llmProvider,
      llmModel,
    ],
  );

  const handleModificationsUpdate = useCallback(
    (mods: Record<string, string>, tailored: CVParagraph[]) => {
      setResult((current) =>
        current
          ? {
              ...current,
              modified_paragraphs: mods,
              tailored_paragraphs: tailored,
              modifications_count: Object.keys(mods).length,
            }
          : current,
      );
      setAcceptedModifications(mods);
      setExportUrls(null);
    },
    [],
  );

  const handleFileSelect = async (selected: File | null) => {
    setFile(selected);
    setResult(null);
    setAnalysis(null);
    setInvalidFileError(null);
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
    if (!file || jobDescription.trim().length < 20) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setExportUrls(null);
    try {
      const response = await tailorCV({
        file,
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        tailorIntensity,
        customSystemPrompt: prompts.system_prompt,
        customUserPrompt: prompts.user_prompt,
      });
      setResult(response);
      setTimeout(() => {
        document.getElementById("modification-review")?.scrollIntoView({ behavior: "smooth" });
      }, 200);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  };

  const hasCv = Boolean(file) && originalParagraphs.length > 0;
  const canSubmit = hasCv && jobDescription.trim().length >= 20 && !loading && hasLlmConfigured;
  const canAnalyze = hasCv && jobDescription.trim().length >= 20 && hasLlmConfigured && !analysisLoading;
  const compareOriginal = result?.original_paragraphs ?? originalParagraphs;
  const acceptedCount = Object.keys(acceptedModifications).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-slate-100">
      <AppHeader active="cv" />
      <main className="page-main">
        <BackendConnectionBanner />
        <PrivacyNotice />
        <FileUpload
          file={file}
          onFileSelect={handleFileSelect}
          onInvalidFile={() => setInvalidFileError(t("uploadInvalidType"))}
        />
        {invalidFileError && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {invalidFileError}
          </div>
        )}
        {previewLoading && (
          <div className="card space-y-2 text-center text-sm text-slate-500">
            <p className="flex items-center justify-center gap-2">
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"
                aria-hidden
              />
              {t("previewLoading")}
            </p>
            {previewSlowHint && (
              <p className="text-xs text-amber-700">{t("previewLoadingSlow")}</p>
            )}
          </div>
        )}
        {error && previewLoading === false && file && originalParagraphs.length === 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">{t("jobTitle")}</h2>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder={t("jobPlaceholder")}
            rows={8}
            className="input-field"
          />
          <div className="mt-4">
            <JobAnalysisPanel
              analysis={analysis}
              loading={analysisLoading}
              canAnalyze={canAnalyze}
              waitingForCv={originalParagraphs.length === 0}
              waitingForJob={originalParagraphs.length > 0 && jobDescription.trim().length < 20}
              error={analysisError}
              scoreBefore={scoreBefore}
              scoreAfter={scoreAfter}
              onAnalyze={handleAnalyze}
            />
          </div>

          <div className="mt-4">
            <label className="label">{t("tailorIntensity")}</label>
            <div className="grid gap-2 sm:grid-cols-3">
              {(["light", "strong", "ats"] as const).map((mode) => (
                <label
                  key={mode}
                  className={`flex cursor-pointer flex-col rounded-lg border px-3 py-2.5 text-sm transition ${
                    tailorIntensity === mode
                      ? "border-brand-500 bg-brand-50"
                      : "border-slate-300 hover:border-brand-300"
                  }`}
                >
                  <span className="flex items-center gap-2 font-medium text-slate-800">
                    <input
                      type="radio"
                      name="tailorIntensity"
                      checked={tailorIntensity === mode}
                      onChange={() => setTailorIntensity(mode)}
                      className="text-brand-600"
                    />
                    {t(
                      mode === "light"
                        ? "tailorIntensityLight"
                        : mode === "ats"
                          ? "tailorIntensityAts"
                          : "tailorIntensityStrong",
                    )}
                  </span>
                  <span className="mt-1 pl-6 text-xs text-slate-500">
                    {t(
                      mode === "light"
                        ? "tailorIntensityLightHint"
                        : mode === "ats"
                          ? "tailorIntensityAtsHint"
                          : "tailorIntensityStrongHint",
                    )}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <label className="label">{t("outputLang")}</label>
            <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
              <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
                <input type="radio" checked={outputLanguage === "fr"} onChange={() => setOutputLanguage("fr")} className="text-brand-600" />
                {t("french")}
              </label>
              <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
                <input type="radio" checked={outputLanguage === "en"} onChange={() => setOutputLanguage("en")} className="text-brand-600" />
                {t("english")}
              </label>
            </div>
          </div>

          <div className="mt-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={showAdvancedLlm} onChange={(e) => setShowAdvancedLlm(e.target.checked)} />
              {t("advancedLlm")}
            </label>
          </div>
          <LLMSelector
            hidden={!showAdvancedLlm}
            provider={llmProvider}
            model={llmModel}
            onChange={(p, m) => {
              setLlmProvider(p);
              setLlmModel(m);
            }}
            onConfiguredChange={setHasLlmConfigured}
          />
          {!hasLlmConfigured && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t("noLlmConfigured")}
            </p>
          )}
        </div>

        <PromptEditor systemPrompt={prompts.system_prompt} userPrompt={prompts.user_prompt} onChange={setPrompts} defaultOpen={false} />

        <div
          className={
            result
              ? "flex justify-center"
              : "sticky bottom-0 z-40 -mx-3 border-t border-slate-200/80 bg-gradient-to-t from-slate-100 via-slate-100/95 to-transparent px-3 py-3 safe-bottom sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0"
          }
        >
          <button
            type="button"
            onClick={handleTailor}
            disabled={!canSubmit}
            className="btn-primary w-full py-3.5 text-base sm:mx-auto sm:block sm:w-auto sm:max-w-md sm:px-8"
          >
            {loading ? t("processing") : t("tailorBtn")}
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <ResultPanel result={result} acceptedCount={result ? acceptedCount : undefined} />

        {result && (
          <div id="modification-review">
            <ModificationReviewPanel
              originalParagraphs={compareOriginal}
              proposedModifications={result.modified_paragraphs}
              jobDescription={jobDescription}
              outputLanguage={outputLanguage}
              llmProvider={llmProvider}
              llmModel={llmModel}
              tailorIntensity={tailorIntensity}
              onAcceptedChange={handleAcceptedChange}
              onExportReady={handleExportReady}
              onModificationsUpdate={handleModificationsUpdate}
            />
          </div>
        )}

        <div id="cv-compare-section">
          {hasCv && !previewLoading && (
            <CVCompareView
              originalParagraphs={compareOriginal}
              tailoredParagraphs={displayTailoredParagraphs}
              filename={previewFilename || file?.name}
              downloadUrl={exportUrls?.downloadUrl ?? null}
              downloadUrlPdf={exportUrls?.downloadUrlPdf ?? null}
              modificationsCount={acceptedCount}
              summary={result?.summary}
            />
          )}
        </div>

        <ApplicationHistoryPanel />
      </main>
    </div>
  );
}
