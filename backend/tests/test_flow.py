"""End-to-end flow against the real hosted Judge0 (set SKIP_JUDGE0=1 to skip those parts)."""
import os
import time

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_flow.db"
os.environ["ADMIN_USERNAME"] = "root_admin"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"

from fastapi.testclient import TestClient  # noqa: E402

from backend import seed  # noqa: E402
from backend.app.db import Base, engine  # noqa: E402
from backend.app.main import app  # noqa: E402

LIVE = not os.environ.get("SKIP_JUDGE0")


@pytest.fixture(scope="module")
def clients():
    Base.metadata.drop_all(engine)
    seed.main()
    seed.main()  # idempotent
    admin, alice, bob = (TestClient(app) for _ in range(3))
    assert admin.post("/api/auth/login", json={"username": "root_admin", "password": "admin-pass-123"}).status_code == 200
    for c, n in ((alice, "alice"), (bob, "bobby")):
        r = c.post("/api/auth/register", json={"username": n, "password": "password123"})
        assert r.json() == {"username": n, "role": "participant"}
    yield admin, alice, bob
    engine.dispose()
    try:
        os.remove("test_flow.db")
    except OSError:
        pass


def wait(client, sid, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        r = client.get(f"/api/submissions/{sid}").json()
        if r["status"] == "done":
            return r
        time.sleep(2)
    raise AssertionError("submission never finished")


def submit(client, pid, lang, code):
    r = client.post("/api/submissions", json={"problem_id": pid, "language": lang, "source_code": code})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_auth_rules(clients):
    admin, alice, _ = clients
    anon = TestClient(app)
    assert anon.get("/api/problems").status_code == 401
    assert anon.get("/api/problems").json() == {"error": "Not signed in"}
    assert alice.post("/api/admin/problems", json={"title": "x", "statement": "y", "tests": []}).status_code == 403
    assert anon.post("/api/auth/register", json={"username": "alice", "password": "password123"}).status_code == 409
    assert anon.post("/api/auth/login", json={"username": "alice", "password": "wrong-pass"}).status_code == 401
    me = alice.get("/api/auth/me").json()
    assert me == {"username": "alice", "role": "participant"}
    r = anon.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_hidden_tests_not_exposed(clients):
    _, alice, _ = clients
    probs = alice.get("/api/problems").json()
    assert probs and set(probs[0]) == {"id", "title", "solved"}
    p = alice.get(f"/api/problems/{probs[0]['id']}")
    body = p.json()
    assert len(body["samples"]) == 2
    assert "2000000000" not in p.text and "1000000000" not in p.text


def test_limits_and_validation(clients):
    _, alice, _ = clients
    pid = alice.get("/api/problems").json()[0]["id"]
    r = alice.post("/api/submissions", json={"problem_id": pid, "language": "python", "source_code": "x" * 70000})
    assert r.status_code == 413 and "error" in r.json()
    r = alice.post("/api/submissions", json={"problem_id": pid, "language": "java", "source_code": "x"})
    assert r.status_code == 400 and "error" in r.json()


def test_admin_create_problem_with_hidden(clients):
    admin, alice, _ = clients
    r = admin.post("/api/admin/problems", json={
        "title": "Double", "statement": "Print 2*n", "time_limit_sec": 1, "memory_limit_mb": 128, "published": True,
        "tests": [{"input": "2\n", "expected_output": "4\n", "is_sample": True},
                  {"input": "777\n", "expected_output": "1554\n", "is_sample": False}]})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    d = alice.get(f"/api/problems/{pid}").json()
    assert [s["input"] for s in d["samples"]] == ["2\n"]
    assert "777" not in str(d) and "1554" not in str(d)
    r = admin.put(f"/api/admin/problems/{pid}", json={**r.json(), "title": "Double it"})
    assert r.json()["title"] == "Double it"
    assert admin.get("/api/admin/problems").status_code == 200


@pytest.mark.skipif(not LIVE, reason="needs hosted Judge0")
def test_live_verdicts_history_leaderboard(clients):
    admin, alice, bob = clients
    pid = alice.get("/api/problems").json()[0]["id"]
    py_ok = "a,b=map(int,input().split())\nprint(a+b)\n"
    cpp_ok = "#include <iostream>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<a+b<<'\\n';}\n"
    cases = {
        "AC-py": ("python", py_ok, "AC"),
        "AC-cpp": ("cpp", cpp_ok, "AC"),
        "WA": ("python", "a,b=map(int,input().split())\nprint(a+b+(1 if a==0 else 0))\n", "WA"),
        "RE": ("python", "raise SystemExit(3)\n", "RE"),
        "TLE": ("python", "while True: pass\n", "TLE"),
        "CE": ("cpp", "int main(){ return x; }\n", "CE"),
    }
    ids = {}
    t0 = time.time()
    for name, (lang, code, _) in cases.items():
        ids[name] = submit(alice, pid, lang, code)
        # POST must return quickly with pending, not wait for execution
    first = alice.get(f"/api/submissions/{ids['AC-py']}").json()
    assert first["status"] in ("pending", "done")
    results = {n: wait(alice, i) for n, i in ids.items()}
    print("elapsed", round(time.time() - t0, 1))
    for name, (_, _, want) in cases.items():
        r = results[name]
        assert r["verdict"] == want, (name, r)
    assert results["WA"]["failed_test"] == 5
    assert results["AC-py"]["runtime_ms"] is not None
    assert "Wrong answer" in results["WA"]["message"] and "0 0" not in str(results["WA"])
    # bob cannot read alice's submission
    r = bob.get(f"/api/submissions/{ids['AC-py']}")
    assert r.status_code == 404 and "error" in r.json()
    # history newest first
    hist = alice.get("/api/submissions").json()
    assert [h["id"] for h in hist] == sorted([h["id"] for h in hist], reverse=True)
    assert bob.get("/api/submissions").json() == []
    assert alice.get("/api/problems").json()[0]["solved"] is True
    # leaderboard: alice solved 1 with 0 wrong before first AC (AC-py was first)
    lb = alice.get("/api/leaderboard").json()
    assert lb[0] == {"rank": 1, "username": "alice", "solved": 1, "wrong": 0}
    assert all(row["username"] != "root_admin" for row in lb)
