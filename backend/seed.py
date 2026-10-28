"""Idempotent seed: creates/updates tables, the admin from env vars, the sample problem and the 50-problem bank.

Run from the repo root:  python -m backend.seed
Safe to run repeatedly: problems are matched by title and updated in place; tests are only replaced if they changed.
"""
import os
import sys

from sqlalchemy import select

from backend.app.db import SessionLocal, init_db
from backend.app.models import Problem, TestCase, User
from backend.app.security import hash_password
from backend.problems import ALL
from backend.problems.base import build_tests

PROBLEM_TITLE = "A + B"
STATEMENT = """Read two integers A and B from standard input (separated by whitespace) and print their sum.

Input: two integers, |A|, |B| <= 10^9.
Output: A + B."""
HINT = "Python: a, b = map(int, input().split()). C++: use long long, since the sum can exceed the range of a 32-bit int."

TESTS = [
    ("1 2\n", "3\n", True),
    ("-5 5\n", "0\n", True),
    ("1000000000 1000000000\n", "2000000000\n", False),
    ("-1000000000 -1000000000\n", "-2000000000\n", False),
    ("0 0\n", "0\n", False),
]


def upsert(db, title, statement, difficulty, hint, tc, sc, tl, tests):
    p = db.scalar(select(Problem).where(Problem.title == title))
    created = p is None
    if created:
        p = Problem(title=title)
        db.add(p)
    p.statement, p.difficulty, p.hint = statement, difficulty, hint
    p.time_complexity, p.space_complexity = tc, sc
    p.time_limit_sec, p.memory_limit_mb, p.published = tl, 256, True
    new = [(i, o, s) for i, o, s in tests]
    old = [(t.input, t.expected_output, t.is_sample) for t in p.tests] if not created else None
    if old != new:
        p.tests = [TestCase(input=i, expected_output=o, is_sample=s, position=n + 1) for n, (i, o, s) in enumerate(new)]
    return "created" if created else ("updated tests" if old != new else "unchanged tests")


def main():
    init_db()
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password:
        sys.exit("ADMIN_USERNAME and ADMIN_PASSWORD must be set")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == username))
        if admin is None:
            db.add(User(username=username, password_hash=hash_password(password), role="admin"))
            print(f"created admin '{username}'")
        else:
            admin.role = "admin"  # an existing account's password is left unchanged
            print(f"admin '{username}' already exists")
        print("A + B:", upsert(db, PROBLEM_TITLE, STATEMENT, "Easy", HINT, "O(1)", "O(1)", 2.0, TESTS))
        counts = {}
        for pr in ALL:
            r = upsert(db, pr.title, pr.statement, pr.difficulty, pr.hint, pr.time, pr.space, pr.tl, build_tests(pr))
            counts[r] = counts.get(r, 0) + 1
        db.commit()
        print(f"problem bank ({len(ALL)}):", counts)


if __name__ == "__main__":
    main()
