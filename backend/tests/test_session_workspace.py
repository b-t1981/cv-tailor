import pytest

from app.services.session_workspace import clear_session_workspace


def test_clear_session_workspace_no_error_when_empty():
    clear_session_workspace("abcdefghijklmnopqr")


def test_clear_session_workspace_rejects_invalid_id():
    with pytest.raises(ValueError):
        clear_session_workspace("bad id!")
