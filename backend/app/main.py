import re
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, judging
from .db import Base, engine, get_db
from .errors import ApiError
from .models import Problem, Submission, TestCase, User
from .security import admin_user, current_user, hash_password, make_token, verify_password


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(ApiError)
async def api_error(_, e: ApiError):
    return JSONResponse({"error": e.message}, status_code=e.status)


@app.exception_handler(StarletteHTTPException)
async def http_error(_, e: StarletteHTTPException):
    return JSONResponse({"error": str(e.detail)}, status_code=e.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_, e: RequestValidationError):
    first = e.errors()[0] if e.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return JSONResponse({"error": f"Invalid {loc or 'request'}: {first.get('msg', 'bad value')}"}, status_code=400)


@app.exception_handler(Exception)
async def unhandled(_, e: Exception):
    # Logs only the exception type: bodies may contain passwords or source code.
    print(f"unhandled error: {type(e).__name__}")
    return JSONResponse({"error": "Internal server error"}, status_code=500)


# ---------- auth ----------
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


def set_cookie(response: Response, user: User):
    response.set_cookie(config.COOKIE_NAME, make_token(user), httponly=True, samesite="lax",
                        secure=config.IS_PROD, max_age=config.SESSION_DAYS * 86400, path="/")


@app.post("/api/auth/register")
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", body.username):
        raise ApiError(400, "Username may only contain letters, digits and underscore (3-32 chars)")
    if db.scalar(select(User).where(User.username == body.username)):
        raise ApiError(409, "Username already taken")
    user = User(username=body.username, password_hash=hash_password(body.password), role="participant")
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise ApiError(409, "Username already taken")
    set_cookie(response, user)
    return {"username": user.username, "role": user.role}


@app.post("/api/auth/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "Invalid username or password")
    set_cookie(response, user)
    return {"username": user.username, "role": user.role}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=config.IS_PROD)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username, "role": user.role}


# ---------- problems ----------
@app.get("/api/problems")
def list_problems(user: User = Depends(current_user), db: Session = Depends(get_db)):
    solved = set(db.scalars(select(Submission.problem_id).where(Submission.user_id == user.id,
                                                                 Submission.verdict == "AC")))
    problems = db.scalars(select(Problem).where(Problem.published == True).order_by(Problem.id))  # noqa: E712
    return [{"id": p.id, "title": p.title, "solved": p.id in solved} for p in problems]


@app.get("/api/problems/{pid}")
def get_problem(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Problem, pid)
    if not p or (not p.published and user.role != "admin"):
        raise ApiError(404, "Problem not found")
    return {
        "id": p.id, "title": p.title, "statement": p.statement,
        "time_limit_sec": p.time_limit_sec, "memory_limit_mb": p.memory_limit_mb,
        "samples": [{"position": t.position, "input": t.input, "expected_output": t.expected_output}
                    for t in p.tests if t.is_sample],
    }


# ---------- submissions ----------
class SubmitBody(BaseModel):
    problem_id: int
    language: str
    source_code: str


def sub_json(s: Submission) -> dict:
    return {"id": s.id, "problem_id": s.problem_id, "status": s.status, "verdict": s.verdict,
            "failed_test": s.failed_test, "runtime_ms": s.runtime_ms, "memory_kb": s.memory_kb,
            "message": s.message}


@app.post("/api/submissions")
def submit(body: SubmitBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.language not in config.LANGUAGES:
        raise ApiError(400, "Language must be 'python' or 'cpp'")
    if not body.source_code.strip():
        raise ApiError(400, "Source code is empty")
    if len(body.source_code.encode()) > config.MAX_SOURCE_BYTES:
        raise ApiError(413, "Source code is larger than 64 KB")
    p = db.get(Problem, body.problem_id)
    if not p or (not p.published and user.role != "admin"):
        raise ApiError(404, "Problem not found")
    if not p.tests:
        raise ApiError(400, "Problem has no tests")
    sub = Submission(user_id=user.id, problem_id=p.id, language=body.language, source_code=body.source_code)
    db.add(sub)
    db.commit()
    judging.start(db, sub, p, list(p.tests))
    return {"id": sub.id}


@app.get("/api/submissions/{sid}")
def get_submission(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Submission, sid)
    if not s or (s.user_id != user.id and user.role != "admin"):
        raise ApiError(404, "Submission not found")  # same answer for missing and foreign ids
    judging.refresh(db, s)
    return sub_json(s)


@app.get("/api/submissions")
def my_submissions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Submission).where(Submission.user_id == user.id)
                      .order_by(Submission.id.desc()).limit(200))
    return [{**sub_json(s), "problem_title": s.problem.title, "language": s.language,
             "created_at": s.created_at.isoformat()} for s in rows]


