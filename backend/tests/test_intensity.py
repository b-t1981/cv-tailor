from app.services.tailor_intensity import get_intensity_profile


def test_ats_profile_exists():
    profile = get_intensity_profile("ats")
    assert "ATS" in profile.user_prompt_suffix
    assert profile.temperature == 0.25


def test_unknown_defaults_to_strong():
    profile = get_intensity_profile("unknown")
    strong = get_intensity_profile("strong")
    assert profile.max_new_word_ratio == strong.max_new_word_ratio
