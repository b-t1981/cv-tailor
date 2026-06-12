from app.services.job_description_confidence import apply_analysis_confidence


def test_short_posting_lowers_profile_confidence():
    result = apply_analysis_confidence(
        {"score": 70, "profile_confidence": "high", "cv_confidence": "high"},
        "Ingénieur Java. Spring. 3 ans.",
        "fr",
    )
    assert result["profile_confidence"] in ("low", "moderate")
    assert result["confidence_reason"]


def test_corporate_heavy_posting_moderate_or_low():
    corporate = (
        "Notre entreprise est leader mondial. Nos valeurs : innovation, respect, diversité. "
        "Rejoignez une équipe passionnée. Nous offrons télétravail, mutuelle, tickets resto. "
    ) * 8
    corporate += "Mission : support applicatif N2. SQL requis."
    result = apply_analysis_confidence(
        {"score": 65, "profile_confidence": "high", "role_content_ratio": 80},
        corporate,
        "fr",
    )
    assert result["profile_confidence"] in ("low", "moderate")
    assert result["role_content_ratio"] < 50


def test_focused_posting_can_be_high():
    focused = (
        "Ingénieur support applicatif N2\n"
        "Missions : gestion incidents, SQL, ticketing ServiceNow, coordination équipes métier.\n"
        "Profil : 3 ans expérience IT, anglais, ITIL.\n"
        "Compétences : Windows, Active Directory, bases de données."
    )
    result = apply_analysis_confidence(
        {"score": 72, "profile_confidence": "high", "cv_confidence": "high", "role_content_ratio": 70},
        focused,
        "fr",
    )
    assert result["profile_confidence"] == "high"
