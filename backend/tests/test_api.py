"""Offline API tests: real app + SQLite + an in-process fake Judge0 (see fakejudge.py)."""
import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import bcrypt
import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from backend.app import config, db as dbmod, judge0, judging, security
from backend.app.db import Base, SessionLocal, init_db
from backend.app.main import app
from backend.app.models import Problem, Submission, TestCase, User
from backend.tests.fakejudge import FakeJudge

_real_gensalt = bcrypt.gensalt
PW = "password123"
HIDDEN_IN, HIDDEN_OUT = "HIDDEN_SENTINEL_IN\n", "HIDDEN_SENTINEL_OUT\n"


@pytest.fixture
def fake(monkeypatch):
    f = FakeJudge()
    monkeypatch.setattr(judge0, "_client", lambda: httpx.Client(transport=httpx.MockTransport(f.handler), timeout=5))
    return f


@pytest.fixture
def env(fake, monkeypatch):
    monkeypatch.setattr(bcrypt, "gensalt", lambda *a, **k: _real_gensalt(rounds=4))  # fast hashing in tests
    Base.metadata.drop_all(dbmod.engine)
    init_db()
    with SessionLocal() as db:
        db.add(User(username="boss", password_hash=security.hash_password(PW), role="admin"))
        p = Problem(title="Sum", statement="add", time_limit_sec=1, memory_limit_mb=64, published=True)
        p.tests = [TestCase(input="1 2\n", expected_output="3\n", is_sample=True, position=1),
                   TestCase(input="2 2\n", expected_output="4\n", is_sample=True, position=2),
                   TestCase(input=HIDDEN_IN, expected_output=HIDDEN_OUT, is_sample=False, position=3),
                   TestCase(input="5 5\n", expected_output="10\n", is_sample=False, position=4)]
        q = Problem(title="Second", statement="x", published=True)
        q.tests = [TestCase(input="1\n", expected_output="1\n", is_sample=True, position=1)]
        u = Problem(title="Draft", statement="secret draft", published=False)
        u.tests = [TestCase(input="9\n", expected_output="9\n", is_sample=True, position=1)]
        db.add_all([p, q, u])
        db.commit()
        ids = SimpleNamespace(p=p.id, q=q.id, u=u.id)
    admin, alice, bob = TestClient(app), TestClient(app), TestClient(app)
    assert admin.post("/api/auth/login", json={"username": "boss", "password": PW}).status_code == 200
    for c, n in ((alice, "alice"), (bob, "bob_1")):
        assert c.post("/api/auth/register", json={"username": n, "password": PW}).status_code == 200
    return SimpleNamespace(admin=admin, alice=alice, bob=bob, anon=TestClient(app), fake=fake, **vars(ids))


def submit(c, pid, src="#FAKE status=3", lang="python", **extra):
    r = c.post("/api/submissions", json={"problem_id": pid, "language": lang, "source_code": src, **extra})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def poll(c, sid):
    r = c.get(f"/api/submissions/{sid}")
    assert r.status_code == 200, r.text
    return r.json()


def run(c, pid, src="#FAKE status=3 stdout=expected", **extra):
    return c.post("/api/run", json={"problem_id": pid, "language": "python", "source_code": src, **extra})


def run_result(c, token):
    return c.get("/api/run", params={"token": token})


def age(sid, minutes):
    with SessionLocal() as db:
        s = db.get(Submission, sid)
        s.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        db.commit()


# ------------------------------------------------------------------ auth
@pytest.mark.parametrize("name", ["ab", "x" * 33, "bad name", "ünï", "a-b", "<script>", ""])
def test_register_rejects_bad_usernames(env, name):
    r = env.anon.post("/api/auth/register", json={"username": name, "password": PW})
    assert r.status_code == 400 and "error" in r.json()


@pytest.mark.parametrize("pw,ok", [("x" * 7, False), ("x" * 8, True), ("x" * 72, True), ("x" * 73, False),
                                   ("é" * 36, True), ("é" * 37, False)])
