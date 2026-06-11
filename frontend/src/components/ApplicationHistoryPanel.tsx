"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/context";
import { loadHistory, type ApplicationHistoryEntry } from "@/lib/history";

export function ApplicationHistoryPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState<ApplicationHistoryEntry[]>([]);

  useEffect(() => {
    setItems(loadHistory());
  }, []);

  if (items.length === 0) return null;

  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-slate-900">{t("historyTitle")}</h2>
      <ul className="space-y-2">
        {items.slice(0, 8).map((item) => (
          <li
            key={item.id}
            className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="font-medium text-slate-800 break-words">{item.jobTitleSnippet}</p>
              <p className="text-xs text-slate-500">
                {new Date(item.date).toLocaleString()} · {item.modificationsCount}{" "}
                {t("compareChanged")}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {item.scoreBefore != null && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5">
                  {t("scoreBefore")}: {item.scoreBefore}%
                </span>
              )}
              {item.scoreAfter != null && (
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-800">
                  {t("scoreAfter")}: {item.scoreAfter}%
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
