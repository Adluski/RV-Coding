import json
import re
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, judge0, judging
from .db import get_db, init_db
from .errors import ApiError
from .models import Problem, Submission, TestCase, User
from .security import (admin_user, current_user, hash_password, make_run_token, make_token, read_run_token,
                       verify_password)


@asynccontextmanager
async def lifespan(app):
    init_db()
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


def find_user(db: Session, username: str) -> User | None:
    return db.scalars(select(User).where(func.lower(User.username) == username.lower()).order_by(User.id)).first()


@app.post("/api/auth/register")
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", body.username):
        raise ApiError(400, "Username may only contain letters, digits and underscore (3-32 chars)")
    if len(body.password.encode()) > 72:  # bcrypt ignores everything after 72 bytes
        raise ApiError(400, "Password is too long (maximum 72 bytes)")
    if find_user(db, body.username):
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
    user = find_user(db, body.username)
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
    return [{"id": p.id, "title": p.title, "difficulty": p.difficulty or "Easy", "solved": p.id in solved}
            for p in problems]


@app.get("/api/problems/{pid}")
def get_problem(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Problem, pid)
    if not p or (not p.published and user.role != "admin"):
        raise ApiError(404, "Problem not found")
    return {
        "id": p.id, "title": p.title, "statement": p.statement,
        "time_limit_sec": p.time_limit_sec, "memory_limit_mb": p.memory_limit_mb,
        "difficulty": p.difficulty or "Easy", "hint": p.hint,
        "time_complexity": p.time_complexity, "space_complexity": p.space_complexity,
        "samples": [{"position": t.position, "input": t.input, "expected_output": t.expected_output}
                    for t in p.tests if t.is_sample],
    }


# ---------- submissions ----------
class SubmitBody(BaseModel):
    problem_id: int
    language: str
    source_code: str
    claimed_time: str | None = Field(default=None, max_length=64)
    claimed_space: str | None = Field(default=None, max_length=64)


def sub_json(s: Submission) -> dict:
    total = len(json.loads(s.tokens)) if s.tokens else None
    passed = None
    if s.status == "done" and total is not None:
        if s.verdict == "AC":
            passed = total
        elif s.verdict in ("WA", "TLE", "RE") and s.failed_test:
            passed = s.failed_test - 1
    return {"id": s.id, "problem_id": s.problem_id, "language": s.language, "status": s.status,
            "verdict": s.verdict, "failed_test": s.failed_test, "runtime_ms": s.runtime_ms, "memory_kb": s.memory_kb,
            "message": s.message, "claimed_time": s.claimed_time, "claimed_space": s.claimed_space,
            "tests_passed": passed, "tests_total": total,
            "tests": json.loads(s.test_results) if s.test_results else [],
            "created_at": s.created_at.isoformat() if s.created_at else None}


def check_code(language: str, source_code: str):
    if language not in config.LANGUAGES:
        raise ApiError(400, "Language must be 'python' or 'cpp'")
    if not source_code.strip():
        raise ApiError(400, "Source code is empty")
    if len(source_code.encode()) > config.MAX_SOURCE_BYTES:
        raise ApiError(413, "Source code is larger than 64 KB")


def visible_problem(db: Session, pid: int, user: User) -> Problem:
    p = db.get(Problem, pid)
    if not p or (not p.published and user.role != "admin"):
        raise ApiError(404, "Problem not found")
    return p


