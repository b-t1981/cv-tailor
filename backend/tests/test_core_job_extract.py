from app.services.llm_service import LLMService


def test_core_job_extract_prefers_specification_over_company_mission():
    job = (
        "Our Purpose and Mission\n"
        "We are a private bank.\n\n"
        "EFG Competencies\n"
        "Be Entrepreneurial\n\n"
        "Specification of Core Function\n"
        "Control all batches on scheduler, manage alarms and hotlines.\n"
    )
    core = LLMService._extract_core_job_text(job)
    assert core.lower().startswith("specification of core function")
    assert "scheduler" in core.lower()
    assert "be entrepreneurial" not in core.lower()


def test_hallucinated_tools_removed_from_missing():
    job = (
        "Specification of Core Function\n"
        "Control batches on scheduler and manage hotlines.\n"
    )
    cv = "Experience Automic UC4, support applicatif, ITIL, CRM."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": ["CRM", "ITIL"],
            "missing_keywords": ["Automic (UC4)", "Jira", "ServiceNow", "ETL Pentaho"],
            "keyword_suggestions": [
                "Mentionnez Automic (UC4) si vous le maîtrisez",
                "Développez Jira",
            ],
        },
    )
    missing_joined = " ".join(k.lower() for k in result["missing_keywords"])
    assert "automic" not in missing_joined
    assert "jira" not in missing_joined
    assert "servicenow" not in missing_joined
    assert "pentaho" not in missing_joined
    assert result["keyword_suggestions"] == []
