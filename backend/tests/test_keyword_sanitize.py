from app.services.llm_service import LLMService


def test_missing_keyword_removed_when_only_in_cv():
    job = "Manage batches and hotline dispatch in Geneva."
    cv = "Experience with Automic (UC4) scheduler and Control-M."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": [],
            "missing_keywords": ["Automic (UC4)", "scheduler"],
        },
    )
    assert "scheduler" in [k.lower() for k in result["present_keywords"]]
    assert result["missing_keywords"] == []


def test_missing_keyword_kept_when_in_job_not_cv():
    job = "Experience with Kubernetes and Docker required."
    cv = "Strong Linux and SQL background."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": ["Linux"],
            "missing_keywords": ["Kubernetes", "Docker"],
        },
    )
    assert any(k.lower() == "kubernetes" for k in result["missing_keywords"])
    assert any(k.lower() == "docker" for k in result["missing_keywords"])
