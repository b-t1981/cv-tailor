import shutil

from app.config import settings
from app.session import is_valid_session_id


def clear_session_workspace(session_id: str) -> None:
    """Remove CV, exports and uploads for one browser session."""
    if not is_valid_session_id(session_id):
        raise ValueError("Invalid session")

    stored = settings.base_dir / settings.stored_cv_dir / session_id
    if stored.exists():
        shutil.rmtree(stored, ignore_errors=True)

    outputs = settings.session_output_path(session_id)
    if outputs.exists():
        shutil.rmtree(outputs, ignore_errors=True)

    for upload in settings.upload_path.glob(f"{session_id}_*"):
        upload.unlink(missing_ok=True)
