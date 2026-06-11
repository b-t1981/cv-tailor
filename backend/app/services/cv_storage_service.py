import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.schemas import ParagraphInfo
from app.services.cv_extractor import extract_cv_paragraphs
from app.session import is_valid_session_id

METADATA_FILE = "metadata.json"
CV_BASENAME = "last_cv"


class CVStorageService:
    def _storage_path(self, session_id: str) -> Path:
        if not is_valid_session_id(session_id):
            raise ValueError("Invalid session")
        return settings.session_storage_path(session_id)

    def save(
        self,
        session_id: str,
        file_path: Path,
        filename: str,
        paragraphs: list[ParagraphInfo],
    ) -> None:
        storage_path = self._storage_path(session_id)
        suffix = file_path.suffix.lower()
        target = storage_path / f"{CV_BASENAME}{suffix}"
        shutil.copy2(file_path, target)

        for old in storage_path.glob(f"{CV_BASENAME}.*"):
            if old != target:
                old.unlink(missing_ok=True)

        fresh_paragraphs = extract_cv_paragraphs(target)
        if fresh_paragraphs:
            paragraphs = fresh_paragraphs

        metadata = {
            "filename": Path(filename).name,
            "suffix": suffix,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "paragraphs": [paragraph.model_dump() for paragraph in paragraphs],
        }
        with open(storage_path / METADATA_FILE, "w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

    def load_metadata(self, session_id: str) -> dict | None:
        storage_path = self._storage_path(session_id)
        metadata_path = storage_path / METADATA_FILE
        if not metadata_path.exists():
            return None

        with open(metadata_path, encoding="utf-8") as file:
            data = json.load(file)

        suffix = data.get("suffix", ".docx")
        cv_path = storage_path / f"{CV_BASENAME}{suffix}"
        if not cv_path.exists():
            return None

        data["file_path"] = str(cv_path)
        paragraphs = extract_cv_paragraphs(cv_path)
        if not paragraphs:
            paragraphs = [ParagraphInfo(**item) for item in data.get("paragraphs", [])]
        data["paragraphs"] = paragraphs
        return data

    def get_file_path(self, session_id: str) -> Path | None:
        metadata = self.load_metadata(session_id)
        if not metadata:
            return None
        path = Path(metadata["file_path"])
        return path if path.exists() else None


cv_storage_service = CVStorageService()
