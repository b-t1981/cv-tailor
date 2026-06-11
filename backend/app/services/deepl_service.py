import json
import re
import urllib.error
import urllib.parse
import urllib.request

from app.config import settings
from app.models.schemas import ParagraphInfo

_DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
_DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"
_BATCH_SIZE = 50

# Lignes à ne pas envoyer à DeepL (contacts, URLs, dates seules)
_SKIP_LINE_RE = re.compile(
    r"^[\w.+-]+@[\w.-]+\.\w+$|"
    r"^\+?[\d\s().-]{8,}$|"
    r"^https?://\S+$|"
    r"^\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}$",
    re.IGNORECASE,
)


class DeepLService:
    def is_configured(self) -> bool:
        return settings.is_deepl_configured()

    def translate_paragraphs(
        self,
        paragraphs: list[ParagraphInfo],
        target_language: str,
    ) -> dict:
        target_code = "FR" if target_language == "fr" else "EN-GB"

        translatable_indices: list[int] = []
        texts: list[str] = []
        for index, paragraph in enumerate(paragraphs):
            text = paragraph.text.strip()
            if not text or _SKIP_LINE_RE.match(text):
                continue
            translatable_indices.append(index)
            texts.append(paragraph.text)

        if not texts:
            return {
                "paragraphs": paragraphs,
                "source_language": target_language,
                "target_language": target_language,
                "translated": False,
            }

        translated_texts, detected_code = self._translate_batches(texts, target_code)
        source_language = _map_deepl_lang(detected_code)

        if source_language == target_language:
            return {
                "paragraphs": paragraphs,
                "source_language": source_language,
                "target_language": target_language,
                "translated": False,
            }

        updated: list[ParagraphInfo] = []
        translation_by_index = dict(zip(translatable_indices, translated_texts, strict=True))
        for index, paragraph in enumerate(paragraphs):
            new_text = translation_by_index.get(index)
            if new_text and new_text.strip() != paragraph.text.strip():
                updated.append(
                    ParagraphInfo(
                        id=paragraph.id,
                        text=new_text,
                        style=paragraph.style,
                        is_heading=paragraph.is_heading,
                        modified=True,
                    )
                )
            else:
                updated.append(paragraph)

        return {
            "paragraphs": updated,
            "source_language": source_language,
            "target_language": target_language,
            "translated": True,
        }

    def _translate_batches(self, texts: list[str], target_code: str) -> tuple[list[str], str]:
        results: list[str] = []
        detected = ""
        for start in range(0, len(texts), _BATCH_SIZE):
            chunk = texts[start : start + _BATCH_SIZE]
            batch_texts, batch_detected = self._translate_batch(chunk, target_code)
            results.extend(batch_texts)
            if batch_detected:
                detected = batch_detected
        return results, detected

    def _translate_batch(self, texts: list[str], target_code: str) -> tuple[list[str], str]:
        payload: list[tuple[str, str]] = [("target_lang", target_code)]
        for text in texts:
            payload.append(("text", text))

        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            settings.deepl_api_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"DeepL-Auth-Key {settings.deepl_api_key.strip()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"DeepL request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"DeepL connection failed: {exc.reason}") from exc

        translations = data.get("translations", [])
        if len(translations) != len(texts):
            raise ValueError("DeepL returned an unexpected number of translations")

        detected = str(translations[0].get("detected_source_language", "")).upper()
        return [str(item.get("text", "")) for item in translations], detected


def _map_deepl_lang(code: str) -> str:
    normalized = code.upper()
    if normalized.startswith("FR"):
        return "fr"
    if normalized.startswith("EN"):
        return "en"
    return "fr" if "FR" in normalized else "en"


deepl_service = DeepLService()
