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
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=config.SESSION_DAYS)
    return jwt.encode({"sub": str(user.id), "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(config.COOKIE_NAME)
    if not token:
        return None
    try:
        data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        return db.get(User, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise ApiError(401, "Not signed in")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise ApiError(403, "Admin only")
    return user
