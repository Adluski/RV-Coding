"""Idempotent seed: creates tables, the admin from env vars, and a sample problem.

Run from the repo root:  python -m backend.seed
"""
import os
import sys

from sqlalchemy import select

from backend.app.db import Base, SessionLocal, engine
from backend.app.models import Problem, TestCase, User
from backend.app.security import hash_password

PROBLEM_TITLE = "A + B"
STATEMENT = """Read two integers A and B from standard input (separated by whitespace) and print their sum.

Input: two integers, |A|, |B| <= 10^9.
Output: A + B."""

TESTS = [
    ("1 2\n", "3\n", True),
    ("-5 5\n", "0\n", True),
    ("1000000000 1000000000\n", "2000000000\n", False),
    ("-1000000000 -1000000000\n", "-2000000000\n", False),
    ("0 0\n", "0\n", False),
]


def main():
    Base.metadata.create_all(engine)
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
        if db.scalar(select(Problem).where(Problem.title == PROBLEM_TITLE)) is None:
            p = Problem(title=PROBLEM_TITLE, statement=STATEMENT, time_limit_sec=2.0, memory_limit_mb=256,
                        published=True)
            p.tests = [TestCase(input=i, expected_output=o, is_sample=s, position=n + 1)
                       for n, (i, o, s) in enumerate(TESTS)]
            db.add(p)
            print("created sample problem")
        db.commit()


if __name__ == "__main__":
    main()
