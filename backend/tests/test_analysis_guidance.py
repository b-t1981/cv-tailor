from app.models.schemas import AnalysisGuidance
from app.services.analysis_guidance import build_analysis_guidance_suffix


def test_empty_guidance_returns_empty_suffix():
    assert build_analysis_guidance_suffix(None) == ""
    assert build_analysis_guidance_suffix(AnalysisGuidance()) == ""


def test_writing_improvements_included_in_suffix():
    guidance = AnalysisGuidance(
        writing_improvements=[
            "Utiliser des verbes d'action plus dynamiques",
            "Réorganiser certaines sections pour améliorer la lisibilité",
        ],
    )
    suffix = build_analysis_guidance_suffix(guidance)
    assert "MUST APPLY" in suffix
    assert "verbes d'action" in suffix
    assert "Réorganiser certaines sections" in suffix
    assert "strong action verbs" in suffix
