from jose import jwt  # type: ignore

from .settings import settings


def authenticate_user(username: str, password: str) -> str | None:
    if username == settings.ADMIN_USER and password == settings.ADMIN_PASSWORD:
        return username
    return None


def create_access_token(data) -> str:
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def validate_access_token(token: str) -> bool:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        return username is not None
    except jwt.JWTError:
        return False