def test_register_password_length_in_bytes(env, pw, ok):
    r = env.anon.post("/api/auth/register", json={"username": "pwuser", "password": pw})
    assert (r.status_code == 200) == ok, r.text


def test_long_password_prefix_cannot_log_in(env):
    env.anon.post("/api/auth/register", json={"username": "longpw", "password": "a" * 72})
    r = TestClient(app).post("/api/auth/login", json={"username": "longpw", "password": "a" * 72 + "zzz"})
    assert r.status_code in (400, 401)


def test_register_ignores_role_field(env):
    r = env.anon.post("/api/auth/register", json={"username": "sneaky", "password": PW, "role": "admin"})
    assert r.json() == {"username": "sneaky", "role": "participant"}
    assert env.anon.get("/api/admin/problems").status_code == 403


def test_usernames_are_case_insensitive(env):
    assert env.anon.post("/api/auth/register", json={"username": "ALICE", "password": PW}).status_code == 409
    r = TestClient(app).post("/api/auth/login", json={"username": "Alice", "password": PW})
    assert r.status_code == 200 and r.json()["username"] == "alice"


def test_login_failures_do_not_reveal_which_part_was_wrong(env):
    a = TestClient(app).post("/api/auth/login", json={"username": "alice", "password": "wrong-password"})
    b = TestClient(app).post("/api/auth/login", json={"username": "nobody_here", "password": "wrong-password"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


@pytest.mark.parametrize("body", [None, "not json", {"username": "alice"}, {"password": PW}, {"username": 5, "password": PW}])
def test_malformed_auth_bodies(env, body):
    if body is None:
        r = env.anon.post("/api/auth/login")
    elif isinstance(body, str):
        r = env.anon.post("/api/auth/login", content=body, headers={"Content-Type": "application/json"})
    else:
        r = env.anon.post("/api/auth/login", json=body)
    assert r.status_code == 400 and set(r.json()) == {"error"}


def test_cookie_flags(env, monkeypatch):
    r = TestClient(app).post("/api/auth/login", json={"username": "alice", "password": PW})
    c = r.headers["set-cookie"].lower()
    assert "httponly" in c and "samesite=lax" in c and "secure" not in c
    monkeypatch.setattr(config, "IS_PROD", True)
    r = TestClient(app).post("/api/auth/login", json={"username": "alice", "password": PW})
    assert "secure" in r.headers["set-cookie"].lower()


def test_logout_and_bad_cookies(env):
    assert env.alice.post("/api/auth/logout").status_code == 200
    assert env.alice.get("/api/auth/me").status_code == 401
    c = TestClient(app)
    for tok in ["garbage", jwt.encode({"sub": "1"}, "wrong-key", algorithm="HS256"),
                jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                           config.SECRET_KEY, algorithm="HS256"),
                jwt.encode({"sub": "99999"}, config.SECRET_KEY, algorithm="HS256"),
                jwt.encode({"sub": "abc"}, config.SECRET_KEY, algorithm="HS256"),
                jwt.encode({"nosub": 1}, config.SECRET_KEY, algorithm="HS256")]:
        c.cookies.set(config.COOKIE_NAME, tok)
        assert c.get("/api/auth/me").status_code == 401, tok


def test_legacy_session_token_without_typ_still_works(env):
    with SessionLocal() as db:
        uid = db.query(User).filter_by(username="alice").one().id
    c = TestClient(app)
    c.cookies.set(config.COOKIE_NAME, jwt.encode({"sub": str(uid)}, config.SECRET_KEY, algorithm="HS256"))
    assert c.get("/api/auth/me").json()["username"] == "alice"


def test_unknown_route_and_method_return_json_errors(env):
    r = env.alice.get("/api/nope")
    assert r.status_code == 404 and "error" in r.json()
    r = env.alice.delete("/api/problems")
    assert r.status_code == 405 and "error" in r.json()


def test_every_api_needs_login(env):
    for method, path in [("get", "/api/problems"), ("get", f"/api/problems/{env.p}"), ("get", "/api/submissions"),
                         ("get", "/api/submissions/1"), ("post", "/api/submissions"), ("get", "/api/leaderboard"),
                         ("post", "/api/run"), ("get", "/api/run?token=x"), ("get", "/api/admin/problems")]:
        r = getattr(env.anon, method)(path, **({"json": {}} if method == "post" else {}))
        assert r.status_code == 401, (method, path, r.status_code)


# ------------------------------------------------------------------ problems & hidden tests
def test_participant_never_sees_hidden_tests_or_drafts(env):
    lst = env.alice.get("/api/problems").json()
    assert {p["title"] for p in lst} == {"Sum", "Second"}
    d = env.alice.get(f"/api/problems/{env.p}")
    assert d.status_code == 200 and len(d.json()["samples"]) == 2
    assert "HIDDEN_SENTINEL" not in d.text
    assert env.alice.get(f"/api/problems/{env.u}").status_code == 404
    assert env.admin.get(f"/api/problems/{env.u}").status_code == 200
    for bad in ["999999", "-1", "0"]:
        assert env.alice.get(f"/api/problems/{bad}").status_code == 404
    assert env.alice.get("/api/problems/abc").status_code == 400


def test_unpublished_problem_blocked_everywhere_for_participants(env):
    assert submit(env.admin, env.u)
    r = env.alice.post("/api/submissions", json={"problem_id": env.u, "language": "python", "source_code": "x"})
    assert r.status_code == 404
    assert run(env.alice, env.u).status_code == 404
    assert run(env.admin, env.u).status_code == 200


# ------------------------------------------------------------------ submission validation
@pytest.mark.parametrize("lang", ["java", "PYTHON", "", "c++"])
def test_bad_language(env, lang):
    r = env.alice.post("/api/submissions", json={"problem_id": env.p, "language": lang, "source_code": "x"})
    assert r.status_code == 400


@pytest.mark.parametrize("src,code", [
    ("", 400), ("   \n\t", 400),
    ("x" * config.MAX_SOURCE_BYTES, 200), ("x" * (config.MAX_SOURCE_BYTES + 1), 413),
    ("é" * (config.MAX_SOURCE_BYTES // 2), 200), ("é" * (config.MAX_SOURCE_BYTES // 2) + "x", 413),
], ids=["empty", "whitespace", "exactly-64KB", "64KB+1", "multibyte-64KB", "multibyte-64KB+1"])
def test_source_size_limits_are_in_bytes(env, src, code):
    r = env.alice.post("/api/submissions", json={"problem_id": env.p, "language": "python", "source_code": src})
    assert r.status_code == code, r.text[:200]


@pytest.mark.parametrize("body", [{"language": "python", "source_code": "x"},
                                  {"problem_id": "abc", "language": "python", "source_code": "x"},
                                  {"problem_id": 1, "language": "python"},
                                  {"problem_id": 1, "language": "python", "source_code": "x", "claimed_time": "x" * 65}])
def test_submission_body_validation(env, body):
    r = env.alice.post("/api/submissions", json=body)
    assert r.status_code == 400 and "error" in r.json()


def test_submit_missing_problem_and_problem_without_tests(env):
    r = env.alice.post("/api/submissions", json={"problem_id": 999, "language": "python", "source_code": "x"})
    assert r.status_code == 404
    pid = env.admin.post("/api/admin/problems", json={"title": "Empty", "statement": "s", "tests": []}).json()["id"]
    r = env.admin.post("/api/submissions", json={"problem_id": pid, "language": "python", "source_code": "x"})
    assert r.status_code == 400


# ------------------------------------------------------------------ verdicts
def test_accepted_reports_runtime_memory_and_per_test_results(env):
    sid = submit(env.alice, env.p, "#FAKE status=3 time=0.123 memory=2048", claimed_time=" O(1) ", claimed_space="")
    s = poll(env.alice, sid)
    assert (s["status"], s["verdict"], s["runtime_ms"], s["memory_kb"]) == ("done", "AC", 123, 2048)
    assert s["tests_passed"] == s["tests_total"] == 4 and len(s["tests"]) == 4
    assert s["claimed_time"] == "O(1)" and s["claimed_space"] is None
    assert s["failed_test"] is None and s["language"] == "python"


def test_wrong_answer_reports_first_failing_test_only(env):
    s = poll(env.alice, submit(env.alice, env.p, "#FAKE status=3,3,4,3"))
    assert (s["verdict"], s["failed_test"], s["tests_passed"], s["tests_total"]) == ("WA", 3, 2, 4)
    assert s["message"] == "Wrong answer on test 3" and len(s["tests"]) == 3
    assert "HIDDEN_SENTINEL" not in json.dumps(s)


@pytest.mark.parametrize("status,verdict", [(5, "TLE"), (7, "RE"), (11, "RE"), (12, "RE"), (13, "ERR"),
                                            (14, "ERR"), (99, "ERR")])
def test_status_mapping(env, status, verdict):
    s = poll(env.alice, submit(env.alice, env.p, f"#FAKE status={status}"))
    assert s["verdict"] == verdict
    if verdict == "ERR":
        assert "not a wrong answer" in s["message"] and s["failed_test"] is None


def test_compile_error_shows_compiler_output(env):
    s = poll(env.alice, submit(env.alice, env.p, "#FAKE status=6 compile=main.cpp:1:error", lang="cpp"))
    assert s["verdict"] == "CE" and "main.cpp:1:error" in s["message"] and s["failed_test"] is None
    assert env.fake.created_items[-1]["compiler_options"] == "-std=c++17"


def test_earlier_test_pending_blocks_verdict_even_if_later_failed(env):
    sid = submit(env.alice, env.p, "#FAKE status=3,3,4,3 hold=0")
    assert poll(env.alice, sid)["status"] == "pending"
    env.fake.release()
    assert poll(env.alice, sid)["verdict"] == "WA"


def test_failure_decided_without_waiting_for_later_tests(env):
    s = poll(env.alice, submit(env.alice, env.p, "#FAKE status=4 hold=3"))
    assert (s["verdict"], s["failed_test"]) == ("WA", 1)


def test_done_submissions_are_not_polled_again(env):
    sid = submit(env.alice, env.p)
    poll(env.alice, sid)
    n = env.fake.gets
    poll(env.alice, sid)
    poll(env.alice, sid)
    assert env.fake.gets == n


def test_submission_path_never_requests_program_output(env):
    poll(env.alice, submit(env.alice, env.p, "#FAKE status=3,4"))
    assert env.fake.get_fields and all("stdout" not in f and "stderr" not in f for f in env.fake.get_fields)


@pytest.mark.parametrize("mode,text", [(429, "rate limiting"), (500, "rejected"), (503, "rejected"),
                                       ("disconnect", "reach"), ("badjson", "unexpected"),
                                       ("notoken", "could not accept"), ("short", "unexpected")])
def test_judge_failure_on_create_is_err_not_wrong_answer(env, mode, text):
    env.fake.create_mode = mode
    s = poll(env.alice, submit(env.alice, env.p))
    assert s["status"] == "done" and s["verdict"] == "ERR" and text in s["message"]
    assert s["tests_total"] is None and s["tests_passed"] is None


@pytest.mark.parametrize("mode", [429, 500, "disconnect", "badjson"])
def test_judge_failure_while_polling_stays_pending_then_recovers(env, mode):
    sid = submit(env.alice, env.p)
    env.fake.get_mode = mode
    s = poll(env.alice, sid)
    assert s["status"] == "pending" and s["message"]
    env.fake.get_mode = None
    s = poll(env.alice, sid)
    assert s["verdict"] == "AC" and s["message"] is None


def test_stale_submissions_become_err(env):
    sid = submit(env.alice, env.p, "#FAKE status=3 hold=0")
    age(sid, 10)
    s = poll(env.alice, sid)
    assert s["verdict"] == "ERR" and "did not finish" in s["message"]
    sid = submit(env.alice, env.p)
    env.fake.get_mode = 500
    age(sid, 10)
    assert poll(env.alice, sid)["verdict"] == "ERR"


def test_token_unknown_to_judge_counts_as_pending(env):
    sid = submit(env.alice, env.p)
    env.fake.subs.clear()
    assert poll(env.alice, sid)["status"] == "pending"


# ------------------------------------------------------------------ ownership & history
def test_submission_privacy(env):
    sid = submit(env.alice, env.p)
    assert env.bob.get(f"/api/submissions/{sid}").status_code == 404
    assert env.bob.get("/api/submissions/999999").status_code == 404
    assert env.admin.get(f"/api/submissions/{sid}").status_code == 200
    assert env.bob.get("/api/submissions").json() == []


def test_history_is_newest_first_and_marks_solved(env):
    a = submit(env.alice, env.p, "#FAKE status=4")
    b = submit(env.alice, env.p, "#FAKE status=3")
    c = submit(env.alice, env.q, "#FAKE status=6", lang="cpp")
    for sid in (a, b, c):
        poll(env.alice, sid)
    hist = env.alice.get("/api/submissions").json()
    assert [h["id"] for h in hist] == [c, b, a]
    assert hist[0]["problem_title"] == "Second" and hist[0]["language"] == "cpp"
    assert "source_code" not in hist[0]
    solved = {p["title"]: p["solved"] for p in env.alice.get("/api/problems").json()}
    assert solved == {"Sum": True, "Second": False}


# ------------------------------------------------------------------ leaderboard
def test_leaderboard_ordering_and_counting_rules(env):
    T = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t = lambda m: T + timedelta(minutes=m)  # noqa: E731
    with SessionLocal() as db:
        users = {}
        for n in ["u1", "u2", "u3", "u4", "u5"]:
            u = User(username=n, password_hash="x", role="participant")
            db.add(u)
            db.flush()
            users[n] = u.id
        admin_id = db.query(User).filter_by(username="boss").one().id
        rows = [
            ("u1", env.p, "WA", 1), ("u1", env.p, "AC", 2), ("u1", env.q, "AC", 3),
            ("u2", env.p, "AC", 1), ("u2", env.q, "AC", 5),
            ("u3", env.p, "CE", 0), ("u3", env.p, "ERR", 0), ("u3", env.p, "AC", 1),
            ("u3", env.q, "TLE", 2), ("u3", env.q, "RE", 3),
            ("u4", env.p, "AC", 0), ("u4", env.p, "WA", 9),
        ]
        for n, pid, v, m in rows:
            db.add(Submission(user_id=users[n], problem_id=pid, language="python", source_code="x", status="done",
                              verdict=v, created_at=t(m)))
        db.add(Submission(user_id=users["u5"], problem_id=env.p, language="python", source_code="x",
                          status="pending", verdict=None, created_at=t(0)))
        db.add(Submission(user_id=admin_id, problem_id=env.p, language="python", source_code="x", status="done",
                          verdict="AC", created_at=t(0)))
        db.commit()
    lb = env.alice.get("/api/leaderboard").json()
    # u2 beats u1 on fewer wrong attempts; u4 beats u3 on earlier AC; CE/ERR, wrongs after AC, wrongs on
    # unsolved problems, pending submissions and the admin are not counted; zero-solve ties sort by name.
    assert [(r["username"], r["solved"], r["wrong"]) for r in lb] == [
        ("u2", 2, 0), ("u1", 2, 1), ("u4", 1, 0), ("u3", 1, 0), ("alice", 0, 0), ("bob_1", 0, 0), ("u5", 0, 0)]
    assert [r["rank"] for r in lb] == list(range(1, len(lb) + 1))
    assert "boss" not in {r["username"] for r in lb}
    assert {"u5", "alice", "bob_1"} <= {r["username"] for r in lb}


def test_runs_and_judge_errors_do_not_touch_leaderboard(env):
    env.fake.create_mode = 429
    poll(env.alice, submit(env.alice, env.p))
    env.fake.create_mode = None
    tok = run(env.alice, env.p, "#FAKE status=4").json()["run_token"]
    run_result(env.alice, tok)
    row = next(r for r in env.alice.get("/api/leaderboard").json() if r["username"] == "alice")
    assert (row["solved"], row["wrong"]) == (0, 0)


# ------------------------------------------------------------------ run
def test_run_on_samples(env):
    r = run(env.alice, env.p)
    assert r.status_code == 200
    out = run_result(env.alice, r.json()["run_token"]).json()
    assert out["status"] == "done" and out["verdict"] == "AC" and len(out["cases"]) == 2
    assert {"position": 1, "input": "1 2\n", "expected_output": "3\n", "stdout": "3\n"}.items() <= out["cases"][0].items()
    assert "HIDDEN_SENTINEL" not in json.dumps(out)
    assert all("HIDDEN" not in judge0._unb64(i["stdin"]) for i in env.fake.created_items)
    assert len(env.fake.created_items) == 2
    assert env.alice.get("/api/submissions").json() == []


def test_run_wrong_answer_and_pending(env):
    tok = run(env.alice, env.p, "#FAKE status=3,4 stdout=oops hold=1").json()["run_token"]
    assert run_result(env.alice, tok).json()["status"] == "pending"
    env.fake.release()
    out = run_result(env.alice, tok).json()
    assert out["verdict"] == "WA" and out["cases"][1]["verdict"] == "WA" and out["cases"][1]["stdout"] == "oops"


def test_run_custom_input(env):
    r = run(env.alice, env.p, "#FAKE status=3 stdout=echo", custom_input="hello world\n")
    out = run_result(env.alice, r.json()["run_token"]).json()
    assert out["custom"] and out["verdict"] == "OK"
    assert out["cases"][0]["stdout"] == "hello world\n" and "expected_output" not in out["cases"][0]
    assert "expected_output" not in env.fake.created_items[-1]
    r = run(env.alice, env.p, "#FAKE status=3", custom_input="")
    assert r.status_code == 200
    r = run(env.alice, env.p, custom_input="x" * (config.MAX_SOURCE_BYTES + 1))
    assert r.status_code == 413


def test_run_compile_error_and_runtime_error_output(env):
    out = run_result(env.alice, run(env.alice, env.p, "#FAKE status=6 compile=bad_syntax").json()["run_token"]).json()
    assert out["verdict"] == "CE" and "bad_syntax" in out["compile_output"]
    out = run_result(env.alice, run(env.alice, env.p, "#FAKE status=11 stderr=Traceback").json()["run_token"]).json()
    assert out["verdict"] == "RE" and out["cases"][0]["stderr"] == "Traceback"


def test_run_output_is_truncated(env):
    big = "y" * 10000
    env.fake.subs.clear()
    tok = run(env.alice, env.p, f"#FAKE status=3 stdout={big}").json()["run_token"]
    out = run_result(env.alice, tok).json()
    assert len(out["cases"][0]["stdout"]) < 4100 and "truncated" in out["cases"][0]["stdout"]


def test_run_throttled_or_judge_down(env):
    env.fake.create_mode = 429
    r = run(env.alice, env.p)
    assert r.status_code == 429 and "rate limiting" in r.json()["error"]
    env.fake.create_mode = "disconnect"
    assert run(env.alice, env.p).status_code == 503
    env.fake.create_mode = None
    tok = run(env.alice, env.p).json()["run_token"]
    env.fake.get_mode = 500
    out = run_result(env.alice, tok).json()
    assert out["status"] == "pending" and out["message"]


def test_run_problem_without_samples(env):
    pid = env.admin.post("/api/admin/problems", json={
        "title": "NoSamples", "statement": "s", "published": True,
        "tests": [{"input": HIDDEN_IN, "expected_output": HIDDEN_OUT, "is_sample": False}]}).json()["id"]
    assert run(env.alice, pid).status_code == 400
    out = run_result(env.alice, run(env.alice, pid, "#FAKE status=3", custom_input="1\n").json()["run_token"]).json()
    assert out["verdict"] == "OK" and "HIDDEN_SENTINEL" not in json.dumps(out)


def test_run_token_security(env, monkeypatch):
    tok = run(env.alice, env.p).json()["run_token"]
    assert run_result(env.bob, tok).status_code == 404
    assert run_result(env.alice, tok[:-3] + ("AAA" if not tok.endswith("AAA") else "BBB")).status_code == 400
    assert run_result(env.alice, "not-a-token").status_code == 400
    session = env.alice.cookies.get(config.COOKIE_NAME)
    assert run_result(env.alice, session).status_code == 400
    c = TestClient(app)
    c.cookies.set(config.COOKIE_NAME, tok)
    assert c.get("/api/auth/me").status_code == 401
    forged = jwt.encode({**jwt.decode(tok, options={"verify_signature": False}), "uid": 1}, "wrong-key",
                        algorithm="HS256")
    assert run_result(env.alice, forged).status_code == 400
    monkeypatch.setattr(security, "RUN_TOKEN_MINUTES", -1)
    expired = run(env.alice, env.p).json()["run_token"]
    assert run_result(env.alice, expired).status_code == 410


def test_run_never_reveals_test_that_became_hidden(env):
    tok = run(env.alice, env.p).json()["run_token"]
    with SessionLocal() as db:
        for t in db.get(Problem, env.p).tests:
            if t.position == 1:
                t.input, t.expected_output, t.is_sample = HIDDEN_IN, HIDDEN_OUT, False
        db.commit()
    out = run_result(env.alice, tok).json()
    assert "HIDDEN_SENTINEL_OUT" not in json.dumps({k: v for k, v in out.items()} | {"cases": [
        {k: v for k, v in c.items() if k != "stdout"} for c in out["cases"]]})
    assert "input" not in out["cases"][0]


# ------------------------------------------------------------------ admin
def test_admin_endpoints_require_admin(env):
    body = {"title": "t", "statement": "s", "tests": []}
    for c, code in ((env.anon, 401), (env.alice, 403)):
        assert c.get("/api/admin/problems").status_code == code
        assert c.post("/api/admin/problems", json=body).status_code == code
        assert c.put(f"/api/admin/problems/{env.p}", json=body).status_code == code


@pytest.mark.parametrize("patch", [{"difficulty": "Impossible"}, {"time_limit_sec": 0}, {"time_limit_sec": 16},
                                   {"memory_limit_mb": 8}, {"title": ""}, {"title": "x" * 201},
                                   {"published": True, "tests": []},
                                   {"tests": [{"input": "1", "expected_output": "1"}] * 101}])
def test_admin_validation(env, patch):
    body = {"title": "t", "statement": "s", "tests": [{"input": "1", "expected_output": "1", "is_sample": True}]}
    r = env.admin.post("/api/admin/problems", json={**body, **patch})
    assert r.status_code == 400 and "error" in r.json()


def test_admin_update_replaces_tests_and_can_unpublish(env):
    assert env.admin.put("/api/admin/problems/999999", json={"title": "t", "statement": "s", "tests": []}).status_code == 404
    body = {"title": "Sum v2", "statement": "s", "published": False, "difficulty": "Hard", "hint": "h",
            "time_complexity": "O(1)", "space_complexity": "O(1)",
            "tests": [{"input": "a", "expected_output": "b", "is_sample": True},
                      {"input": "c", "expected_output": "d"}]}
    out = env.admin.put(f"/api/admin/problems/{env.p}", json=body).json()
    assert len(out["tests"]) == 2 and out["difficulty"] == "Hard"
    with SessionLocal() as db:
        assert [t.position for t in db.get(Problem, env.p).tests] == [1, 2]
    assert env.alice.get(f"/api/problems/{env.p}").status_code == 404


# ------------------------------------------------------------------ logging & crashes
def test_no_secrets_in_logs(env, capsys, caplog):
    TestClient(app).post("/api/auth/register", json={"username": "logger", "password": "PW_SENTINEL_123"})
    sid = submit(env.alice, env.p, "#FAKE status=4\n# SRC_SENTINEL")
    poll(env.alice, sid)
    out = capsys.readouterr()
    logs = out.out + out.err + caplog.text
    assert "PW_SENTINEL" not in logs and "SRC_SENTINEL" not in logs and "HIDDEN_SENTINEL" not in logs


def test_unhandled_errors_are_generic_json(env, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("SRC_SENTINEL details")
    monkeypatch.setattr(judging, "refresh", boom)
    sid = submit(env.alice, env.p)
    c = TestClient(app, raise_server_exceptions=False)
    c.cookies.set(config.COOKIE_NAME, env.alice.cookies.get(config.COOKIE_NAME))
    r = c.get(f"/api/submissions/{sid}")
    assert r.status_code == 500 and r.json() == {"error": "Internal server error"}
    assert "SRC_SENTINEL" not in capsys.readouterr().out


# ------------------------------------------------------------------ seed & migrations
def test_seed_is_idempotent_and_keeps_existing_admin_password(env, monkeypatch):
    from backend import seed
    monkeypatch.setenv("ADMIN_USERNAME", "boss")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-different-password")
    with SessionLocal() as db:
        db.query(User).filter_by(username="boss").one().role = "participant"
        db.commit()
    seed.main()
    seed.main()
    with SessionLocal() as db:
        assert db.query(Problem).filter_by(title="Two Sum").count() == 1
        assert db.query(User).filter_by(username="boss").one().role == "admin"
    assert TestClient(app).post("/api/auth/login", json={"username": "boss", "password": PW}).status_code == 200
    r = TestClient(app).post("/api/auth/login", json={"username": "boss", "password": "a-different-password"})
    assert r.status_code == 401


def _old_schema_engine(path):
    if os.path.exists(path):
        os.remove(path)
    eng = create_engine(f"sqlite:///{path}")
    with eng.begin() as c:
        for stmt in [
            "create table users(id integer primary key,username varchar(32),password_hash varchar(100),role varchar(16))",
            "create table problems(id integer primary key,title varchar(200),statement text,time_limit_sec float,"
            "memory_limit_mb integer,published boolean)",
            "create table test_cases(id integer primary key,problem_id integer,input text,expected_output text,"
            "is_sample boolean,position integer)",
            "create table submissions(id integer primary key,user_id integer,problem_id integer,language varchar(8),"
            "source_code text,status varchar(8),verdict varchar(4),failed_test integer,runtime_ms integer,"
            "memory_kb integer,message text,tokens text,created_at datetime)",
        ]:
            c.execute(text(stmt))
    return eng


def test_migration_adds_all_new_columns(monkeypatch):
    eng = _old_schema_engine("old_schema.db")
    monkeypatch.setattr(dbmod, "engine", eng)
    init_db()
    init_db()
    cols = {c["name"] for c in inspect(eng).get_columns("submissions")}
    assert {"claimed_time", "claimed_space", "test_results"} <= cols
    assert {"difficulty", "hint"} <= {c["name"] for c in inspect(eng).get_columns("problems")}
    eng.dispose()
    os.remove("old_schema.db")


def test_migration_survives_losing_a_race(monkeypatch):
    import sqlalchemy
    eng = _old_schema_engine("race_schema.db")
    with eng.begin() as c:
        c.execute(text("ALTER TABLE submissions ADD COLUMN test_results TEXT"))  # "other instance" got there first
    real = sqlalchemy.inspect
    calls = {"n": 0}

    class Stale:
        def __init__(self, i):
            self.i = i

        def get_columns(self, table):
            return [c for c in self.i.get_columns(table) if c["name"] != "test_results"]

    def fake_inspect(x):
        calls["n"] += 1
        return Stale(real(x)) if calls["n"] == 1 else real(x)

    monkeypatch.setattr(dbmod, "engine", eng)
    monkeypatch.setattr(sqlalchemy, "inspect", fake_inspect)
    init_db()  # must not raise
    monkeypatch.setattr(sqlalchemy, "inspect", real)
    assert "test_results" in {c["name"] for c in inspect(eng).get_columns("submissions")}
    eng.dispose()
    os.remove("race_schema.db")
