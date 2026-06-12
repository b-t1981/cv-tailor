"""Heuristics + merge logic for job-description analysis confidence."""

import re
from typing import Literal

ConfidenceLevel = Literal["high", "moderate", "low"]

_RANK: dict[str, int] = {"high": 2, "moderate": 1, "low": 0}

_CORPORATE_FRAGMENTS = (
    "nos valeurs",
    "notre entreprise",
    "rejoignez",
    "nous offrons",
    "culture d'entreprise",
    "diversité",
    "passionné",
    "leader mondial",
    "our values",
    "join our team",
    "we offer",
    "company culture",
)

_ROLE_FRAGMENTS = (
    "mission",
    "profil recherché",
    "profil :",
    "responsabilit",
    "compétence",
    "requise",
    "expérience",
    "skills",
    "requirements",
    "vous êtes",
    "vous avez",
    "job description",
    "role:",
)


def _normalize_level(value: str | None, default: ConfidenceLevel = "moderate") -> ConfidenceLevel:
    if value in _RANK:
        return value  # type: ignore[return-value]
    return default


def _min_level(a: ConfidenceLevel, b: ConfidenceLevel) -> ConfidenceLevel:
    return a if _RANK[a] <= _RANK[b] else b


def _estimate_role_content_ratio(job_description: str) -> int:
    text = job_description.strip()
    length = len(text)
    if length == 0:
        return 0

    lower = text.lower()
    corporate_hits = sum(lower.count(fragment) for fragment in _CORPORATE_FRAGMENTS)
    role_hits = sum(lower.count(fragment) for fragment in _ROLE_FRAGMENTS)

    sentences = [part.strip() for part in re.split(r"[.!?\n]+", text) if part.strip()]
    role_sentences = sum(
        1
        for sentence in sentences
        if any(fragment in sentence.lower() for fragment in _ROLE_FRAGMENTS)
    )

    if corporate_hits + role_hits > 0:
        keyword_ratio = int(round(role_hits / (role_hits + corporate_hits) * 100))
    else:
        keyword_ratio = 50

    sentence_ratio = (
        int(round(role_sentences / len(sentences) * 100)) if sentences else keyword_ratio
    )
    blended = int(round((keyword_ratio * 0.7) + (sentence_ratio * 0.3)))

    if length > 900 and corporate_hits >= role_hits * 4:
        blended = min(blended, 25)
    if length > 1800 and role_hits < 3:
        blended = min(blended, 18)

    return max(5, min(95, blended))


def _heuristic_profile_confidence(job_description: str) -> tuple[ConfidenceLevel, int]:
    text = job_description.strip()
    length = len(text)
    if length == 0:
        return "low", 0

    ratio = _estimate_role_content_ratio(job_description)

    if length < 80:
        return "low", ratio
    if length < 140 or ratio < 15:
        return "low", ratio
    if length < 220 or ratio < 22:
        return "moderate", ratio
    if ratio < 38:
        return "moderate", ratio
    return "high", ratio


def _heuristic_cv_confidence(job_description: str) -> ConfidenceLevel:
    length = len(job_description.strip())
    if length < 80:
        return "moderate"
    if length < 160:
        return "moderate"
    return "high"


def _fallback_reason(
    profile_confidence: ConfidenceLevel,
    role_content_ratio: int,
    job_description: str,
    output_language: str,
) -> str:
    length = len(job_description.strip())
    fr = output_language == "fr"

    if profile_confidence == "high":
        return (
            "L'offre contient assez d'exigences concrètes sur le poste pour une analyse fiable."
            if fr
            else "The posting has enough concrete role requirements for a reliable analysis."
        )

    if profile_confidence == "low":
        if length < 120:
            return (
                "Description très courte : peu d'exigences exploitables pour évaluer l'adéquation profil."
                if fr
                else "Very short description: too few requirements to assess profile fit reliably."
            )
        return (
            f"Environ {100 - role_content_ratio} % du texte concerne l'entreprise ou le contexte "
            "plutôt que le poste. Collez la section missions / profil recherché pour améliorer l'analyse."
            if fr
            else f"About {100 - role_content_ratio}% of the text is company or context, not the role. "
            "Paste the missions / requirements section for a sharper analysis."
        )

    if length < 280:
        return (
            "Description partielle : les scores profil sont indicatifs. Complétez si possible la partie missions."
            if fr
            else "Partial description: profile scores are indicative. Add missions/requirements if you can."
        )
    return (
        f"Une partie importante de l'offre ({100 - role_content_ratio} % hors cœur du poste) "
        "peut biaiser mots-clés et écarts."
        if fr
        else f"A large share of the posting ({100 - role_content_ratio}% non-role content) may skew keywords and gaps."
    )


def apply_analysis_confidence(
    result: dict,
    job_description: str,
    output_language: str = "fr",
) -> dict:
    """Merge LLM confidence fields with conservative heuristics."""
    heuristic_profile, role_ratio = _heuristic_profile_confidence(job_description)
    heuristic_cv = _heuristic_cv_confidence(job_description)

    llm_profile = _normalize_level(result.get("profile_confidence"))
    llm_cv = _normalize_level(result.get("cv_confidence"))
    llm_ratio = result.get("role_content_ratio")

    if isinstance(llm_ratio, (int, float)):
        llm_ratio_int = max(0, min(100, int(llm_ratio)))
        role_content_ratio = min(llm_ratio_int, role_ratio + 10)
        role_content_ratio = int(round((role_content_ratio * 0.35) + (role_ratio * 0.65)))
    else:
        role_content_ratio = role_ratio

    profile_confidence = _min_level(llm_profile, heuristic_profile)
    cv_confidence = _min_level(llm_cv, heuristic_cv)

    reason = str(result.get("confidence_reason", "")).strip()
    if not reason or profile_confidence != llm_profile:
        reason = _fallback_reason(profile_confidence, role_content_ratio, job_description, output_language)

    result["profile_confidence"] = profile_confidence
    result["cv_confidence"] = cv_confidence
    result["role_content_ratio"] = role_content_ratio
    result["confidence_reason"] = reason
    return result
