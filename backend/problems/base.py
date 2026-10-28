"""Problem definitions. Expected outputs are computed by the reference `solve` function, never typed by hand."""
import random
from dataclasses import dataclass, field
from typing import Callable, Optional


def A(arr):
    return " ".join(map(str, arr))


def ints(t):
    return list(map(int, t.split()))


@dataclass
class Prob:
    title: str
    difficulty: str          # Easy | Medium | Hard
    statement: str
    hint: str
    time: str                # target time complexity of the intended solution
    space: str
    solve: Callable[[str], str]
    gen: Callable[[random.Random], str]
    samples: list            # shown to participants (first tests)
    edges: list = field(default_factory=list)
    big: Optional[Callable[[random.Random], str]] = None   # one large hidden test that punishes slow solutions
    brute: Optional[Callable[[str], str]] = None            # independent slow solver used only by the self-check
    tl: float = 2.0


def build_tests(p: Prob):
    """-> list of (input, expected_output, is_sample), samples first."""
    rng = random.Random(p.title)
    ins = [(s, True) for s in p.samples] + [(e, False) for e in p.edges]
    ins += [(p.gen(rng), False) for _ in range(6)]
    if p.big:
        ins.append((p.big(rng), False))
    out, seen = [], set()
    for s, is_sample in ins:
        if s in seen and not is_sample:
            continue
        seen.add(s)
        out.append((s, p.solve(s) + "\n", is_sample))
    return out
