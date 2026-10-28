"""Offline self-check of the problem bank (no network)."""
import random
from collections import Counter

import pytest

from backend.problems import ALL
from backend.problems.base import build_tests


def test_counts_and_shape():
    assert len(ALL) == 50
    assert Counter(p.difficulty for p in ALL) == {"Easy": 17, "Medium": 23, "Hard": 10}
    assert len({p.title for p in ALL}) == 50
    for p in ALL:
        assert p.hint and p.time and p.space and p.statement, p.title
        assert len(p.samples) >= 1


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.title)
def test_reference_matches_bruteforce(p):
    if not p.brute:
        pytest.skip("no independent brute force for this problem")
    rng = random.Random(12345)
    for _ in range(300):
        s = p.gen(rng)
        assert p.solve(s) == p.brute(s), (p.title, s)
    for s in [x for x in p.samples + p.edges if len(x) < 80]:  # brute force is too slow on big edges
        try:
            expected = p.brute(s)
        except RecursionError:
            continue
        assert p.solve(s) == expected, (p.title, s)


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.title)
def test_tests_build(p):
    tests = build_tests(p)
    assert sum(1 for t in tests if t[2]) == len(p.samples)
    assert sum(1 for t in tests if not t[2]) >= 4
    assert all(out.strip() != "" for _, out, _ in tests), p.title
    assert sum(len(i) for i, _, _ in tests) < 600_000


def test_without_brute_listed():
    print("no brute force:", [p.title for p in ALL if not p.brute])
