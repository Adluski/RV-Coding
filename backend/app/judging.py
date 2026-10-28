import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import config, judge0
from .models import Problem, Submission, TestCase


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


def finish(sub: Submission, verdict: str, failed_test=None, runtime_ms=None, memory_kb=None, message=None):
    sub.status = "done"
    sub.verdict = verdict
    sub.failed_test = failed_test
    sub.runtime_ms = runtime_ms
    sub.memory_kb = memory_kb
    sub.message = message


def start(db: Session, sub: Submission, problem: Problem, tests: list[TestCase]):
    """Send all tests to Judge0 without waiting. A failure is recorded as ERR (never as WA)."""
    try:
        tokens = judge0.create_batch(sub.source_code, sub.language, tests, problem.time_limit_sec,
                                     problem.memory_limit_mb)
        sub.tokens = json.dumps([{"position": t.position, "token": tok} for t, tok in zip(tests, tokens)])
    except judge0.Judge0Error as e:
        finish(sub, "ERR", message=e.message)
    db.commit()


def _age_seconds(sub: Submission) -> float:
    created = sub.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds()


def refresh(db: Session, sub: Submission):
    """Poll Judge0 for a pending submission; store the verdict once it is known."""
    if sub.status == "done":
        return
    age = _age_seconds(sub)
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

    max_time, max_mem = 0.0, 0
    for e in sorted(entries, key=lambda e: e["position"]):
        r = results.get(e["token"])
        v = verdict_for(r.get("status_id") if r else None)
        if v is None:
            # Earlier test still running, so the first failure is not known yet.
            if age > config.STALE_SECONDS:
                finish(sub, "ERR", message="The judge did not finish in time.")
                db.commit()
            return
        max_time = max(max_time, float(r.get("time") or 0))
        max_mem = max(max_mem, int(r.get("memory") or 0))
        if v == "AC":
            continue
        if v == "CE":
            msg = (r.get("compile_output") or r.get("message") or "Compilation failed")[:500]
            finish(sub, "CE", message=msg)
        elif v == "ERR":
            finish(sub, "ERR", message="The judge failed to run this submission. This is not a wrong answer.")
        else:
            label = {"WA": "Wrong answer", "TLE": "Time limit exceeded", "RE": "Runtime error"}[v]
            finish(sub, v, e["position"], int(max_time * 1000), max_mem, f"{label} on test {e['position']}")
        db.commit()
        return
    finish(sub, "AC", None, int(max_time * 1000), max_mem, None)
    db.commit()
