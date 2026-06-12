from app.models.schemas import AnalysisGuidance


def build_analysis_guidance_suffix(guidance: AnalysisGuidance | None) -> str:
    """Turn prior analyze_job_fit output into mandatory tailor instructions."""
    if guidance is None or not guidance.has_content():
        return ""

    sections: list[str] = []

    if guidance.writing_improvements:
        items = "\n".join(f"- {item}" for item in guidance.writing_improvements)
        sections.append(
            "### Writing improvements — MUST APPLY in modified lines\n"
            "Each point below must be visibly reflected in the rewritten bullets/profile "
            "(not only mentioned in the summary):\n"
            f"{items}"
        )

    if guidance.gaps:
        items = "\n".join(f"- {item}" for item in guidance.gaps)
        sections.append(
            "### Job gaps — address honestly in wording\n"
            "Reframe existing experience to highlight transferable skills where truthful. "
            "Never invent qualifications:\n"
            f"{items}"
        )

    if guidance.missing_keywords:
        items = "\n".join(f"- {item}" for item in guidance.missing_keywords)
        sections.append(
            "### Missing keywords — weave in when truthful\n"
            "Use these terms only if the CV already supports them (same domain, tools, or duties):\n"
            f"{items}"
        )

    if guidance.keyword_suggestions:
        items = "\n".join(f"- {item}" for item in guidance.keyword_suggestions)
        sections.append(f"### Keyword integration tips\n{items}")

    return (
        "\n\n## Prior CV analysis — mandatory guidance\n"
        "The CV was analyzed before adaptation. You MUST apply every item below in your "
        "actual line rewrites.\n\n"
        + "\n\n".join(sections)
        + "\n\n### How to apply writing feedback\n"
        "- Replace weak/passive verbs with strong action verbs (e.g. piloté, optimisé, "
        "coordonné, delivered, led, streamlined).\n"
        "- Surface achievements, metrics and outcomes already present in the original text.\n"
        "- Improve readability: concise bullets, clear flow, less redundancy.\n"
        "- If reorganization was suggested: improve logical flow and grouping through "
        "clearer bullet wording (do not change headings, dates, companies or job titles).\n"
    )
