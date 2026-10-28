from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), default="participant")


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    statement: Mapped[str] = mapped_column(Text)
    time_limit_sec: Mapped[float] = mapped_column(Float, default=2.0)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty: Mapped[str | None] = mapped_column(String(8), default="Easy", nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)  # target for the problem
    space_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tests: Mapped[list["TestCase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="TestCase.position"
    )


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # not a pytest class
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    input: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer)
    problem: Mapped[Problem] = relationship(back_populates="tests")


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    language: Mapped[str] = mapped_column(String(8))
    source_code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8), default="pending")  # pending | done
    verdict: Mapped[str | None] = mapped_column(String(4), nullable=True)
    failed_test: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_time: Mapped[str | None] = mapped_column(String(64), nullable=True)  # self-reported, not measured
    claimed_space: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{position, token}]
    test_results: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{position, verdict, runtime_ms, memory_kb}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    problem: Mapped[Problem] = relationship()
