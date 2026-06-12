"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/context";
import { fetchLLMProviders, type LLMProviderInfo } from "@/lib/api";
import type { LLMProviderId } from "@/lib/types";

export type { LLMProviderId };

interface LLMSelectorProps {
  provider: LLMProviderId;
  model: string;
  onChange: (provider: LLMProviderId, model: string) => void;
  onConfiguredChange?: (hasConfiguredProvider: boolean) => void;
  /** Masque l'UI tout en conservant la logique (Groq par défaut si hidden). */
  hidden?: boolean;
}

export function LLMSelector({
  provider,
  model,
  onChange,
  onConfiguredChange,
  hidden = false,
}: LLMSelectorProps) {
  const { t } = useI18n();
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [defaultProvider, setDefaultProvider] = useState<LLMProviderId>("openai");

  useEffect(() => {
    fetchLLMProviders()
      .then((data) => {
        setProviders(data.providers);
        setDefaultProvider(data.default_provider as LLMProviderId);
        const initial = hidden
          ? (data.providers.find((item) => item.id === "groq" && item.configured) ??
            data.providers.find((item) => item.configured))
          : (data.providers.find((item) => item.id === data.default_provider && item.configured) ??
            data.providers.find((item) => item.configured));
        onConfiguredChange?.(data.providers.some((item) => item.configured));
        if (initial) {
          onChange(initial.id as LLMProviderId, initial.default_model);
        }
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = providers.find((item) => item.id === provider);
  const availableModels = selected?.models ?? [];

  const handleProviderChange = (nextProvider: LLMProviderId) => {
    const info = providers.find((item) => item.id === nextProvider);
    onChange(nextProvider, info?.default_model ?? model);
  };

  if (hidden) {
    return null;
  }

  return (
    <div className="mt-4 space-y-4">
      <div>
        <label className="label">{t("llmProvider")}</label>
        <div className="grid gap-2 sm:grid-cols-3">
          {providers.map((item) => (
            <label
              key={item.id}
              className={`flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2.5 text-sm transition ${
                provider === item.id
                  ? "border-brand-500 bg-brand-50"
                  : "border-slate-300 hover:border-brand-300"
              } ${!item.configured ? "opacity-60" : ""}`}
            >
              <input
                type="radio"
                name="llmProvider"
                checked={provider === item.id}
                disabled={!item.configured}
                onChange={() => handleProviderChange(item.id as LLMProviderId)}
                className="mt-0.5 text-brand-600"
              />
              <span>
                <span className="block font-medium text-slate-800">{item.name}</span>
                <span className="block text-xs text-slate-500">
                  {item.configured ? t("llmConfigured") : t("llmNotConfigured")}
                </span>
              </span>
            </label>
          ))}
        </div>
        {providers.length === 0 && (
          <p className="text-sm text-slate-500">{t("llmLoading")}</p>
        )}
      </div>

      {availableModels.length > 0 && (
        <div>
          <label className="label" htmlFor="llmModel">
            {t("llmModel")}
          </label>
          <select
            id="llmModel"
            value={model}
            onChange={(event) => onChange(provider, event.target.value)}
            className="input-field"
          >
            {availableModels.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
      )}

      {provider === defaultProvider && (
        <p className="text-xs text-slate-500">{t("llmDefaultNote")}</p>
      )}
    </div>
  );
}
