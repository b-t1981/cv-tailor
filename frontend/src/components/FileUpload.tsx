"use client";

import { useCallback, useRef, useState } from "react";
import { useI18n } from "@/i18n/context";

interface FileUploadProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  onInvalidFile?: () => void;
}

export function FileUpload({ file, onFileSelect, onInvalidFile }: FileUploadProps) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (selected: File | null) => {
      if (!selected) return;
      const ext = selected.name.split(".").pop()?.toLowerCase();
      if (ext !== "docx" && ext !== "pdf") {
        onInvalidFile?.();
        return;
      }
      onFileSelect(selected);
    },
    [onFileSelect, onInvalidFile],
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
        className={`mt-3 flex cursor-pointer flex-col gap-3 rounded-lg border border-dashed px-4 py-4 transition sm:flex-row sm:items-center sm:py-3 ${
          isDragging
            ? "border-brand-500 bg-brand-50"
            : "border-slate-300 hover:border-brand-400 hover:bg-slate-50 active:bg-slate-50"
        }`}
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center self-start rounded-full bg-brand-100 text-brand-600 sm:h-9 sm:w-9">
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
        <span className="btn-secondary w-full shrink-0 px-3 py-2.5 text-center text-xs sm:w-auto sm:py-1.5">
          {t("uploadBrowse")}
        </span>
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
