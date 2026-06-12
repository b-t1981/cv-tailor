import { JOB_STORAGE_KEY } from "@/lib/constants";

const HISTORY_KEY = "cv-tailor-history";
const ADAPTED_CV_KEY = "cv-tailor-adapted-cv";
const PREVIEW_CV_KEY = "cv-tailor-preview-cv";

let clientResetDone = false;

function shouldResetOnNavigation(): boolean {
  if (typeof window === "undefined") return false;
  const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  if (!nav) return true;
  return nav.type === "reload" || nav.type === "navigate";
}

export function clearClientWorkspace(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(JOB_STORAGE_KEY);
  localStorage.removeItem(HISTORY_KEY);
  localStorage.removeItem(ADAPTED_CV_KEY);
  localStorage.removeItem(PREVIEW_CV_KEY);
}

/** Synchronous wipe before pages read persisted state (full page load / refresh). */
export function runWorkspaceResetOnLoad(): void {
  if (clientResetDone || typeof window === "undefined") return;
  clientResetDone = true;
  if (!shouldResetOnNavigation()) return;
  clearClientWorkspace();
}
