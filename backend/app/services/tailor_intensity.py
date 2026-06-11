from dataclasses import dataclass
from typing import Literal

TailorIntensity = Literal["light", "strong", "ats"]


@dataclass(frozen=True)
class IntensityProfile:
    user_prompt_suffix: str
    retry_prompt_suffix: str
    temperature: float
    max_new_word_ratio: float
    min_modifications_before_retry: int


INTENSITY_PROFILES: dict[TailorIntensity, IntensityProfile] = {
    "light": IntensityProfile(
        user_prompt_suffix=(
            "\n\n## Intensity: LIGHT\n"
            "- Modify only the most relevant experience bullets and profile (target 25–40% of [TEXT] lines).\n"
            "- Prefer subtle rephrasing; keep wording close to the original when already adequate.\n"
            "- Skip lines that are already a reasonable match."
        ),
        retry_prompt_suffix=(
            "\n\nIMPORTANT: Too few lines were changed. "
            "Return 4–8 additional modified block IDs with light, targeted rephrasing only."
        ),
        temperature=0.2,
        max_new_word_ratio=0.35,
        min_modifications_before_retry=2,
    ),
    "strong": IntensityProfile(
        user_prompt_suffix=(
            "\n\n## Intensity: STRONG\n"
            "- Modify most experience bullets and profile/summary (target 60–80% of [TEXT] lines).\n"
            "- Emphasize job keywords and outcomes; make alignment obvious to a recruiter.\n"
            "- Rephrase aggressively while staying 100% truthful to the CV."
        ),
        retry_prompt_suffix=(
            "\n\nIMPORTANT: Your previous response changed too few lines. "
            "Return at least 8–15 modified block IDs for experience bullets and profile lines."
        ),
        temperature=0.35,
        max_new_word_ratio=0.55,
        min_modifications_before_retry=3,
    ),
    "ats": IntensityProfile(
        user_prompt_suffix=(
            "\n\n## Intensity: ATS (Applicant Tracking System)\n"
            "- Optimize wording for ATS keyword matching using terms from the job description.\n"
            "- ONLY use keywords that truthfully describe existing CV experience (never invent).\n"
            "- Prefer exact job-description terms when they match the candidate's real skills.\n"
            "- Modify experience bullets and skills lines (target 50–70% of [TEXT] lines).\n"
            "- Keep natural readable French/English — no keyword stuffing lists."
        ),
        retry_prompt_suffix=(
            "\n\nIMPORTANT: Add more ATS-aligned rephrasing on experience bullets. "
            "Return 6–12 modified block IDs using honest keyword alignment only."
        ),
        temperature=0.25,
        max_new_word_ratio=0.45,
        min_modifications_before_retry=3,
    ),
}


def get_intensity_profile(intensity: str) -> IntensityProfile:
    if intensity not in INTENSITY_PROFILES:
        return INTENSITY_PROFILES["strong"]
    return INTENSITY_PROFILES[intensity]  # type: ignore[index]
