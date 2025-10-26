# app/middleware/auth_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.security import decode_access_token
from app.db.session import async_session
from app.repositories.user_repo import UserRepository

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization")
        request.state.user = None
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            try:
                payload = decode_access_token(token)
                user_id = int(payload.get("sub"))
                # گرفتن یوزر از DB
                async with async_session() as session:
                    repo = UserRepository(session)
                    user = await repo.get_by_id(user_id)
                    request.state.user = user
            except Exception:
                request.state.user = None
        response = await call_next(request)
        return response
