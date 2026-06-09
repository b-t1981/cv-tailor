"use client";

import { getDownloadUrl, type TailorResult } from "@/lib/api";
import { useI18n } from "@/i18n/context";

interface ResultPanelProps {
  result: TailorResult | null;
  matchScore?: number | null;
}

export function ResultPanel({ result, matchScore }: ResultPanelProps) {
  const { t } = useI18n();

  if (!result) return null;

  return (
    <div className="card border-green-200 bg-green-50/30">
      <h2 className="mb-4 text-lg font-semibold text-slate-900">{t("resultTitle")}</h2>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
          {result.modifications_count} {t("modifications")}
        </span>
        <span className="rounded-full bg-brand-100 px-3 py-1 text-sm font-medium text-brand-800">
          {t("llmUsed")}: {result.llm_provider} / {result.llm_model}
        </span>
        {matchScore != null && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-800">
            {t("matchTitle")}: {matchScore}%
          </span>
        )}
        <a
          href={getDownloadUrl(result.download_url)}
          download
          className="btn-primary inline-flex items-center gap-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          {t("download")}
        </a>
        {result.download_url_pdf && (
          <a
            href={getDownloadUrl(result.download_url_pdf)}
            download
            className="btn-secondary inline-flex items-center gap-2"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            {t("downloadPdf")}
          </a>
        )}
      </div>

      <div className="mb-4">
        <h3 className="label">{t("summary")}</h3>
        <p className="rounded-lg bg-white p-3 text-sm text-slate-700">{result.summary}</p>
      </div>
    </div>
  );
}
