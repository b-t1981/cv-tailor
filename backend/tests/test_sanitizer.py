from app.models.schemas import ParagraphInfo
from app.services.modification_sanitizer import sanitize_modifications


def test_rejects_invented_words():
    paragraphs = [
        ParagraphInfo(id="b0", text="Développement Java et SQL", is_heading=False),
    ]
    mods = {"b0": "Développement Java SQL Kubernetes et Docker"}
    result = sanitize_modifications(paragraphs, mods)
    assert "b0" not in result


def test_accepts_cv_vocabulary_from_other_line():
    paragraphs = [
        ParagraphInfo(id="b0", text="Développement backend", is_heading=False),
        ParagraphInfo(id="b1", text="Stack : Python, Django", is_heading=False),
    ]
    mods = {"b0": "Développement backend Python"}
    result = sanitize_modifications(paragraphs, mods, max_new_word_ratio=0.55)
    assert "b0" in result


def test_light_mode_stricter_ratio():
    paragraphs = [
        ParagraphInfo(id="b0", text="Gestion de projets informatiques", is_heading=False),
    ]
    mods = {"b0": "Pilotage delivery projets informatiques transverses équipes"}
    strict = sanitize_modifications(paragraphs, mods, max_new_word_ratio=0.35)
    loose = sanitize_modifications(paragraphs, mods, max_new_word_ratio=0.55)
    assert len(loose) >= len(strict)
