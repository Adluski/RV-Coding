import itertools
import re
from collections import Counter, deque

from .base import A, Prob, ints

P = []


def add(**kw):
    P.append(Prob(difficulty="Hard", **kw))


# 41 Trapping Rain Water
def rain(t):
    d = ints(t); h = d[1:1 + d[0]]; i, j = 0, len(h) - 1; lm = rm = tot = 0
    while i < j:
        if h[i] < h[j]:
            lm = max(lm, h[i]); tot += lm - h[i]; i += 1
        else:
            rm = max(rm, h[j]); tot += rm - h[j]; j -= 1
    return str(tot)


def rain_brute(t):
    d = ints(t); h = d[1:1 + d[0]]
    return str(sum(max(0, min(max(h[:i + 1]), max(h[i:])) - h[i]) for i in range(len(h))))


def rain_gen(r, n=None, lim=6):
    n = n or r.randint(1, 10); return f"{n}\n{A(r.randint(0, lim) for _ in range(n))}\n"


add(title="Trapping Rain Water", statement="""Bars of width 1 have the given heights. After rain, how many units of water are trapped between the bars?

Input: n, then n non-negative heights.
Constraints: 1 <= n <= 20000, 0 <= height <= 10^5.""",
    hint="Water above bar i is min(tallest bar to its left, tallest bar to its right) - height[i]. Recomputing those maxima per bar is O(n^2). Two pointers: always advance from the side whose current wall is lower; that side's running maximum is the limiting wall.",
    time="O(n)", space="O(1)", solve=rain, gen=rain_gen, brute=rain_brute,
    samples=["12\n0 1 0 2 1 0 1 3 2 1 2 1\n", "6\n4 2 0 3 2 5\n"], edges=["1\n5\n", "3\n3 0 3\n", "4\n1 2 3 4\n"],
    big=lambda r: rain_gen(r, 20000, 100000), tl=3.0)


# 42 Edit Distance
def edit(t):
    s, u = t.split(); prev = list(range(len(u) + 1))
    for i, a in enumerate(s, 1):
        cur = [i]
        for j, b in enumerate(u, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b)))
        prev = cur
    return str(prev[-1])


def edit_brute(t):
    s, u = t.split()

    def f(i, j):
        if i == len(s):
            return len(u) - j
        if j == len(u):
            return len(s) - i
        if s[i] == u[j]:
            return f(i + 1, j + 1)
        return 1 + min(f(i + 1, j), f(i, j + 1), f(i + 1, j + 1))
    return str(f(0, 0))


def edit_gen(r, lo=1, hi=6):
    return "".join(r.choice("abc") for _ in range(r.randint(lo, hi))) + "\n" + "".join(r.choice("abc") for _ in range(r.randint(lo, hi))) + "\n"


add(title="Edit Distance", statement="""Given two lowercase words, print the minimum number of single-character operations (insert, delete, replace) needed to turn the first word into the second.

Input: two lines, the words (length 1 to 800).
Output: the minimum number of operations.""",
    hint="Let dp[i][j] be the distance between the first i letters of s and the first j letters of t. If the letters match, dp[i][j] = dp[i-1][j-1]; otherwise 1 + min(dp[i-1][j] (delete), dp[i][j-1] (insert), dp[i-1][j-1] (replace)). Only the previous row is needed.",
    time="O(n * m)", space="O(min(n, m))", solve=edit, gen=edit_gen, brute=edit_brute,
    samples=["horse\nros\n", "intention\nexecution\n"], edges=["a\na\n", "abc\nxyz\n", "a\nbbbbbb\n"],
    big=lambda r: edit_gen(r, 800, 800), tl=4.0)


# 43 Largest Rectangle in Histogram
def hist(t):
    d = ints(t); h = d[1:1 + d[0]] + [0]; st = []; best = 0
    for i, v in enumerate(h):
        start = i
        while st and st[-1][1] >= v:
            idx, hh = st.pop(); best = max(best, hh * (i - idx)); start = idx
        st.append((start, v))
    return str(best)


def hist_brute(t):
    d = ints(t); h = d[1:1 + d[0]]
    return str(max(min(h[i:j]) * (j - i) for i in range(len(h)) for j in range(i + 1, len(h) + 1)))


def hist_gen(r, n=None, lim=6):
    n = n or r.randint(1, 9); return f"{n}\n{A(r.randint(0, lim) for _ in range(n))}\n"


