"use client";

import { APP_BUILD_LABEL, APP_BUILT_AT } from "@/generated/build-info";

function formatBuildDate(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function AppVersion() {
  if (!APP_BUILD_LABEL) return null;

  const title = APP_BUILT_AT ? `Build: ${formatBuildDate(APP_BUILT_AT)}` : undefined;

  return (
    <span
      title={title}
      className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium tabular-nums text-slate-500"
    >
      {APP_BUILD_LABEL}
    </span>
  );
}
