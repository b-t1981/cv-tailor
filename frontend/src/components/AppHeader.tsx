"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/context";

interface AppHeaderProps {
  active?: "cv" | "application";
}

export function AppHeader({ active = "cv" }: AppHeaderProps) {
  const { t, locale, setLocale } = useI18n();

  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">{t("appTitle")}</h1>
          <p className="text-sm text-slate-600">
            {active === "cv" ? t("appSubtitle") : t("applicationPageSubtitle")}
          </p>
        </div>

        <nav className="flex flex-wrap items-center gap-2">
          <Link
            href="/"
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              active === "cv" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {t("navCv")}
          </Link>
          <Link
            href="/candidature"
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              active === "application"
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {t("navApplication")}
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{t("uiLang")}</span>
          <button
            type="button"
            onClick={() => setLocale("fr")}
            className={`rounded-md px-2.5 py-1 text-sm font-medium ${
              locale === "fr" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            FR
          </button>
          <button
            type="button"
            onClick={() => setLocale("en")}
            className={`rounded-md px-2.5 py-1 text-sm font-medium ${
              locale === "en" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            EN
          </button>
        </div>
      </div>
    </header>
  );
}
