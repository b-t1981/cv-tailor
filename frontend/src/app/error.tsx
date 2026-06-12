"use client";

import { useEffect } from "react";
import { useI18n } from "@/i18n/context";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useI18n();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 text-center shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-slate-900">{t("errorPageTitle")}</h2>
        <p className="mb-4 text-sm text-slate-600">{t("errorPageMessage")}</p>
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          {t("errorPageRetry")}
        </button>
      </div>
    </div>
  );
}
