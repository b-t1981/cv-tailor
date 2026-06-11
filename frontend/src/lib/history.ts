import type { CVParagraph } from "./api";

export interface ApplicationHistoryEntry {
  id: string;
  date: string;
  jobTitleSnippet: string;
  scoreBefore: number | null;
  scoreAfter: number | null;
  modificationsCount: number;
  downloadUrl?: string;
  tailoredParagraphs?: CVParagraph[];
}

const HISTORY_KEY = "cv-tailor-history";
const ADAPTED_CV_KEY = "cv-tailor-adapted-cv";
const PREVIEW_CV_KEY = "cv-tailor-preview-cv";
const MAX_ENTRIES = 20;

export interface CvForApplication {
  paragraphs: CVParagraph[];
  filename: string;
  adapted: boolean;
}

export function loadHistory(): ApplicationHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as ApplicationHistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveHistoryEntry(entry: ApplicationHistoryEntry): void {
  const items = [entry, ...loadHistory()].slice(0, MAX_ENTRIES);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
}

export function saveAdaptedCv(paragraphs: CVParagraph[], filename: string): void {
  localStorage.setItem(
    ADAPTED_CV_KEY,
    JSON.stringify({ paragraphs, filename, savedAt: new Date().toISOString() }),
  );
}

export function loadAdaptedCv(): { paragraphs: CVParagraph[]; filename: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(ADAPTED_CV_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as { paragraphs: CVParagraph[]; filename: string };
    if (!data.paragraphs?.length) return null;
    return data;
  } catch {
    return null;
  }
}

export function savePreviewCv(paragraphs: CVParagraph[], filename: string): void {
  localStorage.setItem(
    PREVIEW_CV_KEY,
    JSON.stringify({ paragraphs, filename, savedAt: new Date().toISOString() }),
  );
}

export function loadCvForApplication(): CvForApplication | null {
  const adapted = loadAdaptedCv();
  if (adapted) {
    return { ...adapted, adapted: true };
  }
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PREVIEW_CV_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as { paragraphs: CVParagraph[]; filename: string };
    if (!data.paragraphs?.length) return null;
    return { paragraphs: data.paragraphs, filename: data.filename, adapted: false };
  } catch {
    return null;
  }
}
