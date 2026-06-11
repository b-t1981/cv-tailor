"use client";

import type { TailorResult } from "@/lib/api";
import { useI18n } from "@/i18n/context";

interface ResultPanelProps {
  result: TailorResult | null;
  acceptedCount?: number;
}

export function ResultPanel({ result, acceptedCount }: ResultPanelProps) {
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
        {acceptedCount != null && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-800">
            {acceptedCount} {t("reviewSelected")}
          </span>
        )}
      </div>

      <div className="mb-4">
        <h3 className="label">{t("summary")}</h3>
        <p className="rounded-lg bg-white p-3 text-sm text-slate-700">{result.summary}</p>
      </div>

      <p className="text-sm text-slate-600">{t("reviewDownloadHint")}</p>
    </div>
  );
}
