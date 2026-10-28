import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import config, judge0
from .models import Problem, Submission, TestCase

LABELS = {"WA": "Wrong answer", "TLE": "Time limit exceeded", "RE": "Runtime error"}


def verdict_for(status_id: int | None) -> str | None:
    """Map a Judge0 status id to our verdict; None means still queued/running."""
    if status_id in (None, 1, 2):
        return None
    if status_id == 3:
        return "AC"
    if status_id == 4:
        return "WA"
    if status_id == 5:
        return "TLE"
    if status_id == 6:
        return "CE"
    if status_id in (7, 8, 9, 10, 11, 12):
        return "RE"
    return "ERR"  # 13 internal error, 14 exec format error, unknown


def ms(r: dict) -> int:
    try:
        return int(float(r.get("time") or 0) * 1000)
    except (TypeError, ValueError):
        return 0


def kb(r: dict) -> int:
    try:
        return int(r.get("memory") or 0)
    except (TypeError, ValueError):
        return 0


def finish(sub: Submission, verdict: str, failed_test=None, runtime_ms=None, memory_kb=None, message=None,
           results=None):
    sub.status = "done"
    sub.verdict = verdict
    sub.failed_test = failed_test
    sub.runtime_ms = runtime_ms
    sub.memory_kb = memory_kb
    sub.message = message
    sub.test_results = json.dumps(results) if results is not None else None


def start(db: Session, sub: Submission, problem: Problem, tests: list[TestCase]):
    """Send all tests to Judge0 without waiting. A failure is recorded as ERR (never as WA)."""
    try:
        tokens = judge0.create_batch(sub.source_code, sub.language, [(t.input, t.expected_output) for t in tests],
                                     problem.time_limit_sec, problem.memory_limit_mb)
        sub.tokens = json.dumps([{"position": t.position, "token": tok} for t, tok in zip(tests, tokens)])
    except judge0.Judge0Error as e:
        finish(sub, "ERR", message=e.message)
    db.commit()


def age_seconds(created: datetime) -> float:
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds()


def refresh(db: Session, sub: Submission):
    """Poll Judge0 for a pending submission; store the verdict once it is known."""
    if sub.status == "done":
        return
    age = age_seconds(sub.created_at)
    try:
        entries = json.loads(sub.tokens or "[]")
        if not entries:
            raise judge0.Judge0Error("No judge tokens were stored for this submission.")
        results = judge0.get_batch([e["token"] for e in entries])
    except judge0.Judge0Error as e:
        if age > config.STALE_SECONDS:
            finish(sub, "ERR", message=e.message)
        else:
            sub.message = e.message  # transient; stays pending, client keeps polling
        db.commit()
        return

    per_test = []  # tests up to (and including) the first failure, in position order
    for e in sorted(entries, key=lambda e: e["position"]):
        r = results.get(e["token"])
        v = verdict_for(r.get("status_id") if r else None)
        if v is None:
            # Earlier test still running, so the first failure is not known yet.
            if age > config.STALE_SECONDS:
                finish(sub, "ERR", message="The judge did not finish in time.")
                db.commit()
            elif sub.message:
                sub.message = None  # clear a stale transient error
                db.commit()
            return
        if v in ("CE", "ERR"):
            if v == "CE":
                msg = (r.get("compile_output") or r.get("message") or "Compilation failed")[:2000]
                finish(sub, "CE", message=msg)
            else:
                finish(sub, "ERR", message="The judge failed to run this submission. This is not a wrong answer.")
            db.commit()
            return
        per_test.append({"position": e["position"], "verdict": v, "runtime_ms": ms(r), "memory_kb": kb(r)})
        if v != "AC":
            finish(sub, v, e["position"], max(t["runtime_ms"] for t in per_test),
                   max(t["memory_kb"] for t in per_test), f"{LABELS[v]} on test {e['position']}", per_test)
            db.commit()
            return
    finish(sub, "AC", None, max(t["runtime_ms"] for t in per_test), max(t["memory_kb"] for t in per_test),
           None, per_test)
    db.commit()
