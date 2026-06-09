"use client";

import { useI18n } from "@/i18n/context";
import type { MatchScoreResult } from "@/lib/api";

interface MatchScorePanelProps {
  match: MatchScoreResult | null;
  loading: boolean;
  waitingForCv?: boolean;
  waitingForJob?: boolean;
  error?: string | null;
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

export function MatchScorePanel({
  match,
  loading,
  waitingForCv,
  waitingForJob,
  error,
}: MatchScorePanelProps) {
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

  if (loading) {
    return (
      <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-700">
        {t("matchLoading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!match) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-16 w-16 items-center justify-center rounded-full border-4 border-slate-100 text-xl font-bold ${scoreColor(match.score)}`}
          >
            {match.score}%
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">{t("matchTitle")}</p>
            <p className="text-xs text-slate-500">{t("matchSubtitle")}</p>
          </div>
        </div>
        <div className="min-w-[160px] flex-1">
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all ${scoreBg(match.score)}`}
              style={{ width: `${match.score}%` }}
            />
          </div>
        </div>
      </div>

      {match.summary && <p className="mt-3 text-sm text-slate-700">{match.summary}</p>}

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {match.strengths.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-green-700">{t("matchStrengths")}</p>
            <ul className="space-y-1 text-sm text-slate-700">
              {match.strengths.map((item) => (
                <li key={item} className="flex gap-1.5">
                  <span className="text-green-500">+</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {match.gaps.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-amber-700">{t("matchGaps")}</p>
            <ul className="space-y-1 text-sm text-slate-700">
              {match.gaps.map((item) => (
                <li key={item} className="flex gap-1.5">
                  <span className="text-amber-500">−</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
