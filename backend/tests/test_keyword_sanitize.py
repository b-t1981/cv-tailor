from app.services.llm_service import LLMService


def test_missing_keyword_removed_when_only_in_cv():
    job = "Manage batches on scheduler and hotline dispatch in Geneva."
    cv = "Experience with Automic (UC4) scheduler and Control-M."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": [],
            "missing_keywords": ["Automic (UC4)", "scheduler"],
        },
    )
    assert result["missing_keywords"] == []
    assert any("scheduler" in k.lower() for k in result["present_keywords"])


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


def test_noise_keywords_removed_from_missing():
    job = (
        "Specification of Core Function\n"
        "Work in Geneva on 2x8 teams. Manage batches on scheduler and hotlines. "
        "Show accountability and partnership-oriented mindset."
    )
    cv = "IT operations support with scheduler monitoring."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": [],
            "missing_keywords": ["Geneva", "2x8 teams", "Accountability", "hotlines"],
        },
    )
    missing_lower = [k.lower() for k in result["missing_keywords"]]
    assert "geneva" not in missing_lower
    assert "accountability" not in missing_lower
    assert any("hotline" in k for k in missing_lower)


def test_scheduler_synonyms_detected_in_cv():
    job = (
        "Specification of Core Function\n"
        "Follow and control all batches on scheduler, manage alarms and hotlines."
    )
    cv = "Pilotage Automic (UC4) et supervision des flux batch en environnement bancaire."
    result = LLMService._sanitize_analysis_keywords(
        job,
        cv,
        {
            "present_keywords": ["Support applicatif"],
            "missing_keywords": [
                "Scheduler",
                "Planification de tâches",
                "Gestion de batches",
                "IT Operations",
            ],
        },
    )
    missing_lower = [k.lower() for k in result["missing_keywords"]]
    assert "scheduler" not in missing_lower
    assert "planification" not in " ".join(missing_lower)
    assert "batch" not in " ".join(missing_lower) or result["missing_keywords"] == []


def test_gaps_removed_when_cv_covers_concept():
    gaps = LLMService._sanitize_gaps(
        [
            "Pas de mention de l'utilisation d'outils de planification de tâches (scheduler)",
            "Pas d'expérience spécifique dans le domaine des opérations IT",
        ],
        "Support applicatif et pilotage Automic UC4 pour les jobs planifiés.",
    )
    assert gaps == []
