"use client";

import { useCallback, useRef, useState } from "react";
import { useI18n } from "@/i18n/context";

interface FileUploadProps {
  file: File | null;
  restored?: boolean;
  onFileSelect: (file: File | null) => void;
}

export function FileUpload({ file, restored, onFileSelect }: FileUploadProps) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (selected: File | null) => {
      if (!selected) return;
      const ext = selected.name.split(".").pop()?.toLowerCase();
      if (ext !== "docx" && ext !== "pdf") return;
      onFileSelect(selected);
    },
    [onFileSelect],
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setIsDragging(false);
      handleFile(event.dataTransfer.files[0] ?? null);
    },
    [handleFile],
  );

  return (
    <div className="card py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{t("uploadTitle")}</h2>
          <p className="text-xs text-slate-500">{t("uploadHint")}</p>
        </div>
        {restored && file && (
          <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-medium text-brand-700">
            {t("cvRestored")}
          </span>
        )}
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => event.key === "Enter" && inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={`mt-3 flex cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-3 transition ${
          isDragging
            ? "border-brand-500 bg-brand-50"
            : "border-slate-300 hover:border-brand-400 hover:bg-slate-50"
        }`}
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <div className="min-w-0 flex-1 text-left">
          <p className="truncate text-sm font-medium text-slate-700">
            {file ? file.name : t("uploadDrop")}
          </p>
          <p className="text-xs text-slate-500">{t("docxNote")}</p>
        </div>
        <span className="btn-secondary shrink-0 px-3 py-1.5 text-xs">{t("uploadBrowse")}</span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".docx,.pdf"
        className="hidden"
        onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
      />
    </div>
  );
}
