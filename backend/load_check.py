"""Bounded check: submit 20 correct Python solutions concurrently to the seeded A+B problem.

Usage (against a running server):  python -m backend.load_check https://your-app.vercel.app
Without a URL it runs in-process against the local DB (ADMIN_*/DATABASE_URL env as for the app).
"""
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

N = 20
CODE = "a,b=map(int,input().split())\nprint(a+b)\n"


def one(client_factory, i):
    c = client_factory()
    name = f"load_{uuid.uuid4().hex[:10]}"
    c.post("/api/auth/register", json={"username": name, "password": "password123"}).raise_for_status()
    pid = c.get("/api/problems").json()[0]["id"]
    t0 = time.time()
    r = c.post("/api/submissions", json={"problem_id": pid, "language": "python", "source_code": CODE})
    r.raise_for_status()
    post_s = time.time() - t0
    sid = r.json()["id"]
    while time.time() - t0 < 240:
        s = c.get(f"/api/submissions/{sid}").json()
        if s["status"] == "done":
            return s["verdict"], post_s, time.time() - t0, s.get("message")
        time.sleep(2)
    return "TIMEOUT", post_s, time.time() - t0, None


def main():
    if len(sys.argv) > 1:
        base = sys.argv[1].rstrip("/")
        factory = lambda: httpx.Client(base_url=base, timeout=30)  # noqa: E731
    else:
        from fastapi.testclient import TestClient
        from backend.app.main import app
        factory = lambda: TestClient(app)  # noqa: E731
    with ThreadPoolExecutor(N) as ex:
        results = list(ex.map(lambda i: one(factory, i), range(N)))
    verdicts = {}
    for v, *_ in results:
        verdicts[v] = verdicts.get(v, 0) + 1
    print("verdicts:", verdicts)
    print("POST latency max/avg (s): %.2f / %.2f" % (max(r[1] for r in results), sum(r[1] for r in results) / N))
    print("time to final verdict max/avg (s): %.1f / %.1f" % (max(r[2] for r in results), sum(r[2] for r in results) / N))
    errs = {r[3] for r in results if r[0] == "ERR"}
    if errs:
        print("ERR messages:", errs)


if __name__ == "__main__":
    main()
