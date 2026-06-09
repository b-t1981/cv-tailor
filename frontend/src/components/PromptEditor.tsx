"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/context";
import { resetPrompts, savePrompts, type PromptConfig } from "@/lib/api";

interface PromptEditorProps {
  systemPrompt: string;
  userPrompt: string;
  onChange: (config: PromptConfig) => void;
  defaultOpen?: boolean;
}

export function PromptEditor({
  systemPrompt,
  userPrompt,
  onChange,
  defaultOpen = false,
}: PromptEditorProps) {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 3000);
    return () => clearTimeout(timer);
  }, [saved]);

  const handleReset = async () => {
    try {
      const defaults = await resetPrompts();
      onChange(defaults);
    } catch {
      setError(t("error"));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const savedConfig = await savePrompts({
        system_prompt: systemPrompt,
        user_prompt: userPrompt,
      });
      onChange(savedConfig);
      setSaved(true);
    } catch {
      setError(t("error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <div>
          <h2 className="text-base font-semibold text-slate-900">{t("promptTitle")}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {isOpen ? t("promptHint") : t("promptCollapsedHint")}
          </p>
        </div>
        <span className="shrink-0 text-sm text-brand-600">
          {isOpen ? t("promptCollapse") : t("promptExpand")}
        </span>
      </button>

      {isOpen && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <div className="mb-4 flex flex-wrap justify-end gap-2">
            <button type="button" onClick={handleReset} className="btn-secondary">
              {t("resetPrompts")}
            </button>
            <button type="button" onClick={handleSave} disabled={saving} className="btn-primary">
              {t("savePrompts")}
            </button>
          </div>

          <div className="mb-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
            <span className="font-medium">{t("variables")}:</span>{" "}
            <code className="text-brand-700">{"{job_description}"}</code>,{" "}
            <code className="text-brand-700">{"{cv_paragraphs}"}</code>,{" "}
            <code className="text-brand-700">{"{output_language}"}</code>
          </div>

          <div className="space-y-4">
            <div>
              <label className="label">{t("systemPrompt")}</label>
              <textarea
                value={systemPrompt}
                onChange={(event) =>
                  onChange({ system_prompt: event.target.value, user_prompt: userPrompt })
                }
                rows={10}
                className="input-field font-mono text-xs leading-relaxed"
              />
            </div>
            <div>
              <label className="label">{t("userPrompt")}</label>
              <textarea
                value={userPrompt}
                onChange={(event) =>
                  onChange({ system_prompt: systemPrompt, user_prompt: event.target.value })
                }
                rows={8}
                className="input-field font-mono text-xs leading-relaxed"
              />
            </div>
          </div>

          {saved && <p className="mt-3 text-sm text-green-600">{t("promptsSaved")}</p>}
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>
      )}
    </div>
  );
}
