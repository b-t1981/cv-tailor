"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { BackendConnectionBanner } from "@/components/BackendConnectionBanner";
import { CopyButton } from "@/components/CopyButton";
import { LLMSelector, type LLMProviderId } from "@/components/LLMSelector";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { loadCvForApplication } from "@/lib/history";
import { useI18n } from "@/i18n/context";
import {
  exportCoverLetterDocx,
  generateApplicationKit,
  getDownloadUrl,
  type ApplicationKitResult,
  type CVParagraph,
} from "@/lib/api";

const JOB_STORAGE_KEY = "cv-tailor-job-description";

export default function ApplicationPage() {
  const { t } = useI18n();
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [recruiterName, setRecruiterName] = useState("");
  const [tone, setTone] = useState<"professional" | "friendly">("professional");
  const [outputLanguage, setOutputLanguage] = useState<"fr" | "en">("fr");
  const [llmProvider, setLlmProvider] = useState<LLMProviderId>("groq");
  const [llmModel, setLlmModel] = useState("llama-3.3-70b-versatile");
  const [hasLlmConfigured, setHasLlmConfigured] = useState(true);
  const [cvParagraphs, setCvParagraphs] = useState<CVParagraph[]>([]);
  const [cvFilename, setCvFilename] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApplicationKitResult | null>(null);
  const [exportingCoverLetter, setExportingCoverLetter] = useState(false);
  const [usingAdaptedCv, setUsingAdaptedCv] = useState(false);
  const [coverLetterPdfUrl, setCoverLetterPdfUrl] = useState<string | null>(null);

  const refreshCvFromStorage = useCallback(() => {
    const cv = loadCvForApplication();
    if (cv) {
      setCvParagraphs(cv.paragraphs);
      setCvFilename(cv.filename);
      setUsingAdaptedCv(cv.adapted);
    } else {
      setCvParagraphs([]);
      setCvFilename("");
      setUsingAdaptedCv(false);
    }
  }, []);

  useEffect(() => {
    const saved = sessionStorage.getItem(JOB_STORAGE_KEY);
    if (saved) setJobDescription(saved);
    refreshCvFromStorage();
  }, [refreshCvFromStorage]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") refreshCvFromStorage();
    };
    window.addEventListener("focus", refreshCvFromStorage);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", refreshCvFromStorage);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refreshCvFromStorage]);

  useEffect(() => {
    if (jobDescription.trim()) {
      sessionStorage.setItem(JOB_STORAGE_KEY, jobDescription);
    }
  }, [jobDescription]);

  const handleGenerate = useCallback(async () => {
    if (jobDescription.trim().length < 20 || cvParagraphs.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const kit = await generateApplicationKit({
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        companyName: companyName || undefined,
        jobTitle: jobTitle || undefined,
        recruiterName: recruiterName || undefined,
        tone,
        paragraphs: cvParagraphs,
      });
      setResult(kit);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  }, [
    jobDescription,
    outputLanguage,
    llmProvider,
    llmModel,
    companyName,
    jobTitle,
    recruiterName,
    tone,
    cvParagraphs,
    t,
  ]);

  const canSubmit =
    hasLlmConfigured && cvParagraphs.length > 0 && jobDescription.trim().length >= 20 && !loading;

  const handleExportCoverLetter = async () => {
    if (!result?.cover_letter) return;

    setExportingCoverLetter(true);
    setError(null);
    try {
      const exported = await exportCoverLetterDocx({
        coverLetter: result.cover_letter,
        companyName: companyName || undefined,
        jobTitle: jobTitle || undefined,
      });
      setCoverLetterPdfUrl(exported.download_url_pdf ?? null);
      const link = document.createElement("a");
      link.href = getDownloadUrl(exported.download_url);
      link.download = exported.filename;
      link.click();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setExportingCoverLetter(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-slate-100">
      <AppHeader active="application" />

      <main className="page-main">
        <BackendConnectionBanner />
        <PrivacyNotice />
        <div className="card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">{t("applicationFormTitle")}</h2>
          <p className="mb-4 text-sm text-slate-500">{t("applicationFormHint")}</p>

          {cvParagraphs.length > 0 ? (
            <p className="mb-4 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">
              {usingAdaptedCv ? t("applicationAdaptedCv") : t("applicationCvLoaded")}:{" "}
              <strong>{cvFilename}</strong> ({cvParagraphs.length} {t("compareLines")})
            </p>
          ) : (
            <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t("applicationCvMissing")}
            </p>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label" htmlFor="companyName">
                {t("applicationCompany")}
              </label>
              <input
                id="companyName"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="input-field"
                placeholder={t("applicationCompanyPlaceholder")}
              />
            </div>
            <div>
              <label className="label" htmlFor="jobTitleField">
                {t("applicationJobTitle")}
              </label>
              <input
                id="jobTitleField"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                className="input-field"
                placeholder={t("applicationJobTitlePlaceholder")}
              />
            </div>
            <div>
              <label className="label" htmlFor="recruiterName">
                {t("applicationRecruiter")}
              </label>
              <input
                id="recruiterName"
                value={recruiterName}
                onChange={(e) => setRecruiterName(e.target.value)}
                className="input-field"
                placeholder={t("applicationRecruiterPlaceholder")}
              />
            </div>
            <div>
              <label className="label">{t("applicationTone")}</label>
              <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:gap-3">
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="radio"
                    checked={tone === "professional"}
                    onChange={() => setTone("professional")}
                    className="text-brand-600"
                  />
                  {t("applicationToneProfessional")}
                </label>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="radio"
                    checked={tone === "friendly"}
                    onChange={() => setTone("friendly")}
                    className="text-brand-600"
                  />
                  {t("applicationToneFriendly")}
                </label>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <label className="label" htmlFor="jobDescription">
              {t("jobTitle")}
            </label>
            <textarea
              id="jobDescription"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder={t("jobPlaceholder")}
              rows={8}
              className="input-field"
            />
          </div>

          <div className="mt-4">
            <label className="label">{t("outputLang")}</label>
            <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
              <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
                <input
                  type="radio"
                  checked={outputLanguage === "fr"}
                  onChange={() => setOutputLanguage("fr")}
                  className="text-brand-600"
                />
                {t("french")}
              </label>
              <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
                <input
                  type="radio"
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
        </div>

        <div
          className={
            result
              ? "flex justify-center"
              : "sticky bottom-0 z-40 -mx-3 border-t border-slate-200/80 bg-gradient-to-t from-slate-100 via-slate-100/95 to-transparent px-3 py-3 safe-bottom sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0"
          }
        >
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!canSubmit}
            className="btn-primary w-full py-3.5 text-base sm:mx-auto sm:block sm:w-auto sm:max-w-md sm:px-8"
          >
            {loading ? t("applicationGenerating") : t("applicationGenerateBtn")}
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-6">
            {result.summary && (
              <div className="card border-brand-200 bg-brand-50/40">
                <p className="text-sm text-slate-700">{result.summary}</p>
              </div>
            )}

            <section className="card">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <h3 className="text-base font-semibold text-slate-900 sm:text-lg">{t("applicationCoverLetter")}</h3>
                <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap">
                  <button
                    type="button"
                    onClick={handleExportCoverLetter}
                    disabled={exportingCoverLetter}
                    className="btn-primary w-full px-3 py-2 text-xs sm:w-auto sm:py-1"
                  >
                    {exportingCoverLetter ? t("applicationExportingCoverLetter") : t("applicationDownloadCoverLetter")}
                  </button>
                  {coverLetterPdfUrl && (
                    <a
                      href={getDownloadUrl(coverLetterPdfUrl)}
                      download
                      className="btn-secondary w-full px-3 py-2 text-center text-xs sm:w-auto sm:py-1"
                    >
                      {t("applicationDownloadCoverLetterPdf")}
                    </a>
                  )}
                  <CopyButton text={result.cover_letter} />
                </div>
              </div>
              <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-800 sm:p-4">
                {result.cover_letter}
              </pre>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-base font-semibold text-slate-900 sm:text-lg">{t("applicationEmailSubject")}</h3>
                <CopyButton text={result.email_subject} />
              </div>
              <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-800">{result.email_subject}</p>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-base font-semibold text-slate-900 sm:text-lg">{t("applicationRecruiterMessage")}</h3>
                <CopyButton text={result.recruiter_message} />
              </div>
              <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-800 sm:p-4">
                {result.recruiter_message}
              </pre>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-base font-semibold text-slate-900 sm:text-lg">{t("applicationLinkedinMessage")}</h3>
                <CopyButton text={result.linkedin_message} />
              </div>
              <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-800 sm:p-4">
                {result.linkedin_message}
              </pre>
              <p className="mt-2 text-xs text-slate-500">
                {result.linkedin_message.length} {t("applicationChars")}
              </p>
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="card">
                <h3 className="mb-3 text-lg font-semibold text-slate-900">{t("applicationTips")}</h3>
                <ul className="space-y-2">
                  {result.application_tips.map((tip, index) => (
                    <li key={index} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                      {tip}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="card">
                <h3 className="mb-3 text-lg font-semibold text-slate-900">{t("applicationChecklist")}</h3>
                <ul className="space-y-2">
                  {result.checklist.map((item, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-slate-700"
                    >
                      <span className="text-green-600">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
