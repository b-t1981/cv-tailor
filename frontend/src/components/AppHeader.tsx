"use client";

import Link from "next/link";
import { AppVersion } from "@/components/AppVersion";
import { useI18n } from "@/i18n/context";

interface AppHeaderProps {
  active?: "cv" | "application";
}

const navLinkClass = (isActive: boolean) =>
  `flex flex-1 items-center justify-center rounded-md px-2 py-2.5 text-sm font-medium sm:flex-none sm:px-3 sm:py-1.5 ${
    isActive ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200 active:bg-slate-300"
  }`;

export function AppHeader({ active = "cv" }: AppHeaderProps) {
  const { t, locale, setLocale } = useI18n();

  return (
    <header className="safe-top sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-brand-900 sm:text-2xl">{t("appTitle")}</h1>
              <AppVersion />
            </div>
            <p className="mt-0.5 line-clamp-2 text-xs text-slate-600 sm:text-sm">
              {active === "cv" ? t("appSubtitle") : t("applicationPageSubtitle")}
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <nav className="flex w-full gap-1.5 sm:w-auto sm:gap-2" aria-label="Main">
              <Link href="/" className={navLinkClass(active === "cv")}>
                {t("navCv")}
              </Link>
              <Link href="/candidature" className={navLinkClass(active === "application")}>
                {t("navApplication")}
              </Link>
            </nav>

            <div className="flex items-center justify-end gap-1.5 sm:gap-2">
              <span className="mr-1 text-xs text-slate-500">{t("uiLang")}</span>
              <button
                type="button"
                onClick={() => setLocale("fr")}
                aria-pressed={locale === "fr"}
                className={`min-h-[40px] min-w-[40px] rounded-md px-2.5 py-1 text-sm font-medium sm:min-h-0 sm:min-w-0 ${
                  locale === "fr" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                FR
              </button>
              <button
                type="button"
                onClick={() => setLocale("en")}
                aria-pressed={locale === "en"}
                className={`min-h-[40px] min-w-[40px] rounded-md px-2.5 py-1 text-sm font-medium sm:min-h-0 sm:min-w-0 ${
                  locale === "en" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                EN
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
