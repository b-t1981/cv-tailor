import type { CVParagraph } from "./api";

const ADAPTED_CV_KEY = "cv-tailor-adapted-cv";
const PREVIEW_CV_KEY = "cv-tailor-preview-cv";

export interface CvForApplication {
  paragraphs: CVParagraph[];
  filename: string;
  adapted: boolean;
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
