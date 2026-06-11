import re

from app.models.schemas import ParagraphInfo

STOP_WORDS = {
    "avec", "dans", "pour", "sur", "des", "les", "une", "par", "aux", "son", "ses",
    "the", "and", "for", "with", "from", "that", "this", "into", "via",
    "est", "sont", "été", "être", "plus", "tout", "tous", "toute",
}

ACRONYM_RE = re.compile(r"\b[A-Z]{2,}\b")
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9'/-]*")


def _significant_words(text: str) -> set[str]:
    return {
        word.lower()
        for word in WORD_RE.findall(text)
        if len(word) > 2 and word.lower() not in STOP_WORDS
    }


def _acronyms(text: str) -> set[str]:
    return set(ACRONYM_RE.findall(text))


def _is_safe_modification(
    original: str,
    new: str,
    cv_vocabulary: set[str],
    max_new_word_ratio: float = 0.55,
) -> bool:
    original = original.strip()
    new = new.strip()
    if not original or not new or original == new:
        return False

    original_words = _significant_words(original)
    new_words = _significant_words(new)
    if not new_words:
        return False

    added_words = new_words - original_words
    if not added_words:
        return False

    invented_words = added_words - cv_vocabulary
    if invented_words:
        return False

    # Allow richer rephrasing; block only when most of the line is new vocabulary.
    if len(added_words) / len(new_words) > max_new_word_ratio:
        return False

    added_acronyms = _acronyms(new) - _acronyms(original)
    if added_acronyms:
        return False

    return True


def sanitize_modifications(
    paragraphs: list[ParagraphInfo],
    modifications: dict[str, str],
    max_new_word_ratio: float = 0.55,
) -> dict[str, str]:
    """Drop LLM changes that duplicate lines or invent content."""
    original_by_id = {paragraph.id: paragraph.text.strip() for paragraph in paragraphs}
    existing_texts = {paragraph.text.strip() for paragraph in paragraphs if paragraph.text.strip()}
    cv_vocabulary: set[str] = set()
    for paragraph in paragraphs:
        cv_vocabulary |= _significant_words(paragraph.text)

    cleaned: dict[str, str] = {}
    used_new_texts: set[str] = set()

    for block_id, raw_new_text in modifications.items():
        if block_id not in original_by_id:
            continue

        new_text = raw_new_text.strip()
        original = original_by_id[block_id]
        if not _is_safe_modification(original, new_text, cv_vocabulary, max_new_word_ratio):
            continue

        if new_text in existing_texts and new_text != original:
            continue

        if new_text in used_new_texts:
            continue

        cleaned[block_id] = new_text
        used_new_texts.add(new_text)

    return cleaned