add(title="Largest Rectangle in Histogram", statement="""A histogram has n bars of width 1 and the given heights. Find the area of the largest rectangle that fits inside it (the rectangle must lie within consecutive bars).

Input: n, then n non-negative heights.
Constraints: 1 <= n <= 20000, 0 <= height <= 10^5.""",
    hint="For each bar, the widest rectangle using it as the lowest bar extends left and right until a shorter bar. Keep a stack of bars with increasing heights: when a lower bar arrives, pop taller bars and compute the area they could cover.",
    time="O(n)", space="O(n)", solve=hist, gen=hist_gen, brute=hist_brute,
    samples=["6\n2 1 5 6 2 3\n", "2\n2 4\n"], edges=["1\n0\n", "4\n3 3 3 3\n", "5\n5 4 3 2 1\n"],
    big=lambda r: hist_gen(r, 20000, 100000), tl=3.0)


# 44 Median of Two Sorted Arrays
def median(t):
    d = ints(t); n, m = d[0], d[1]; a = d[2:2 + n]; b = d[2 + n:2 + n + m]
    i = j = 0; out = []
    while i < n or j < m:
        if j >= m or (i < n and a[i] <= b[j]):
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    k = len(out)
    return "%.1f" % (out[k // 2] if k % 2 else (out[k // 2 - 1] + out[k // 2]) / 2)


def median_brute(t):
    d = ints(t); n, m = d[0], d[1]; s = sorted(d[2:2 + n + m]); k = len(s)
    return "%.1f" % (s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2)


def median_gen(r, n=None, m=None, lim=20):
    n = n or r.randint(1, 6); m = m or r.randint(1, 6)
    a = sorted(r.randint(-lim, lim) for _ in range(n)); b = sorted(r.randint(-lim, lim) for _ in range(m))
    return f"{n} {m}\n{A(a)}\n{A(b)}\n"


add(title="Median of Two Sorted Arrays", statement="""Two sorted arrays are given. Print the median of all their elements combined, with exactly one digit after the decimal point (for example 2.0 or 2.5).

Input: first line n and m; second line n sorted integers; third line m sorted integers.
Constraints: 1 <= n, m <= 20000, |values| <= 10^6.""",
    hint="Merging both arrays gives O(n + m) and passes here. The classic O(log(min(n, m))) solution binary-searches a partition of the smaller array so that the left halves of both arrays together hold half the elements and every left value is <= every right value.",
    time="O(log(min(n, m)))  (O(n + m) merge also accepted)", space="O(1)", solve=median, gen=median_gen, brute=median_brute,
    samples=["2 1\n1 3\n2\n", "2 2\n1 2\n3 4\n"], edges=["1 1\n5\n5\n", "1 3\n100\n1 2 3\n", "3 1\n-5 -3 -1\n-2\n"])


# 45 Longest Valid Parentheses
def lvp(t):
    s = t.strip(); st = [-1]; best = 0
    for i, c in enumerate(s):
        if c == "(":
            st.append(i)
        else:
            st.pop()
            if not st:
                st.append(i)
            else:
                best = max(best, i - st[-1])
    return str(best)


def lvp_brute(t):
    s = t.strip(); best = 0
    for i in range(len(s)):
        bal = 0
        for j in range(i, len(s)):
            bal += 1 if s[j] == "(" else -1
            if bal < 0:
                break
            if bal == 0:
                best = max(best, j - i + 1)
    return str(best)


add(title="Longest Valid Parentheses", statement="""A string consists only of ( and ). Find the length of the longest contiguous substring that is a valid (well-formed) parentheses sequence.

Input: one line (length 1 to 20000).
Output: the length (0 if none).""",
    hint="Use a stack of indices, starting with -1 as a base. Push the index of every '('. For ')', pop; if the stack becomes empty push the current index as the new base, otherwise the valid length ending here is i - stack top.",
    time="O(n)", space="O(n)", solve=lvp, gen=lambda r: "".join(r.choice("()") for _ in range(r.randint(1, 14))) + "\n", brute=lvp_brute,
    samples=["(()\n", ")()())\n"], edges=["(\n", ")\n", "()(())\n", "((((\n", "()()()\n"],
    big=lambda r: "".join(r.choice("(()") for _ in range(20000)) + "\n", tl=3.0)


# 46 Sliding Window Maximum
def swm(t):
    d = ints(t); n, k = d[0], d[1]; a = d[2:2 + n]; dq = deque(); out = []
    for i, v in enumerate(a):
        while dq and a[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            out.append(a[dq[0]])
    return A(out)


def swm_brute(t):
    d = ints(t); n, k = d[0], d[1]; a = d[2:2 + n]
    return A(max(a[i:i + k]) for i in range(n - k + 1))


def swm_gen(r, n=None, k=None, lim=9):
    n = n or r.randint(1, 10); k = k or r.randint(1, n)
    return f"{n} {k}\n{A(r.randint(-lim, lim) for _ in range(n))}\n"


add(title="Sliding Window Maximum", statement="""A window of size k slides from the left end of the array to the right end, one position at a time. Print the maximum of each window position.

Input: first line n and k; second line n integers.
Output: n - k + 1 integers, space separated.
Constraints: 1 <= k <= n <= 20000, |a[i]| <= 10^9.""",
    hint="Recomputing max for each window is O(n*k). Keep a deque of indices whose values are in decreasing order: pop from the back while the new value is bigger, pop from the front when it leaves the window. The front is always the window maximum.",
    time="O(n)", space="O(k)", solve=swm, gen=swm_gen, brute=swm_brute,
    samples=["8 3\n1 3 -1 -3 5 3 6 7\n", "1 1\n1\n"], edges=["3 3\n1 2 3\n", "4 1\n4 3 2 1\n", "5 2\n2 2 2 2 2\n"],
    big=lambda r: swm_gen(r, 20000, 5000, 10 ** 9), tl=3.0)


# 47 N-Queens (count)
def queens(t):
    n = int(t); full = (1 << n) - 1

    def go(cols, d1, d2):
        if cols == full:
            return 1
        free = full & ~(cols | d1 | d2); tot = 0
        while free:
            bit = free & -free; free ^= bit
            tot += go(cols | bit, ((d1 | bit) << 1) & full, (d2 | bit) >> 1)
        return tot
    return str(go(0, 0, 0))


def queens_brute(t):
    n = int(t)
    return str(sum(all(abs(p[i] - p[j]) != j - i for i in range(n) for j in range(i + 1, n)) for p in itertools.permutations(range(n))))


add(title="N-Queens Count", statement="""Place n queens on an n x n chessboard so that no two attack each other (no shared row, column or diagonal). How many distinct placements exist?

Input: one integer n, 1 <= n <= 10.
Output: the number of solutions.""",
    hint="Place one queen per row with backtracking and remember which columns and both diagonals are taken (sets or bitmasks). Prune as soon as a square is attacked; do not generate all n^n boards.",
    time="O(n!) worst case, heavily pruned", space="O(n)", solve=queens, gen=lambda r: f"{r.randint(1, 8)}\n", brute=queens_brute,
    samples=["4\n", "1\n"], edges=["2\n", "3\n", "8\n", "9\n", "10\n"])


# 48 Minimum Window Substring (length)
def minwin(t):
    s, u = t.split(); need = Counter(u); missing = len(u); best = 0; left = 0
    for right, c in enumerate(s):
        if need[c] > 0:
            missing -= 1
        need[c] -= 1
        if missing == 0:
            while need[s[left]] < 0:
                need[s[left]] += 1; left += 1
            if best == 0 or right - left + 1 < best:
                best = right - left + 1
            need[s[left]] += 1; missing += 1; left += 1
    return str(best)


def minwin_brute(t):
    s, u = t.split(); need = Counter(u)
    for L in range(len(u), len(s) + 1):
        for i in range(len(s) - L + 1):
            if not (need - Counter(s[i:i + L])):
                return str(L)
    return "0"


def minwin_gen(r):
    s = "".join(r.choice("abc") for _ in range(r.randint(1, 12))); u = "".join(r.choice("abc") for _ in range(r.randint(1, 4)))
    return f"{s}\n{u}\n"


add(title="Minimum Window Substring", statement="""Find the shortest contiguous substring of s that contains every character of t, counting multiplicity (if t has two a's the window needs two a's). Print its length, or 0 if no such substring exists.

Input: two lines, s and t (lowercase, length 1 to 20000).
Output: the length.""",
    hint="Sliding window with two pointers. Expand the right end until the window covers all needed counts, then shrink from the left while it still does, recording the shortest. Track how many required characters are still missing instead of re-checking all 26 counts.",
    time="O(|s| + |t|)", space="O(alphabet size)", solve=minwin, gen=minwin_gen, brute=minwin_brute,
    samples=["ADOBECODEBANC\nABC\n", "a\naa\n"], edges=["a\na\n", "ab\nb\n", "aab\naab\n", "abc\nd\n"])


# 49 Word Ladder (length)
def ladder(t):
    L = t.split("\n"); b, e = L[0].split(); words = set(L[2].split())
    if e not in words:
        return "0"
    q = deque([(b, 1)]); seen = {b}
    while q:
        w, d = q.popleft()
        if w == e:
            return str(d)
        for i in range(len(w)):
            for c in "abcdefghijklmnopqrstuvwxyz":
                x = w[:i] + c + w[i + 1:]
                if x in words and x not in seen:
                    seen.add(x); q.append((x, d + 1))
    return "0"


def ladder_gen(r):
    ws = lambda: "".join(r.choice("abc") for _ in range(3))
    b = ws()
    e = ws()
    while e == b:
        e = ws()
    k = r.randint(1, 10); d = sorted({ws() for _ in range(k)})
    if r.random() < 0.7 and e not in d:
        d.append(e)
    return f"{b} {e}\n{len(d)}\n{' '.join(d)}\n"


add(title="Word Ladder", statement="""Transform the word begin into the word end by changing exactly one letter at a time; every intermediate word (and end itself) must be in the dictionary. begin does not need to be in the dictionary. Print the number of words in the shortest sequence, counting both begin and end, or 0 if impossible (or end is not in the dictionary).

Input: line 1 begin and end (equal length, different words); line 2 the number k of dictionary words; line 3 the k words.
Constraints: word length <= 10, k <= 5000.""",
    hint="Every word is a node; two words are connected if they differ in one letter. The shortest transformation is a shortest path in an unweighted graph, so use BFS from begin, and stop the first time you reach end. Generate neighbours by trying all 26 letters at each position rather than comparing all pairs.",
    time="O(k * L * 26)", space="O(k * L)", solve=ladder, gen=ladder_gen,
    samples=["hit cog\n6\nhot dot dog lot log cog\n", "hit cog\n5\nhot dot dog lot log\n"], edges=["aaa aab\n1\naab\n", "aaa bbb\n3\nabb bbb aab\n", "abc cba\n2\ncba xyz\n"])


# 50 Regular Expression Matching
def regex(t):
    s, p = t.split(); n, m = len(s), len(p)
    dp = [[False] * (m + 1) for _ in range(n + 1)]; dp[0][0] = True
    for j in range(2, m + 1):
        if p[j - 1] == "*":
            dp[0][j] = dp[0][j - 2]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if p[j - 1] == "*":
                dp[i][j] = dp[i][j - 2] or (p[j - 2] in (s[i - 1], ".") and dp[i - 1][j])
            else:
                dp[i][j] = p[j - 1] in (s[i - 1], ".") and dp[i - 1][j - 1]
    return "YES" if dp[n][m] else "NO"


def regex_brute(t):
    s, p = t.split()
    return "YES" if re.fullmatch(p, s) else "NO"


def regex_gen(r):
    s = "".join(r.choice("ab") for _ in range(r.randint(1, 6)))
    p = "".join(r.choice("ab.") + r.choice(["", "", "*"]) for _ in range(r.randint(1, 5)))
    return f"{s}\n{p}\n"


add(title="Regular Expression Matching", statement="""Implement matching of the whole string s against a pattern p. In p, '.' matches any single character, and '*' means zero or more of the element before it (so "a*" matches "", "a", "aa", ...). The match must cover the entire string.

Input: two lines, s (lowercase, length 1 to 1000) and p (lowercase letters, '.' and '*'; '*' never appears first and never twice in a row).
Output: YES if p matches the entire s, otherwise NO.""",
    hint="dp[i][j] = does s[:i] match p[:j]? If p[j-1] is '*', either use zero copies (dp[i][j-2]) or one more copy when the preceding element matches s[i-1] (dp[i-1][j]). Otherwise the last characters must match (equal or '.') and dp[i-1][j-1] must be true.",
    time="O(n * m)", space="O(n * m)", solve=regex, gen=regex_gen, brute=regex_brute,
    samples=["aa\na\n", "ab\n.*\n"], edges=["aab\nc*a*b\n", "mississippi\nmis*is*p*.\n", "a\nab*\n", "aaa\na*a\n", "a\n.*.*\n"])