@app.post("/api/submissions")
def submit(body: SubmitBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    check_code(body.language, body.source_code)
    p = visible_problem(db, body.problem_id, user)
    if not p.tests:
        raise ApiError(400, "Problem has no tests")
    sub = Submission(user_id=user.id, problem_id=p.id, language=body.language, source_code=body.source_code,
                      claimed_time=(body.claimed_time or "").strip() or None,
                      claimed_space=(body.claimed_space or "").strip() or None)
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
    return [{**sub_json(s), "problem_title": s.problem.title} for s in rows]


# ---------- run (try code on samples or custom input; nothing is stored) ----------
class RunBody(BaseModel):
    problem_id: int
    language: str
    source_code: str
    custom_input: str | None = None  # None = run the problem's sample tests


OUTPUT_CAP = 4000


def _cap(text: str | None) -> str:
    text = text or ""
    return text if len(text) <= OUTPUT_CAP else text[:OUTPUT_CAP] + "\n... (output truncated)"


@app.post("/api/run")
def run_code(body: RunBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    check_code(body.language, body.source_code)
    p = visible_problem(db, body.problem_id, user)
    if body.custom_input is not None:
        if len(body.custom_input.encode()) > config.MAX_SOURCE_BYTES:
            raise ApiError(413, "Custom input is larger than 64 KB")
        cases, positions = [(body.custom_input, None)], [None]
    else:
        samples = [t for t in p.tests if t.is_sample]
        if not samples:
            raise ApiError(400, "This problem has no sample tests. Use custom input instead.")
        cases, positions = [(t.input, t.expected_output) for t in samples], [t.position for t in samples]
    try:
        tokens = judge0.create_batch(body.source_code, body.language, cases, p.time_limit_sec, p.memory_limit_mb)
    except judge0.Judge0Error as e:
        raise ApiError(429 if e.throttled else 503, e.message)
    items = [{"t": tok, "pos": pos} for tok, pos in zip(tokens, positions)]
    return {"run_token": make_run_token(user.id, p.id, items, body.custom_input is not None)}


@app.get("/api/run")
def run_status(token: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = read_run_token(token, user)
    p = visible_problem(db, data["pid"], user)
    custom = bool(data.get("custom"))
    items = data["items"]
    try:
        results = judge0.get_batch([it["t"] for it in items], fields=judge0.RUN_FIELDS)
    except judge0.Judge0Error as e:
        return {"status": "pending", "message": e.message}
    # Only sample tests are ever echoed back; re-check is_sample in case an admin edited the problem.
    samples = {t.position: t for t in p.tests if t.is_sample}
    cases = []
    for it in items:
        r = results.get(it["t"])
        v = judging.verdict_for(r.get("status_id") if r else None)
        if v is None:
            return {"status": "pending", "message": None}
        if custom and v in ("AC", "WA"):
            v = "OK"  # no expected output to compare with
        case = {"position": it["pos"], "verdict": v, "runtime_ms": judging.ms(r), "memory_kb": judging.kb(r),
                "stdout": _cap(r.get("stdout")), "stderr": _cap(r.get("stderr"))}
        t = samples.get(it["pos"])
        if t is not None:
            case["input"], case["expected_output"] = t.input, t.expected_output
        cases.append(case)
    verdict = next((c["verdict"] for c in cases if c["verdict"] not in ("AC", "OK")), "OK" if custom else "AC")
    compile_output = None
    if verdict == "CE":
        compile_output = _cap(next((results[it["t"]].get("compile_output") for it in items
                                    if results.get(it["t"], {}).get("compile_output")), "Compilation failed"))
        for c in cases:
            c["stdout"] = c["stderr"] = ""
    message = "The judge failed to run this code. Try again." if verdict == "ERR" else None
    return {"status": "done", "custom": custom, "verdict": verdict, "compile_output": compile_output,
            "message": message, "cases": cases}


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
    difficulty: str = Field(default="Easy", pattern="^(Easy|Medium|Hard)$")
    hint: str | None = Field(default=None, max_length=5000)
    time_complexity: str | None = Field(default=None, max_length=64)
    space_complexity: str | None = Field(default=None, max_length=64)
    tests: list[TestIn] = Field(max_length=100)


def problem_admin_json(p: Problem) -> dict:
    return {"id": p.id, "title": p.title, "statement": p.statement, "time_limit_sec": p.time_limit_sec,
            "memory_limit_mb": p.memory_limit_mb, "published": p.published,
            "difficulty": p.difficulty or "Easy", "hint": p.hint,
            "time_complexity": p.time_complexity, "space_complexity": p.space_complexity,
            "tests": [{"input": t.input, "expected_output": t.expected_output, "is_sample": t.is_sample}
                      for t in p.tests]}


def apply_problem(p: Problem, body: ProblemIn):
    if body.published and not body.tests:
        raise ApiError(400, "A published problem needs at least one test")
    p.title, p.statement = body.title, body.statement
    p.time_limit_sec, p.memory_limit_mb, p.published = body.time_limit_sec, body.memory_limit_mb, body.published
    p.difficulty, p.hint = body.difficulty, body.hint
    p.time_complexity, p.space_complexity = body.time_complexity, body.space_complexity
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
