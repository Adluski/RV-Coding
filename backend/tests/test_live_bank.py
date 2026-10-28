"""Live check of the seeded problem bank against the hosted Judge0 (skipped with SKIP_JUDGE0=1)."""
import os
import time

import pytest


from fastapi.testclient import TestClient  # noqa: E402

from backend import seed  # noqa: E402
from backend.app.db import Base, engine  # noqa: E402
from backend.app.main import app  # noqa: E402

pytestmark = pytest.mark.skipif(bool(os.environ.get("SKIP_JUDGE0")), reason="needs hosted Judge0")

SOLUTIONS = {
    ("Two Sum", "AC"): """
import sys
d=list(map(int,sys.stdin.read().split()));n,t=d[0],d[1];a=d[2:2+n];seen={}
for i,v in enumerate(a):
    if t-v in seen:
        print(seen[t-v]+1,i+1);break
    seen.setdefault(v,i)
""",
    ("Two Sum", "TLE"): """
import sys
d=list(map(int,sys.stdin.read().split()));n,t=d[0],d[1];a=d[2:2+n]
for j in range(n):
    for i in range(j):
        if a[i]+a[j]==t:
            print(i+1,j+1);raise SystemExit
""",
    ("Longest Valid Parentheses", "AC"): """
s=input().strip();st=[-1];b=0
for i,c in enumerate(s):
    if c=="(":st.append(i)
    else:
        st.pop()
        if not st:st.append(i)
        else:b=max(b,i-st[-1])
print(b)
""",
    ("Trapping Rain Water", "AC"): """
import sys
d=list(map(int,sys.stdin.read().split()));h=d[1:1+d[0]];i,j=0,len(h)-1;l=r=t=0
while i<j:
    if h[i]<h[j]:
        l=max(l,h[i]);t+=l-h[i];i+=1
    else:
        r=max(r,h[j]);t+=r-h[j];j-=1
print(t)
""",
    ("Sliding Window Maximum", "AC"): """
import sys
from collections import deque
d=list(map(int,sys.stdin.read().split()));n,k=d[0],d[1];a=d[2:2+n];q=deque();o=[]
for i,v in enumerate(a):
    while q and a[q[-1]]<=v:q.pop()
    q.append(i)
    if q[0]<=i-k:q.popleft()
    if i>=k-1:o.append(a[q[0]])
print(*o)
""",
    ("Sliding Window Maximum", "TLE"): """
import sys
d=list(map(int,sys.stdin.read().split()));n,k=d[0],d[1];a=d[2:2+n]
o=[]
for i in range(n-k+1):
    m=a[i]
    for x in range(i+1,i+k):
        if a[x]>m:m=a[x]
    o.append(m)
print(*o)
""",
    ("Edit Distance", "AC"): """
s=input().strip();u=input().strip();p=list(range(len(u)+1))
for i,a in enumerate(s,1):
    c=[i]
    for j,b in enumerate(u,1):
        c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(a!=b)))
    p=c
print(p[-1])
""",
    ("Binary Search Queries", "AC"): """
import sys,bisect
d=list(map(int,sys.stdin.read().split()));n,q=d[0],d[1];a=d[2:2+n]
for x in d[2+n:2+n+q]:
    i=bisect.bisect_left(a,x);print(i if i<n and a[i]==x else -1)
""",
}


def wait(client, sid, timeout=240):
    end = time.time() + timeout
    while time.time() < end:
        r = client.get(f"/api/submissions/{sid}").json()
        if r["status"] == "done":
            return r
        time.sleep(2)
    raise AssertionError("never finished")


def test_bank_live():
    Base.metadata.drop_all(engine)
    seed.main()
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"username": "solver", "password": "password123"}).status_code == 200
    probs = {p["title"]: p for p in c.get("/api/problems").json()}
    assert len(probs) == 51  # 50 + A + B
    levels = [p["difficulty"] for p in probs.values()]
    assert (levels.count("Easy"), levels.count("Medium"), levels.count("Hard")) == (18, 23, 10)

    # participants get the hint and target complexity, samples only, never hidden tests
    d = c.get(f"/api/problems/{probs['Two Sum']['id']}").json()
    assert d["hint"] and d["time_complexity"] == "O(n)" and len(d["samples"]) == 2
    assert "20000" not in str(d["samples"])

    ids = {}
    for (title, want), code in SOLUTIONS.items():
        r = c.post("/api/submissions", json={"problem_id": probs[title]["id"], "language": "python",
                                             "source_code": code, "claimed_time": "O(n)", "claimed_space": "O(1)"})
        assert r.status_code == 200, r.text
        ids[(title, want)] = r.json()["id"]
    out = {}
    for key, sid in ids.items():
        out[key] = wait(c, sid)
        print(key, out[key]["verdict"], out[key]["failed_test"], out[key]["runtime_ms"])
    for (title, want), r in out.items():
        assert r["verdict"] == want, (title, want, r)
    assert out[("Two Sum", "AC")]["claimed_time"] == "O(n)"
    engine.dispose()
    try:
        os.remove("test_suite.db")
    except OSError:
        pass
