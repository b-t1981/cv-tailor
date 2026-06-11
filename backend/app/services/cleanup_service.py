import shutil
import time
from pathlib import Path

from app.config import settings
from app.session import is_valid_session_id


def cleanup_old_outputs() -> int:
    """Remove output files and session folders older than OUTPUT_TTL_HOURS."""
    ttl_seconds = settings.output_ttl_hours * 3600
    cutoff = time.time() - ttl_seconds
    deleted = 0

    for path in settings.output_path.iterdir():
        if not path.exists():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        if path.is_file():
            if mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
            continue

        if path.is_dir() and is_valid_session_id(path.name):
            if mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                deleted += 1

    stored_root = settings.base_dir / settings.stored_cv_dir
    if stored_root.exists():
        for path in stored_root.iterdir():
            if not path.is_dir() or not is_valid_session_id(path.name):
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                deleted += 1

    return deleted
