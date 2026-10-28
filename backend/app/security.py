from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .errors import ApiError
from .models import User


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    if len(pw.encode()) > 72:  # otherwise "72 correct bytes + anything" would also match
        return False
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=config.SESSION_DAYS)
    return jwt.encode({"sub": str(user.id), "typ": "session", "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(config.COOKIE_NAME)
    if not token:
        return None
    try:
        data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        if data.get("typ", "session") != "session":  # tokens issued before "typ" existed are sessions
            return None
        return db.get(User, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None


RUN_TOKEN_MINUTES = 15


def make_run_token(user_id: int, problem_id: int, items: list[dict], custom: bool) -> str:
    """Stateless handle for a Run. Signed, bound to the user, and typed so it can never act as a session."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=RUN_TOKEN_MINUTES)
    return jwt.encode({"typ": "run", "uid": user_id, "pid": problem_id, "items": items, "custom": custom,
                       "iat": datetime.now(timezone.utc), "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def read_run_token(token: str, user: User) -> dict:
    try:
        data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ApiError(410, "This run has expired. Run your code again.")
    except jwt.PyJWTError:
        raise ApiError(400, "Invalid run token")
    if data.get("typ") != "run" or not isinstance(data.get("items"), list):
        raise ApiError(400, "Invalid run token")
    if data.get("uid") != user.id:
        raise ApiError(404, "Run not found")
    return data


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise ApiError(401, "Not signed in")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise ApiError(403, "Admin only")
    return user
