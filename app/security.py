from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, Response
from .config import settings

SESSION_COOKIE = "mdt_session"
serializer = URLSafeSerializer(settings.secret_key, salt="session")

def set_session(response: Response, data: dict):
    response.set_cookie(SESSION_COOKIE, serializer.dumps(data), httponly=True, samesite="lax")

def get_session(request: Request) -> dict | None:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    try:
        return serializer.loads(cookie)
    except BadSignature:
        return None

def clear_session(response: Response):
    response.delete_cookie(SESSION_COOKIE)
