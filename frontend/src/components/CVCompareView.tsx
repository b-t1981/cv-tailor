"use client";

import { getDownloadUrl } from "@/lib/api";
import { useI18n } from "@/i18n/context";
import type { CVParagraph } from "@/lib/api";

interface CVColumnProps {
  title: string;
  paragraphs: CVParagraph[];
  emptyMessage?: string;
  highlightModified?: boolean;
  modifiedIds?: Set<string>;
  showDiffOnly?: boolean;
}

function CVColumn({
  title,
  paragraphs,
  emptyMessage,
  highlightModified = false,
  modifiedIds,
  showDiffOnly = false,
}: CVColumnProps) {
  const items = showDiffOnly
    ? paragraphs.filter((p) => modifiedIds?.has(p.id) || p.modified)
    : paragraphs;

  return (
    <div className="flex min-h-[360px] flex-col rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <p className="text-sm italic text-slate-400">{emptyMessage ?? ""}</p>
        ) : (
          <div className="space-y-2">
            {items.map((paragraph) => {
              const isModified = modifiedIds?.has(paragraph.id) ?? paragraph.modified;
              return (
                <div
                  key={paragraph.id}
                  className={`rounded-md px-3 py-2 text-sm leading-relaxed ${
                    highlightModified && isModified
                      ? "border border-green-300 bg-green-50 text-green-900"
                      : !highlightModified && isModified
                        ? "border border-amber-300 bg-amber-50 text-amber-900 line-through decoration-amber-400/70"
                        : paragraph.is_heading
                          ? "font-semibold text-slate-900"
                          : "text-slate-700"
                  }`}
                >
                  {paragraph.text}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

interface CVCompareViewProps {
  originalParagraphs: CVParagraph[];
  tailoredParagraphs: CVParagraph[] | null;
  filename?: string;
  downloadUrl?: string | null;
  downloadUrlPdf?: string | null;
  modificationsCount?: number;
  summary?: string | null;
}

export function CVCompareView({
  originalParagraphs,
  tailoredParagraphs,
  filename,
  downloadUrl,
  downloadUrlPdf,
  modificationsCount,
  summary,
}: CVCompareViewProps) {
  const { t } = useI18n();

  const hasResult = Boolean(tailoredParagraphs && tailoredParagraphs.length > 0);
  const modifiedIds = new Set(
    tailoredParagraphs?.filter((item) => item.modified).map((item) => item.id) ?? [],
  );
  const modifiedCount = modifiedIds.size;

  if (!hasResult && originalParagraphs.length === 0 && !filename) {
    return null;
  }

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {hasResult ? t("compareAfterTitle") : t("comparePreviewTitle")}
          </h2>
          {filename && <p className="text-sm text-slate-500">{filename}</p>}
          {!hasResult && originalParagraphs.length > 0 && (
            <p className="mt-1 text-xs text-slate-400">
              {originalParagraphs.length} {t("compareLines")}
            </p>
          )}
          {hasResult && summary && (
            <p className="mt-2 max-w-3xl text-sm text-slate-600">{summary}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {hasResult && (
            <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800">
              {modificationsCount ?? modifiedCount} {t("compareChanged")}
            </span>
          )}
          {hasResult && downloadUrl && (
            <a
              href={getDownloadUrl(downloadUrl)}
              download
              className="btn-primary inline-flex items-center gap-2 px-3 py-1.5 text-xs"
            >
              {t("download")}
            </a>
          )}
          {hasResult && downloadUrlPdf && (
            <a
              href={getDownloadUrl(downloadUrlPdf)}
              download
              className="btn-secondary inline-flex items-center gap-2 px-3 py-1.5 text-xs"
            >
              {t("downloadPdf")}
            </a>
          )}
        </div>
      </div>

      {hasResult ? (
        <>
          <p className="mb-3 text-xs text-slate-500">{t("compareDiffHint")}</p>
          <div className="grid gap-4 lg:grid-cols-2">
            <CVColumn
              title={t("compareBefore")}
              paragraphs={originalParagraphs}
              modifiedIds={modifiedIds}
              showDiffOnly
              emptyMessage={t("compareNoChanges")}
            />
            <CVColumn
              title={t("compareAfter")}
              paragraphs={tailoredParagraphs ?? []}
              highlightModified
              showDiffOnly
              emptyMessage={t("compareNoChanges")}
            />
          </div>
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
              {t("compareFullView")}
            </p>
            <div className="grid gap-4 lg:grid-cols-2">
              <CVColumn title={t("compareBeforeFull")} paragraphs={originalParagraphs} />
              <CVColumn
                title={t("compareAfterFull")}
                paragraphs={tailoredParagraphs ?? []}
                highlightModified
                modifiedIds={modifiedIds}
              />
            </div>
          </div>
        </>
      ) : (
        <>
          <p className="mb-3 text-xs text-slate-500">{t("comparePreviewHint")}</p>
          <CVColumn
            title={t("compareOriginal")}
            paragraphs={originalParagraphs}
            emptyMessage={t("compareEmptyCv")}
          />
        </>
      )}
    </div>
  );
}