# ---------- leaderboard ----------
@app.get("/api/leaderboard")
def leaderboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    users = {u.id: u.username for u in db.scalars(select(User).where(User.role == "participant"))}
    subs = db.execute(select(Submission.user_id, Submission.problem_id, Submission.verdict, Submission.created_at)
                      .where(Submission.status == "done").order_by(Submission.created_at, Submission.id)).all()
    per = defaultdict(lambda: {"wrong": 0, "ac_at": None})  # (user, problem) -> state
    for uid, pid, verdict, at in subs:
        if uid not in users:
            continue
        st = per[(uid, pid)]
        if st["ac_at"] is not None:
            continue
        if verdict == "AC":
            st["ac_at"] = at
        elif verdict in ("WA", "TLE", "RE"):
            st["wrong"] += 1
    stats = {uid: {"solved": 0, "wrong": 0, "last": None} for uid in users}
    for (uid, _), st in per.items():
        if st["ac_at"] is None:
            continue
        s = stats[uid]
        s["solved"] += 1
        s["wrong"] += st["wrong"]
        s["last"] = st["ac_at"] if s["last"] is None else max(s["last"], st["ac_at"])
    ordered = sorted(users, key=lambda u: (-stats[u]["solved"], stats[u]["wrong"],
                                           stats[u]["last"].timestamp() if stats[u]["last"] else 0, users[u]))
    return [{"rank": i + 1, "username": users[u], "solved": stats[u]["solved"], "wrong": stats[u]["wrong"]}
            for i, u in enumerate(ordered)]


# ---------- admin ----------
class TestIn(BaseModel):
    input: str = ""
    expected_output: str = ""
    is_sample: bool = False


class ProblemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=20000)
    time_limit_sec: float = Field(default=2.0, gt=0, le=15)
    memory_limit_mb: int = Field(default=256, ge=16, le=512)
    published: bool = False
    tests: list[TestIn] = Field(max_length=100)


def problem_admin_json(p: Problem) -> dict:
    return {"id": p.id, "title": p.title, "statement": p.statement, "time_limit_sec": p.time_limit_sec,
            "memory_limit_mb": p.memory_limit_mb, "published": p.published,
            "tests": [{"input": t.input, "expected_output": t.expected_output, "is_sample": t.is_sample}
                      for t in p.tests]}


def apply_problem(p: Problem, body: ProblemIn):
    if body.published and not body.tests:
        raise ApiError(400, "A published problem needs at least one test")
    p.title, p.statement = body.title, body.statement
    p.time_limit_sec, p.memory_limit_mb, p.published = body.time_limit_sec, body.memory_limit_mb, body.published
    p.tests = [TestCase(input=t.input, expected_output=t.expected_output, is_sample=t.is_sample, position=i + 1)
               for i, t in enumerate(body.tests)]


@app.get("/api/admin/problems")
def admin_list(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [problem_admin_json(p) for p in db.scalars(select(Problem).order_by(Problem.id))]


@app.post("/api/admin/problems")
def admin_create(body: ProblemIn, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    p = Problem()
    apply_problem(p, body)
    db.add(p)
    db.commit()
    return problem_admin_json(p)


@app.put("/api/admin/problems/{pid}")
def admin_update(pid: int, body: ProblemIn, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    p = db.get(Problem, pid)
    if not p:
        raise ApiError(404, "Problem not found")
    apply_problem(p, body)
    db.commit()
    return problem_admin_json(p)
