"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { CopyButton } from "@/components/CopyButton";
import { LLMSelector, type LLMProviderId } from "@/components/LLMSelector";
import { useI18n } from "@/i18n/context";
import {
  fetchLastCV,
  generateApplicationKit,
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
  const [llmProvider, setLlmProvider] = useState<LLMProviderId>("openai");
  const [llmModel, setLlmModel] = useState("gpt-4o-mini");
  const [hasLlmConfigured, setHasLlmConfigured] = useState(true);
  const [cvParagraphs, setCvParagraphs] = useState<CVParagraph[]>([]);
  const [cvFilename, setCvFilename] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApplicationKitResult | null>(null);

  useEffect(() => {
    const saved = sessionStorage.getItem(JOB_STORAGE_KEY);
    if (saved) {
      setJobDescription(saved);
    }

    fetchLastCV()
      .then((cv) => {
        setCvParagraphs(cv.paragraphs);
        setCvFilename(cv.filename);
      })
      .catch(() => {
        setCvParagraphs([]);
        setCvFilename("");
      });
  }, []);

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

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-slate-100">
      <AppHeader active="application" />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <div className="card">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">{t("applicationFormTitle")}</h2>
          <p className="mb-4 text-sm text-slate-500">{t("applicationFormHint")}</p>

          {cvParagraphs.length > 0 ? (
            <p className="mb-4 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">
              {t("applicationCvLoaded")}: <strong>{cvFilename}</strong> ({cvParagraphs.length}{" "}
              {t("compareLines")})
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
              <div className="flex gap-3 pt-2">
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
            <div className="flex gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  checked={outputLanguage === "fr"}
                  onChange={() => setOutputLanguage("fr")}
                  className="text-brand-600"
                />
                {t("french")}
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
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
            provider={llmProvider}
            model={llmModel}
            onChange={(nextProvider, nextModel) => {
              setLlmProvider(nextProvider);
              setLlmModel(nextModel);
            }}
            onConfiguredChange={setHasLlmConfigured}
          />
        </div>

        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!canSubmit}
            className="btn-primary px-8 py-3 text-base"
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
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-semibold text-slate-900">{t("applicationCoverLetter")}</h3>
                <CopyButton text={result.cover_letter} />
              </div>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
                {result.cover_letter}
              </pre>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-semibold text-slate-900">{t("applicationEmailSubject")}</h3>
                <CopyButton text={result.email_subject} />
              </div>
              <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-800">{result.email_subject}</p>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-semibold text-slate-900">{t("applicationRecruiterMessage")}</h3>
                <CopyButton text={result.recruiter_message} />
              </div>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
                {result.recruiter_message}
              </pre>
            </section>

            <section className="card">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-semibold text-slate-900">{t("applicationLinkedinMessage")}</h3>
                <CopyButton text={result.linkedin_message} />
              </div>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
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
