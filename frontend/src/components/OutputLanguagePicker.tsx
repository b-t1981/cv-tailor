"use client";

import { useI18n } from "@/i18n/context";

interface OutputLanguagePickerProps {
  value: "fr" | "en";
  onChange: (lang: "fr" | "en") => void;
  loading?: boolean;
  error?: string | null;
}

export function OutputLanguagePicker({ value, onChange, loading, error }: OutputLanguagePickerProps) {
  const { t } = useI18n();

  return (
    <div>
      <label className="label">{t("outputLang")}</label>
      <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
        <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
          <input
            type="radio"
            checked={value === "fr"}
            onChange={() => onChange("fr")}
            className="text-brand-600"
          />
          {t("french")}
        </label>
        <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm sm:min-h-0">
          <input
            type="radio"
            checked={value === "en"}
            onChange={() => onChange("en")}
            className="text-brand-600"
          />
          {t("english")}
        </label>
      </div>
      {loading && <p className="mt-2 text-xs text-brand-700">{t("cvTranslateLoading")}</p>}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
