from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.session import SESSION_COOKIE, generate_session_id, is_valid_session_id


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cookie_value = request.cookies.get(SESSION_COOKIE)
        if is_valid_session_id(cookie_value):
            request.state.session_id = cookie_value
            request.state.new_session = False
        else:
            request.state.session_id = generate_session_id()
            request.state.new_session = True

        response = await call_next(request)

        if request.state.new_session:
            response.set_cookie(
                key=SESSION_COOKIE,
                value=request.state.session_id,
                httponly=True,
                secure=settings.cookie_secure,
                samesite=settings.cookie_samesite,
                max_age=settings.session_ttl_hours * 3600,
                path="/",
            )

        return response
