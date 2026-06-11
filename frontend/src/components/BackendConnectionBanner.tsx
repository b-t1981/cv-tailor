"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/api";
import { useI18n } from "@/i18n/context";

export function BackendConnectionBanner() {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return;

    checkBackendHealth().then((ok) => setVisible(!ok));
  }, []);

  if (!visible) return null;

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <p className="font-semibold">{t("backendMissingTitle")}</p>
      <p className="mt-1">{t("backendMissingHint")}</p>
    </div>
  );
}
