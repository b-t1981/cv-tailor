"use client";

import type { ReactNode } from "react";

interface CollapsibleCardProps {
  title: string;
  defaultOpen?: boolean;
  actions?: ReactNode;
  children: ReactNode;
}

export function CollapsibleCard({ title, defaultOpen = false, actions, children }: CollapsibleCardProps) {
  return (
    <details className="card group" open={defaultOpen || undefined}>
      <summary className="flex cursor-pointer list-none flex-col gap-2 marker:content-none sm:flex-row sm:items-center sm:justify-between [&::-webkit-details-marker]:hidden">
        <span className="inline-flex min-w-0 items-center gap-2 text-base font-semibold text-slate-900 sm:text-lg">
          <span className="shrink-0 text-brand-600 transition group-open:rotate-90">›</span>
          <span className="break-words">{title}</span>
        </span>
        {actions && (
          <div
            className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {actions}
          </div>
        )}
      </summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}
