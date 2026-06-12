"use client";

import { useI18n } from "@/i18n/context";

export function PrivacyNotice() {
  const { t } = useI18n();

  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50 text-xs leading-relaxed text-slate-600">
      <summary className="cursor-pointer list-none px-4 py-2.5 font-medium text-slate-700 marker:content-none [&::-webkit-details-marker]:hidden">
        {t("privacyTitle")}
      </summary>
      <p className="border-t border-slate-200 px-4 py-3">{t("privacyNotice")}</p>
    </details>
  );
}
