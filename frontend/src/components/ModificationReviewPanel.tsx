"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/context";
import type { LLMProviderId } from "@/lib/types";
import {
  applyModifications,
  retryModifications,
  type CVParagraph,
  type TailorIntensity,
} from "@/lib/api";

interface ModificationReviewPanelProps {
  originalParagraphs: CVParagraph[];
  proposedModifications: Record<string, string>;
  jobDescription: string;
  outputLanguage: "fr" | "en";
  llmProvider: LLMProviderId;
  llmModel: string;
  tailorIntensity: TailorIntensity;
  onAcceptedChange: (accepted: Record<string, string>) => void;
  onExportReady: (urls: { downloadUrl: string; downloadUrlPdf?: string | null }) => void;
  onModificationsUpdate: (mods: Record<string, string>, tailored: CVParagraph[]) => void;
}

export function ModificationReviewPanel({
  originalParagraphs,
  proposedModifications,
  jobDescription,
  outputLanguage,
  llmProvider,
  llmModel,
  tailorIntensity,
  onAcceptedChange,
  onExportReady,
  onModificationsUpdate,
}: ModificationReviewPanelProps) {
  const { t } = useI18n();
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set());
  const [editedTexts, setEditedTexts] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exported, setExported] = useState(false);

  const modificationEntries = Object.entries(proposedModifications);

  useEffect(() => {
    const ids = Object.keys(proposedModifications);
    setAcceptedIds(new Set(ids));
    setEditedTexts({ ...proposedModifications });
    setExported(false);
    setError(null);
  }, [proposedModifications]);

  useEffect(() => {
    const accepted: Record<string, string> = {};
    for (const id of acceptedIds) {
      const text = editedTexts[id]?.trim();
      if (text) accepted[id] = text;
    }
    onAcceptedChange(accepted);
  }, [acceptedIds, editedTexts, onAcceptedChange]);

  if (modificationEntries.length === 0) {
    return null;
  }

  const originalById = Object.fromEntries(originalParagraphs.map((p) => [p.id, p.text]));

  const toggle = (id: string) => {
    setAcceptedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setExported(false);
  };

  const selectAll = () => {
    setAcceptedIds(new Set(Object.keys(proposedModifications)));
    setExported(false);
  };

  const selectNone = () => {
    setAcceptedIds(new Set());
    setExported(false);
  };

  const getAccepted = () => {
    const accepted: Record<string, string> = {};
    for (const id of acceptedIds) {
      const text = editedTexts[id]?.trim();
      if (text) accepted[id] = text;
    }
    return accepted;
  };

  const getRejectedIds = () =>
    Object.keys(proposedModifications).filter((id) => !acceptedIds.has(id));

  const handleApply = async () => {
    const accepted = getAccepted();
    if (Object.keys(accepted).length === 0) {
      setError(t("reviewNoSelection"));
      return;
    }

    setApplying(true);
    setError(null);
    try {
      const result = await applyModifications(accepted);
      onExportReady({
        downloadUrl: result.download_url,
        downloadUrlPdf: result.download_url_pdf,
      });
      setExported(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setApplying(false);
    }
  };

  const handleRetryRejected = async () => {
    const rejected = getRejectedIds();
    if (rejected.length === 0) return;

    setRetrying(true);
    setError(null);
    try {
      const kept = getAccepted();
      const result = await retryModifications({
        jobDescription,
        outputLanguage,
        llmProvider,
        llmModel,
        tailorIntensity,
        rejectedBlockIds: rejected,
        keptModifications: kept,
      });
      const merged = result.modified_paragraphs;
      setEditedTexts(merged);
      setAcceptedIds(new Set(Object.keys(merged)));
      onModificationsUpdate(merged, result.tailored_paragraphs);
      setExported(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setRetrying(false);
    }
  };

  const rejectedCount = getRejectedIds().length;

  return (
    <div className="card border-brand-200">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900 sm:text-lg">{t("reviewTitle")}</h2>
          <p className="text-sm text-slate-500">{t("reviewHint")}</p>
        </div>
        <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
          <button type="button" onClick={selectAll} className="btn-secondary col-span-1 px-2 py-2 text-xs sm:px-3 sm:py-1">
            {t("reviewSelectAll")}
          </button>
          <button type="button" onClick={selectNone} className="btn-secondary col-span-1 px-2 py-2 text-xs sm:px-3 sm:py-1">
            {t("reviewSelectNone")}
          </button>
          {rejectedCount > 0 && (
            <button
              type="button"
              onClick={handleRetryRejected}
              disabled={retrying}
              className="btn-secondary col-span-2 px-2 py-2 text-xs sm:col-span-1 sm:px-3 sm:py-1"
            >
              {retrying ? t("reviewRetrying") : t("reviewRetryRejected")}
            </button>
          )}
        </div>
      </div>

      <div className="max-h-[min(70vh,520px)] space-y-3 overflow-y-auto pr-0.5 sm:pr-1">
        {modificationEntries.map(([id]) => {
          const original = originalById[id] ?? "";
          const isAccepted = acceptedIds.has(id);
          return (
            <div
              key={id}
              className={`rounded-lg border p-3 transition ${
                isAccepted ? "border-brand-300 bg-brand-50/50" : "border-slate-200 bg-slate-50 opacity-80"
              }`}
            >
              <div className="mb-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isAccepted}
                  onChange={() => toggle(id)}
                  className="text-brand-600"
                />
                <span className="text-xs font-medium text-slate-500">{t("reviewAccept")}</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-amber-700">{t("compareBefore")}</p>
                  <p className="text-sm text-slate-600 line-through decoration-amber-300">{original}</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-green-700">{t("reviewEditAfter")}</p>
                  <textarea
                    value={editedTexts[id] ?? ""}
                    onChange={(e) => {
                      setEditedTexts((prev) => ({ ...prev, [id]: e.target.value }));
                      setExported(false);
                    }}
                    rows={3}
                    className="input-field text-sm"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
        <button
          type="button"
          onClick={handleApply}
          disabled={applying || acceptedIds.size === 0}
          className="btn-primary w-full px-6 py-3 sm:w-auto sm:py-2"
        >
          {applying ? t("reviewApplying") : t("reviewApplyBtn")}
        </button>
        <span className="text-center text-sm text-slate-500 sm:text-left">
          {acceptedIds.size} / {modificationEntries.length} {t("reviewSelected")}
        </span>
      </div>

      {error && (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {exported && (
        <p className="mt-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {t("reviewExportReady")}
        </p>
      )}
    </div>
  );
}
