"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { BackendConnectionBanner } from "@/components/BackendConnectionBanner";
import { ApplicationHistoryPanel } from "@/components/ApplicationHistoryPanel";
import { CVCompareView } from "@/components/CVCompareView";
import { FileUpload } from "@/components/FileUpload";
import { JobAnalysisPanel } from "@/components/JobAnalysisPanel";
import { LLMSelector } from "@/components/LLMSelector";
import { OutputLanguagePicker } from "@/components/OutputLanguagePicker";
import { StickyPrimaryAction } from "@/components/StickyPrimaryAction";
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
  toAnalysisGuidance,
  translateCV,
  type CVParagraph,
  type JobAnalysisResult,
  type PromptConfig,
  type TailorIntensity,
  type TailorResult,
} from "@/lib/api";
import { JOB_STORAGE_KEY } from "@/lib/constants";
import { saveAdaptedCv, saveHistoryEntry, savePreviewCv, updateHistoryEntry } from "@/lib/history";
import type { LLMProviderId } from "@/lib/types";

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
  const [baseParagraphs, setBaseParagraphs] = useState<CVParagraph[]>([]);
  const [originalParagraphs, setOriginalParagraphs] = useState<CVParagraph[]>([]);
  const [cvSourceLanguage, setCvSourceLanguage] = useState<"fr" | "en" | null>(null);
  const [translationLoading, setTranslationLoading] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [languageTouched, setLanguageTouched] = useState(false);
  const translationCacheRef = useRef<Partial<Record<"fr" | "en", CVParagraph[]>>>({});
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
    setBaseParagraphs(preview.paragraphs);
    setOriginalParagraphs(preview.paragraphs);
    setCvSourceLanguage(null);
    setLanguageTouched(true);
    setTranslationError(null);
    translationCacheRef.current = {};
    const fname = filename ?? preview.filename;
    setPreviewFilename(fname);
    if (preview.paragraphs.length > 0) {
      savePreviewCv(preview.paragraphs, fname || "cv.docx");
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

  const handleOutputLanguageChange = useCallback((lang: "fr" | "en") => {
    setLanguageTouched(true);
    setOutputLanguage(lang);
    setResult(null);
    setExportUrls(null);
    setAnalysis(null);
    setAnalysisError(null);
    setScoreBefore(null);
    setScoreAfter(null);
  }, []);

  useEffect(() => {
    if (!languageTouched || baseParagraphs.length === 0) return;

    if (cvSourceLanguage === outputLanguage) {
      setOriginalParagraphs(baseParagraphs);
      return;
    }

    const cached = translationCacheRef.current[outputLanguage];
    if (cached) {
      setOriginalParagraphs(cached);
      return;
    }

    let cancelled = false;
    setTranslationLoading(true);
    setTranslationError(null);

    translateCV({
      paragraphs: baseParagraphs,
      targetLanguage: outputLanguage,
      llmProvider,
      llmModel,
    })
      .then((data) => {
        if (cancelled) return;
        setCvSourceLanguage(data.source_language);
        translationCacheRef.current[data.source_language] = baseParagraphs;
        if (data.translated) {
          translationCacheRef.current[data.target_language] = data.paragraphs;
          setOriginalParagraphs(data.paragraphs);
        } else {
          setOriginalParagraphs(baseParagraphs);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setTranslationError(err instanceof Error ? err.message : t("error"));
        setOriginalParagraphs(baseParagraphs);
      })
      .finally(() => {
        if (!cancelled) setTranslationLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [languageTouched, outputLanguage, baseParagraphs, cvSourceLanguage, llmProvider, llmModel, t]);

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

  useEffect(() => {
    if (!displayTailoredParagraphs?.length) return;
    saveAdaptedCv(
      displayTailoredParagraphs,
      previewFilename || file?.name || "cv.docx",
    );
  }, [displayTailoredParagraphs, previewFilename, file]);

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
        updateHistoryEntry(result.job_id, { scoreAfter: after.score });
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
      setBaseParagraphs([]);
      setOriginalParagraphs([]);
      setCvSourceLanguage(null);
      setLanguageTouched(false);
      translationCacheRef.current = {};
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
      let guidance = analysis;
      if (!guidance) {
        try {
          guidance = await analyzeJob({
            jobDescription,
            outputLanguage,
            llmProvider,
            llmModel,
            paragraphs: originalParagraphs,
          });
          setAnalysis(guidance);
          setScoreBefore(guidance.score);
        } catch {
          /* tailor without prior analysis */
        }
      }

      const response = await tailorCV({
        file,
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        tailorIntensity,
        customSystemPrompt: prompts.system_prompt,
        customUserPrompt: prompts.user_prompt,
        analysisGuidance: guidance ? toAnalysisGuidance(guidance) : undefined,
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
  const canSubmit =
    hasCv && jobDescription.trim().length >= 20 && !loading && !translationLoading && hasLlmConfigured;
  const canAnalyze =
    hasCv && jobDescription.trim().length >= 20 && hasLlmConfigured && !analysisLoading && !translationLoading;
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
        <div className="card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">{t("jobTitle")}</h2>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder={t("jobPlaceholder")}
            rows={8}
            className="input-field"
          />
          <p
            className={`mt-1 text-right text-xs ${
              jobDescription.trim().length >= 20 ? "text-slate-500" : "text-amber-600"
            }`}
          >
            {jobDescription.length} {t("jobCharCount")}
          </p>
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
                  className={`flex min-h-[44px] cursor-pointer flex-col rounded-lg border px-3 py-2.5 text-sm transition sm:min-h-0 ${
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
            <OutputLanguagePicker
              value={outputLanguage}
              onChange={handleOutputLanguageChange}
              loading={translationLoading}
              error={translationError}
            />
          </div>

          <LLMSelector
            hidden
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

        <StickyPrimaryAction>
          <button
            type="button"
            onClick={handleTailor}
            disabled={!canSubmit}
            className="btn-primary w-full py-3.5 text-base sm:mx-auto sm:block sm:w-auto sm:max-w-md sm:px-8"
          >
            {loading ? t("processing") : t("tailorBtn")}
          </button>
        </StickyPrimaryAction>

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
              analysisGuidance={analysis ? toAnalysisGuidance(analysis) : null}
              onAcceptedChange={handleAcceptedChange}
              onExportReady={handleExportReady}
              onModificationsUpdate={handleModificationsUpdate}
            />
          </div>
        )}

        <div id="cv-compare-section">
          {result && !previewLoading && (
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
