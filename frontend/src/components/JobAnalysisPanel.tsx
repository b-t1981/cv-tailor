"use client";

import { useI18n } from "@/i18n/context";
import type { JobAnalysisResult } from "@/lib/api";

interface JobAnalysisPanelProps {
  analysis: JobAnalysisResult | null;
  loading: boolean;
  canAnalyze: boolean;
  waitingForCv?: boolean;
  waitingForJob?: boolean;
  error?: string | null;
  scoreBefore?: number | null;
  scoreAfter?: number | null;
  onAnalyze: () => void;
}

function scoreColor(score: number): string {
  if (score >= 75) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

export function JobAnalysisPanel({
  analysis,
  loading,
  canAnalyze,
  waitingForCv,
  waitingForJob,
  error,
  scoreBefore,
  scoreAfter,
  onAnalyze,
}: JobAnalysisPanelProps) {
  const { t } = useI18n();

  if (waitingForCv) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-500">
        {t("matchNeedCv")}
      </div>
    );
  }

  if (waitingForJob) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-500">
        {t("matchNeedJob")}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={!canAnalyze || loading}
          className="btn-secondary w-full px-4 py-2.5 text-sm sm:w-auto sm:py-2"
        >
          {loading ? t("analysisLoading") : t("analysisBtn")}
        </button>
        {!analysis && !loading && !error && (
          <span className="text-xs text-slate-500">{t("analysisHint")}</span>
        )}
      </div>

      {loading && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-700">
          {t("analysisLoading")}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {analysis && !loading && (
        <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex items-center gap-3">
              <div
                className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-4 border-slate-100 text-lg font-bold sm:h-16 sm:w-16 sm:text-xl ${scoreColor(analysis.score)}`}
              >
                {analysis.score}%
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">{t("matchTitle")}</p>
                <p className="text-xs text-slate-500">{t("matchSubtitle")}</p>
              </div>
            </div>
            <div className="w-full min-w-0 flex-1 sm:min-w-[160px]">
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full transition-all ${scoreBg(analysis.score)}`}
                  style={{ width: `${analysis.score}%` }}
                />
              </div>
            </div>
          </div>

          {(scoreBefore != null || scoreAfter != null) && (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {scoreBefore != null && (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                  {t("scoreBefore")}: {scoreBefore}%
                </span>
              )}
              {scoreAfter != null && (
                <span className="rounded-full bg-green-100 px-2.5 py-1 font-medium text-green-800">
                  {t("scoreAfter")}: {scoreAfter}%
                </span>
              )}
            </div>
          )}

          {analysis.summary && <p className="mt-3 text-sm text-slate-700">{analysis.summary}</p>}

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {analysis.strengths.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-green-700">{t("matchStrengths")}</p>
                <ul className="space-y-1 text-sm text-slate-700">
                  {analysis.strengths.map((item) => (
                    <li key={item} className="flex gap-1.5">
                      <span className="text-green-500">+</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.gaps.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-amber-700">{t("matchGaps")}</p>
                <ul className="space-y-1 text-sm text-slate-700">
                  {analysis.gaps.map((item) => (
                    <li key={item} className="flex gap-1.5">
                      <span className="text-amber-500">−</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {(analysis.present_keywords.length > 0 || analysis.missing_keywords.length > 0) && (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <p className="mb-2 text-sm font-semibold text-slate-900">{t("keywordsTitle")}</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {analysis.present_keywords.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase text-green-700">
                      {t("keywordsPresent")}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.present_keywords.map((kw) => (
                        <span
                          key={kw}
                          className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {analysis.missing_keywords.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase text-red-700">
                      {t("keywordsMissing")}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.missing_keywords.map((kw) => (
                        <span
                          key={kw}
                          className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{t("keywordsMissingHint")}</p>
                  </div>
                )}
              </div>
              {analysis.keyword_suggestions?.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-xs font-semibold uppercase text-brand-700">
                    {t("keywordsSuggestions")}
                  </p>
                  <ul className="space-y-1.5 text-sm text-slate-700">
                    {analysis.keyword_suggestions.map((tip) => (
                      <li key={tip} className="rounded-lg bg-brand-50 px-3 py-2">
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
