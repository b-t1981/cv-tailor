"use client";

import { useI18n } from "@/i18n/context";

export function PrivacyNotice() {
  const { t } = useI18n();

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-600">
      {t("privacyNotice")}
    </div>
  );
}
