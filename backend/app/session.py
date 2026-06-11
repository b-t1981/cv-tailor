import re
import secrets
from typing import Annotated

from fastapi import HTTPException, Request

SESSION_COOKIE = "cv_tailor_sid"
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def generate_session_id() -> str:
    return secrets.token_urlsafe(24)


def is_valid_session_id(value: str | None) -> bool:
    return bool(value and SESSION_ID_RE.fullmatch(value))


def get_session_id(request: Request) -> str:
    session_id = getattr(request.state, "session_id", None)
    if not is_valid_session_id(session_id):
        raise HTTPException(status_code=500, detail="Session not initialized")
    return session_id


SessionId = Annotated[str, "session_id"]
