"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/context";

interface CopyButtonProps {
  text: string;
  className?: string;
}

export function CopyButton({ text, className = "" }: CopyButtonProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`btn-secondary w-full px-3 py-2 text-xs sm:w-auto sm:py-1 ${className}`}
    >
      {copied ? t("copied") : t("copy")}
    </button>
  );
}
