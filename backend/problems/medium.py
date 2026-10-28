import bisect
import itertools
from collections import Counter, deque

from .base import A, Prob, ints

P = []


def add(**kw):
    P.append(Prob(difficulty="Medium", **kw))


def rows(t, r):
    return t.split("\n")[1:1 + r]


# 18 Longest Substring Without Repeating Characters
def lsub(t):
    s = t.strip(); last = {}; start = best = 0
    for i, c in enumerate(s):
        if c in last and last[c] >= start:
            start = last[c] + 1
        last[c] = i; best = max(best, i - start + 1)
    return str(best)


def lsub_brute(t):
    s = t.strip(); best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            if len(set(s[i:j + 1])) == j - i + 1:
                best = max(best, j - i + 1)
    return str(best)


add(title="Longest Substring Without Repeating Characters", statement="""Find the length of the longest contiguous substring in which all characters are different.

Input: one line, a string of lowercase letters (length 1 to 20000).
Output: the length.""",
    hint="Use a sliding window [start, i]. Remember the last index of every character; when the new character was seen inside the window, move start just past that earlier occurrence.",
    time="O(n)", space="O(alphabet size)", solve=lsub, brute=lsub_brute,
    gen=lambda r: "".join(r.choice("abcd") for _ in range(r.randint(1, 12))) + "\n",
    samples=["abcabcbb\n", "pwwkew\n"], edges=["a\n", "bbbbb\n", "abcdef\n"])


# 19 Count Anagram Groups
def agroups(t):
    w = t.split("\n")[1].split()
    return str(len({"".join(sorted(x)) for x in w}))


def agroups_gen(r):
    n = r.randint(1, 8)
    return f"{n}\n{' '.join(''.join(r.choice('abc') for _ in range(r.randint(1, 3))) for _ in range(n))}\n"


add(title="Count Anagram Groups", statement="""Words that are anagrams of each other belong to the same group. How many groups are there?

Input: n on the first line; the n lowercase words, space separated, on the second line.
Output: the number of groups.
Constraints: 1 <= n <= 10000, word length 1 to 20.""",
    hint="All anagrams share the same sorted-letters string (or the same 26-letter count tuple). Use that as a dictionary key and count distinct keys.",
    time="O(n * k log k)", space="O(n * k)", solve=agroups, gen=agroups_gen,
    samples=["6\neat tea tan ate nat bat\n", "1\na\n"], edges=["3\nab ba ab\n", "3\na b c\n"])


# 20 Product of Array Except Self
def pself(t):
    d = ints(t); a = d[1:1 + d[0]]; n = len(a); out = [1] * n
    p = 1
    for i in range(n):
        out[i] = p; p *= a[i]
    p = 1
    for i in range(n - 1, -1, -1):
        out[i] *= p; p *= a[i]
    return A(out)


def pself_brute(t):
    d = ints(t); a = d[1:1 + d[0]]; out = []
    for i in range(len(a)):
        p = 1
        for j in range(len(a)):
            if j != i:
                p *= a[j]
        out.append(p)
    return A(out)


def pself_gen(r):
    n = r.randint(2, 8)
    return f"{n}\n{A(r.choice([0, r.randint(-4, 4), r.randint(1, 4)]) for _ in range(n))}\n"


add(title="Product of Array Except Self", statement="""For each position i print the product of all elements except a[i]. Do it without division (the array may contain zeros).

Input: n, then n integers.
Output: n integers, space separated.
Constraints: 2 <= n <= 10, |a[i]| <= 10. (Every answer fits in 64 bits.)""",
    hint="Product except i = (product of everything left of i) * (product of everything right of i). Compute prefix products going right, then multiply in suffix products going left.",
    time="O(n)", space="O(1) extra", solve=pself, gen=pself_gen, brute=pself_brute,
    samples=["4\n1 2 3 4\n", "5\n-1 1 0 -3 3\n"], edges=["2\n0 0\n", "3\n0 5 2\n"])


# 21 Top K Frequent Elements
def topk(t):
    d = ints(t); n, k = d[0], d[1]; a = d[2:2 + n]; c = Counter(a)
    return A(sorted(c, key=lambda v: (-c[v], v))[:k])


def topk_gen(r):
    n = r.randint(1, 10); a = [r.randint(-4, 4) for _ in range(n)]; k = r.randint(1, len(set(a)))
    return f"{n} {k}\n{A(a)}\n"


add(title="Top K Frequent Elements", statement="""Print the k values that occur most often. Order the output by frequency (highest first); values with equal frequency are ordered by smaller value first.

Input: first line n and k; second line n integers.
Output: k integers, space separated.
Constraints: 1 <= k <= number of distinct values, n <= 20000.""",
    hint="Count with a hash map. Then either sort the distinct values by (-count, value), or use a heap of size k, or bucket the values by their count for O(n).",
    time="O(n log k)", space="O(n)", solve=topk, gen=topk_gen,
    samples=["6 2\n1 1 1 2 2 3\n", "1 1\n5\n"], edges=["4 2\n3 3 1 1\n", "5 3\n-1 -1 2 2 7\n"])


# 22 3Sum (count)
def three_sum(t):
    d = ints(t); a = sorted(d[1:1 + d[0]]); n = len(a); cnt = 0
    for i in range(n - 2):
        if i and a[i] == a[i - 1]:
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            s = a[i] + a[lo] + a[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                cnt += 1; lo += 1; hi -= 1
                while lo < hi and a[lo] == a[lo - 1]:
                    lo += 1
    return str(cnt)


def three_sum_brute(t):
    d = ints(t); a = d[1:1 + d[0]]
    return str(len({tuple(sorted(c)) for c in itertools.combinations(a, 3) if sum(c) == 0}))


add(title="3Sum", statement="""Count the distinct triplets of values (x, y, z), taken from three different positions, with x + y + z = 0. Triplets with the same multiset of values count once.

Input: n, then n integers.
Output: the number of distinct triplets.
Constraints: 3 <= n <= 1500, |a[i]| <= 1000.""",
    hint="Sort the array. Fix the first element, then use two pointers on the rest: sum too small moves the left pointer up, too large moves the right pointer down. Skip duplicate values to avoid counting a triplet twice.",
    time="O(n^2)", space="O(1)", solve=three_sum, brute=three_sum_brute,
    gen=lambda r: (lambda n: f"{n}\n{A(r.randint(-4, 4) for _ in range(n))}\n")(r.randint(3, 9)),
    samples=["6\n-1 0 1 2 -1 -4\n", "3\n0 0 0\n"], edges=["3\n1 2 3\n", "7\n0 0 0 0 0 0 0\n"],
    big=lambda r: f"1500\n{A(r.randint(-1000, 1000) for _ in range(1500))}\n", tl=4.0)


# 23 Container With Most Water
def water(t):
    d = ints(t); h = d[1:1 + d[0]]; i, j = 0, len(h) - 1; best = 0
    while i < j:
        best = max(best, (j - i) * min(h[i], h[j]))
        if h[i] < h[j]:
            i += 1
        else:
            j -= 1
    return str(best)


def water_brute(t):
    d = ints(t); h = d[1:1 + d[0]]
    return str(max((j - i) * min(h[i], h[j]) for i in range(len(h)) for j in range(i + 1, len(h))))


def water_gen(r, n=None, lim=9):
    n = n or r.randint(2, 9)
    return f"{n}\n{A(r.randint(0, lim) for _ in range(n))}\n"


add(title="Container With Most Water", statement="""n vertical lines stand at positions 1..n with the given heights. Choose two lines; together with the x-axis they form a container whose water area is (distance between them) * (the shorter height). Print the maximum area.

Input: n, then n heights.
Constraints: 2 <= n <= 20000, 0 <= height <= 10000.""",
    hint="Start with the widest container (both ends). The area is limited by the shorter line, so moving the taller line inward can only make it worse; move the shorter one instead.",
    time="O(n)", space="O(1)", solve=water, gen=water_gen, brute=water_brute,
    samples=["9\n1 8 6 2 5 4 8 3 7\n", "2\n1 1\n"], edges=["2\n0 0\n", "3\n5 1 5\n"],
    big=lambda r: water_gen(r, 20000, 10000), tl=3.0)


# 24 Coin Change
def coins(t):
    d = ints(t); n, amt = d[0], d[1]; cs = d[2:2 + n]
    INF = float("inf"); dp = [0] + [INF] * amt
    for x in range(1, amt + 1):
        for c in cs:
            if c <= x and dp[x - c] + 1 < dp[x]:
                dp[x] = dp[x - c] + 1
    return str(dp[amt] if dp[amt] != INF else -1)


def coins_brute(t):
    d = ints(t); n, amt = d[0], d[1]; cs = d[2:2 + n]

    def f(rem):
        if rem == 0:
            return 0
        best = float("inf")
        for c in cs:
            if c <= rem:
                best = min(best, f(rem - c) + 1)
        return best
    r = f(amt)
    return str(r if r != float("inf") else -1)


def coins_gen(r):
    n = r.randint(1, 3); cs = r.sample(range(1, 8), n)
    return f"{n} {r.randint(0, 9)}\n{A(cs)}\n"


add(title="Coin Change", statement="""Given coin denominations (unlimited supply of each) and an amount, find the minimum number of coins that sum exactly to the amount, or -1 if impossible.

Input: first line n (number of denominations) and the amount; second line the n distinct positive denominations.
Output: the minimum number of coins, or -1.
Constraints: 1 <= n <= 12, denominations <= 10000, 0 <= amount <= 10000.""",
    hint="Let dp[x] be the fewest coins for amount x. dp[0] = 0 and dp[x] = 1 + min(dp[x - c]) over all coins c <= x. Greedy (largest coin first) is wrong: coins 1, 3, 4 and amount 6 is 3+3, not 4+1+1.",
    time="O(amount * n)", space="O(amount)", solve=coins, gen=coins_gen, brute=coins_brute,
    samples=["3 11\n1 2 5\n", "1 3\n2\n"], edges=["1 0\n7\n", "3 6\n1 3 4\n", "2 9999\n7 9\n"])


# 25 Longest Increasing Subsequence
def lis(t):
    d = ints(t); a = d[1:1 + d[0]]; tails = []
    for v in a:
        i = bisect.bisect_left(tails, v)
        if i == len(tails):
            tails.append(v)
        else:
            tails[i] = v
    return str(len(tails))


def lis_brute(t):
    d = ints(t); a = d[1:1 + d[0]]; dp = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return str(max(dp))


def lis_gen(r, n=None, lim=12):
    n = n or r.randint(1, 10)
    return f"{n}\n{A(r.randint(-lim, lim) for _ in range(n))}\n"


add(title="Longest Increasing Subsequence", statement="""Find the length of the longest strictly increasing subsequence (not necessarily contiguous).

Input: n, then n integers.
Constraints: 1 <= n <= 20000, |a[i]| <= 10^9.""",
    hint="The O(n^2) DP (best ending at each index) is too slow for 20000 elements. Keep an array tails where tails[k] is the smallest possible ending value of an increasing subsequence of length k+1; it stays sorted, so use binary search to place each element.",
    time="O(n log n)", space="O(n)", solve=lis, gen=lis_gen, brute=lis_brute,
    samples=["8\n10 9 2 5 3 7 101 18\n", "4\n7 7 7 7\n"], edges=["1\n3\n", "5\n5 4 3 2 1\n"],
    big=lambda r: lis_gen(r, 20000, 10 ** 9), tl=3.0)


# 26 Number of Islands
def islands(t):
    r, c = ints(t.split("\n")[0]); g = [list(x) for x in rows(t, r)]; cnt = 0
    for i in range(r):
        for j in range(c):
            if g[i][j] == "1":
                cnt += 1; st = [(i, j)]; g[i][j] = "0"
                while st:
                    x, y = st.pop()
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < r and 0 <= ny < c and g[nx][ny] == "1":
                            g[nx][ny] = "0"; st.append((nx, ny))
    return str(cnt)


def grid_gen(r, alphabet="01", p=None):
    h, w = r.randint(1, 6), r.randint(1, 6)
    return f"{h} {w}\n" + "\n".join("".join(r.choice(alphabet) for _ in range(w)) for _ in range(h)) + "\n"


add(title="Number of Islands", statement="""A grid of 0 (water) and 1 (land) is given. An island is a maximal group of land cells connected horizontally or vertically (not diagonally). Count the islands.

Input: first line r and c; then r lines, each a string of c characters 0/1 (no spaces).
Constraints: 1 <= r, c <= 300.""",
    hint="Scan the grid; when you find an unvisited land cell, count one island and flood-fill (DFS/BFS) all land connected to it, marking cells visited so you never count them again.",
    time="O(r * c)", space="O(r * c)", solve=islands, gen=grid_gen,
    samples=["4 5\n11000\n11000\n00100\n00011\n", "1 1\n0\n"], edges=["1 1\n1\n", "2 2\n10\n01\n", "3 3\n111\n111\n111\n"])


# 27 Rotting Oranges
def rotting(t):
    r, c = ints(t.split("\n")[0]); g = [list(map(int, x)) for x in rows(t, r)]
    q = deque((i, j) for i in range(r) for j in range(c) if g[i][j] == 2)
    fresh = sum(x == 1 for row in g for x in row); mins = 0
    while q and fresh:
        for _ in range(len(q)):
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < r and 0 <= ny < c and g[nx][ny] == 1:
                    g[nx][ny] = 2; fresh -= 1; q.append((nx, ny))
        mins += 1
    return str(mins if fresh == 0 else -1)


add(title="Rotting Oranges", statement="""A grid has 0 (empty), 1 (fresh orange) and 2 (rotten orange). Every minute, each fresh orange that is horizontally or vertically adjacent to a rotten one becomes rotten. Print the minutes until no fresh orange remains, or -1 if some never rot. If there are no fresh oranges at the start, print 0.

Input: first line r and c; then r lines, each a string of c digits (0, 1 or 2, no spaces).
Constraints: 1 <= r, c <= 200.""",
    hint="Start a multi-source BFS from every rotten orange at once. Each BFS layer is one minute. At the end, if any fresh orange is left untouched, the answer is -1.",
    time="O(r * c)", space="O(r * c)", solve=rotting, gen=lambda r: grid_gen(r, "0112"),
    samples=["3 3\n211\n110\n011\n", "3 3\n211\n011\n101\n"], edges=["1 1\n0\n", "1 2\n01\n", "1 1\n1\n", "1 3\n210\n"])


# 28 Course Schedule
def sched(t):
    L = t.split("\n"); n, m = ints(L[0]); adj = [[] for _ in range(n)]; indeg = [0] * n
    for line in L[1:1 + m]:
        a, b = ints(line); adj[b].append(a); indeg[a] += 1
    q = deque(i for i in range(n) if indeg[i] == 0); seen = 0
    while q:
        x = q.popleft(); seen += 1
        for y in adj[x]:
            indeg[y] -= 1
            if indeg[y] == 0:
                q.append(y)
    return "YES" if seen == n else "NO"


def sched_brute(t):
    L = t.split("\n"); n, m = ints(L[0]); adj = [[] for _ in range(n)]
    for line in L[1:1 + m]:
        a, b = ints(line); adj[b].append(a)
    state = [0] * n

    def dfs(x):
        state[x] = 1
        for y in adj[x]:
            if state[y] == 1 or (state[y] == 0 and dfs(y)):
                return True
        state[x] = 2
        return False
    return "NO" if any(state[i] == 0 and dfs(i) for i in range(n)) else "YES"


def sched_gen(r):
    n = r.randint(1, 6); m = r.randint(0, 7); e = []
    for _ in range(m):
        if n > 1:
            a, b = r.sample(range(n), 2); e.append(f"{a} {b}")
    return f"{n} {len(e)}\n" + "".join(x + "\n" for x in e)


add(title="Course Schedule", statement="""There are n courses numbered 0..n-1 and m prerequisite pairs "a b", meaning course b must be taken before course a. Can all courses be finished?

Input: first line n and m; then m lines each with a and b.
Output: YES if possible, otherwise NO (a cycle exists).
Constraints: 1 <= n <= 20000, 0 <= m <= 50000.""",
    hint="Model it as a directed graph. All courses can be finished exactly when the graph has no cycle. Kahn's algorithm: repeatedly remove nodes with no remaining prerequisites; if you cannot remove all n nodes, there is a cycle.",
    time="O(n + m)", space="O(n + m)", solve=sched, gen=sched_gen, brute=sched_brute,
    samples=["2 1\n1 0\n", "2 2\n1 0\n0 1\n"], edges=["1 0\n", "3 0\n", "3 3\n1 0\n2 1\n0 2\n"])


# 29 Word Break
def wbreak(t):
    L = t.split("\n"); s = L[0].strip(); words = set(L[2].split()); n = len(s)
    dp = [True] + [False] * n
    for i in range(1, n + 1):
        dp[i] = any(dp[j] and s[j:i] in words for j in range(i))
    return "YES" if dp[n] else "NO"


def wbreak_brute(t):
    L = t.split("\n"); s = L[0].strip(); words = L[2].split()

    def f(i):
        return i == len(s) or any(s.startswith(w, i) and f(i + len(w)) for w in words)
    return "YES" if f(0) else "NO"


def wbreak_gen(r):
    s = "".join(r.choice("ab") for _ in range(r.randint(1, 9))); k = r.randint(1, 4)
    ws = ["".join(r.choice("ab") for _ in range(r.randint(1, 3))) for _ in range(k)]
    return f"{s}\n{k}\n{' '.join(ws)}\n"


add(title="Word Break", statement="""Can the string s be split into a sequence of one or more dictionary words (words may be reused)?

Input: line 1 the lowercase string s; line 2 the number k of dictionary words; line 3 the k words, space separated.
Output: YES or NO.
Constraints: |s| <= 1000, k <= 500, word length <= 20.""",
    hint="Let dp[i] mean 'the first i characters can be split'. dp[0] = true; dp[i] is true if for some j < i, dp[j] is true and s[j:i] is a word. Put the words in a set for O(1) lookup.",
    time="O(n^2)", space="O(n)", solve=wbreak, gen=wbreak_gen, brute=wbreak_brute,
    samples=["leetcode\n2\nleet code\n", "catsandog\n5\ncats dog sand and cat\n"], edges=["a\n1\na\n", "aaaaaaa\n2\naaa aaaa\n", "ab\n1\nba\n"])


# 30 Unique Paths II
MOD = 10 ** 9 + 7


def upaths(t):
    r, c = ints(t.split("\n")[0]); g = rows(t, r); dp = [[0] * c for _ in range(r)]
    for i in range(r):
        for j in range(c):
            if g[i][j] == "1":
                continue
            if i == 0 and j == 0:
                dp[i][j] = 1
            else:
                dp[i][j] = ((dp[i - 1][j] if i else 0) + (dp[i][j - 1] if j else 0)) % MOD
    return str(dp[r - 1][c - 1])


def upaths_brute(t):
    r, c = ints(t.split("\n")[0]); g = rows(t, r)

    def f(i, j):
        if i >= r or j >= c or g[i][j] == "1":
            return 0
        if i == r - 1 and j == c - 1:
            return 1
        return f(i + 1, j) + f(i, j + 1)
    return str(f(0, 0) % MOD)


def upaths_gen(r):
    h, w = r.randint(1, 5), r.randint(1, 5)
    return f"{h} {w}\n" + "\n".join("".join("1" if r.random() < .25 else "0" for _ in range(w)) for _ in range(h)) + "\n"


add(title="Unique Paths with Obstacles", statement="""A robot starts at the top-left cell of a grid and wants to reach the bottom-right cell, moving only right or down. Cells marked 1 are obstacles. Count the paths modulo 1000000007 (if the start or the end is blocked the answer is 0).

Input: first line r and c; then r lines of c characters 0/1 (no spaces).
Constraints: 1 <= r, c <= 300.""",
    hint="ways[i][j] = ways[i-1][j] + ways[i][j-1] for free cells, 0 for obstacles. Take the remainder at every addition so numbers stay small. One row of memory is enough.",
    time="O(r * c)", space="O(c)", solve=upaths, gen=upaths_gen, brute=upaths_brute,
    samples=["3 3\n000\n010\n000\n", "2 2\n01\n00\n"], edges=["1 1\n0\n", "1 1\n1\n", "2 2\n00\n01\n", "20 20\n" + "\n".join("0" * 20 for _ in range(20)) + "\n"])


# 31 Subarray Sum Equals K
def subk(t):
    d = ints(t); n, k = d[0], d[1]; a = d[2:2 + n]; c = Counter({0: 1}); s = res = 0
    for v in a:
        s += v; res += c[s - k]; c[s] += 1
    return str(res)


def subk_brute(t):
    d = ints(t); n, k = d[0], d[1]; a = d[2:2 + n]
    return str(sum(sum(a[i:j]) == k for i in range(n) for j in range(i + 1, n + 1)))


def subk_gen(r, n=None, lim=3):
    n = n or r.randint(1, 9)
    return f"{n} {r.randint(-3, 3)}\n{A(r.randint(-lim, lim) for _ in range(n))}\n"


add(title="Subarray Sum Equals K", statement="""Count the contiguous non-empty subarrays whose sum equals k. Negative numbers are allowed.

Input: first line n and k; second line n integers.
Constraints: 1 <= n <= 20000, |a[i]| <= 1000, |k| <= 10^7.""",
    hint="Let prefix[i] be the sum of the first i elements. A subarray (j, i] has sum k when prefix[i] - prefix[j] = k. While scanning, store how many times each prefix sum has occurred in a hash map and add count[prefix - k].",
    time="O(n)", space="O(n)", solve=subk, gen=subk_gen, brute=subk_brute,
    samples=["3 2\n1 1 1\n", "3 3\n1 2 3\n"], edges=["1 0\n0\n", "4 0\n0 0 0 0\n", "3 0\n1 -1 0\n"],
    big=lambda r: subk_gen(r, 20000, 2), tl=3.0)


# 32 Daily Temperatures
def daily(t):
    d = ints(t); a = d[1:1 + d[0]]; res = [0] * len(a); st = []
    for i, v in enumerate(a):
        while st and a[st[-1]] < v:
            j = st.pop(); res[j] = i - j
        st.append(i)
    return A(res)


def daily_brute(t):
    d = ints(t); a = d[1:1 + d[0]]; res = []
    for i in range(len(a)):
        res.append(next((j - i for j in range(i + 1, len(a)) if a[j] > a[i]), 0))
    return A(res)


def daily_gen(r):
    n = r.randint(1, 10); return f"{n}\n{A(r.randint(30, 40) for _ in range(n))}\n"


def daily_big(r):
    n = 20000; return f"{n}\n{A(100000 - i for i in range(n))}\n"


add(title="Daily Temperatures", statement="""For each day, print how many days you must wait until a strictly warmer temperature. If there is no warmer day in the future, print 0 for that day.

Input: n, then n temperatures.
Output: n integers, space separated.
Constraints: 1 <= n <= 20000.""",
    hint="Scanning forward from every day is O(n^2) on a falling sequence. Keep a stack of days still waiting for a warmer day (their temperatures are non-increasing). When today is warmer than the top, pop it and its answer is today - that day.",
    time="O(n)", space="O(n)", solve=daily, gen=daily_gen, brute=daily_brute,
    samples=["8\n73 74 75 71 69 72 76 73\n", "3\n30 40 50\n"], edges=["1\n50\n", "4\n5 5 5 5\n", "4\n9 8 7 6\n"], big=daily_big, tl=3.0)


# 33 Merge Intervals
def merge_iv(t):
    L = t.split("\n"); n = int(L[0]); iv = sorted(tuple(ints(x)) for x in L[1:1 + n]); out = []
    for l, r in iv:
        if out and l <= out[-1][1]:
            out[-1][1] = max(out[-1][1], r)
        else:
            out.append([l, r])
    return "\n".join(f"{l} {r}" for l, r in out)


def iv_gen(r):
    n = r.randint(1, 6); ivs = []
    for _ in range(n):
        l = r.randint(0, 15); ivs.append((l, l + r.randint(0, 4)))
    return f"{n}\n" + "".join(f"{l} {h}\n" for l, h in ivs)


add(title="Merge Intervals", statement="""Merge all overlapping intervals. Intervals that touch (one ends exactly where the next starts) also merge. Print the merged intervals sorted by start.

Input: n, then n lines "start end" (start <= end).
Output: one merged interval per line as "start end".
Constraints: 1 <= n <= 20000, 0 <= start <= end <= 10^9.""",
    hint="Sort by start. Walk through them keeping the current merged interval: if the next interval starts at or before the current end, extend the end to the larger of the two; otherwise start a new one.",
    time="O(n log n)", space="O(n)", solve=merge_iv, gen=iv_gen,
    samples=["4\n1 3\n2 6\n8 10\n15 18\n", "2\n1 4\n4 5\n"], edges=["1\n5 5\n", "3\n1 10\n2 3\n4 5\n", "2\n5 6\n1 2\n"])


# 34 Jump Game
def jump(t):
    d = ints(t); a = d[1:1 + d[0]]; far = 0
    for i, v in enumerate(a):
        if i > far:
            return "NO"
        far = max(far, i + v)
    return "YES"


def jump_brute(t):
    d = ints(t); a = d[1:1 + d[0]]

    def f(i):
        return i >= len(a) - 1 or any(f(i + s) for s in range(1, a[i] + 1))
    return "YES" if f(0) else "NO"


def jump_gen(r):
    n = r.randint(1, 9); return f"{n}\n{A(r.choice([0, 0, 1, 2, 3]) for _ in range(n))}\n"


add(title="Jump Game", statement="""You start at index 0. From index i you may jump forward any distance from 1 to a[i]. Can you reach the last index?

Input: n, then n non-negative integers.
Output: YES or NO.
Constraints: 1 <= n <= 20000, 0 <= a[i] <= 10^5.""",
    hint="Track the farthest index reachable so far. If you ever stand on an index beyond that, you are stuck. Otherwise update farthest = max(farthest, i + a[i]).",
    time="O(n)", space="O(1)", solve=jump, gen=jump_gen, brute=jump_brute,
    samples=["5\n2 3 1 1 4\n", "5\n3 2 1 0 4\n"], edges=["1\n0\n", "2\n0 1\n", "3\n1 0 1\n"])


# 35 Longest Palindromic Substring (length)
def lpal(t):
    s = t.strip(); best = 1 if s else 0
    for c in range(len(s)):
        for l, r in ((c, c), (c, c + 1)):
            while l >= 0 and r < len(s) and s[l] == s[r]:
                l -= 1; r += 1
            best = max(best, r - l - 1)
    return str(best)


def lpal_brute(t):
    s = t.strip()
    return str(max(j - i for i in range(len(s)) for j in range(i + 1, len(s) + 1) if s[i:j] == s[i:j][::-1]))


add(title="Longest Palindromic Substring", statement="""Find the length of the longest contiguous substring that reads the same forwards and backwards.

Input: one line, a lowercase string (length 1 to 2000).
Output: the length.""",
    hint="Every palindrome has a centre (a character, or the gap between two). Expand outwards from each of the 2n-1 centres while the two ends match, and remember the best length.",
    time="O(n^2)", space="O(1)", solve=lpal, gen=lambda r: "".join(r.choice("ab") for _ in range(r.randint(1, 12))) + "\n", brute=lpal_brute,
    samples=["babad\n", "cbbd\n"], edges=["a\n", "ab\n", "aaaaaa\n", "abcba\n"])


# 36 House Robber
def robber(t):
    d = ints(t); a = d[1:1 + d[0]]; p = q = 0
    for v in a:
        p, q = q, max(q, p + v)
    return str(q)


def robber_brute(t):
    d = ints(t); a = d[1:1 + d[0]]

    def f(i):
        return 0 if i >= len(a) else max(a[i] + f(i + 2), f(i + 1))
    return str(f(0))


add(title="House Robber", statement="""Houses on a street hold the given amounts of money. You cannot rob two adjacent houses. Print the maximum amount you can rob.

Input: n, then n non-negative integers.
Constraints: 1 <= n <= 20000, 0 <= a[i] <= 10^4.""",
    hint="At each house choose: skip it (keep the best so far) or rob it (its money plus the best up to two houses back). Only the previous two results are needed.",
    time="O(n)", space="O(1)", solve=robber, brute=robber_brute,
    gen=lambda r: (lambda n: f"{n}\n{A(r.randint(0, 9) for _ in range(n))}\n")(r.randint(1, 10)),
    samples=["4\n1 2 3 1\n", "5\n2 7 9 3 1\n"], edges=["1\n5\n", "2\n3 9\n", "3\n0 0 0\n"])


# 37 Search in Rotated Sorted Array
def rsearch(t):
    d = ints(t); n, q = d[0], d[1]; a = d[2:2 + n]; qs = d[2 + n:2 + n + q]; out = []
    for x in qs:
        lo, hi, ans = 0, n - 1, -1
        while lo <= hi:
            m = (lo + hi) // 2
            if a[m] == x:
                ans = m; break
            if a[lo] <= a[m]:
                if a[lo] <= x < a[m]:
                    hi = m - 1
                else:
                    lo = m + 1
            else:
                if a[m] < x <= a[hi]:
                    lo = m + 1
                else:
                    hi = m - 1
        out.append(str(ans))
    return "\n".join(out)


def rsearch_brute(t):
    d = ints(t); n, q = d[0], d[1]; a = d[2:2 + n]; qs = d[2 + n:2 + n + q]
    return "\n".join(str(a.index(x)) if x in a else "-1" for x in qs)


def rs_gen(r, n=None, q=None, lim=40):
    n = n or r.randint(1, 9); q = q or r.randint(1, 6)
    a = sorted(r.sample(range(-lim, lim), n)); k = r.randrange(n); a = a[k:] + a[:k]
    qs = [r.choice(a) if r.random() < .5 else r.randint(-lim - 5, lim + 5) for _ in range(q)]
    return f"{n} {q}\n{A(a)}\n{A(qs)}\n"


add(title="Search in Rotated Sorted Array", statement="""A sorted array of distinct integers was rotated at an unknown pivot (for example 0 1 2 4 5 6 7 became 4 5 6 7 0 1 2). For each of q queries print the 0-based index of the value, or -1 if absent.

Input: first line n and q; second line the n integers; third line the q query values.
Output: q lines, one answer per query.
Constraints: 1 <= n, q <= 20000.""",
    hint="At every step, at least one half of [lo, hi] is properly sorted. Check which half is sorted, test whether the target lies inside that sorted half, and discard the other half. That keeps the binary search going.",
    time="O(q log n)", space="O(1)", solve=rsearch, gen=rs_gen, brute=rsearch_brute,
    samples=["7 3\n4 5 6 7 0 1 2\n0 3 6\n", "1 2\n1\n0 1\n"], edges=["2 3\n2 1\n1 2 3\n", "3 2\n3 1 2\n2 3\n"],
    big=lambda r: rs_gen(r, 20000, 20000, 10 ** 6), tl=3.0)


# 38 Kth Largest Element
def kth(t):
    d = ints(t); n, k = d[0], d[1]
    return str(sorted(d[2:2 + n], reverse=True)[k - 1])


def kth_gen(r):
    n = r.randint(1, 10); return f"{n} {r.randint(1, n)}\n{A(r.randint(-9, 9) for _ in range(n))}\n"


add(title="Kth Largest Element", statement="""Print the k-th largest value of the array (duplicates count separately: in 3 3 1 the 2nd largest is 3).

Input: first line n and k; second line n integers.
Constraints: 1 <= k <= n <= 20000, |a[i]| <= 10^9.""",
    hint="Sorting works in O(n log n). To do better keep a min-heap of the k largest values seen so far (its root is the answer), or use quickselect for O(n) on average.",
    time="O(n log k)", space="O(k)", solve=kth, gen=kth_gen,
    samples=["6 2\n3 2 1 5 6 4\n", "9 4\n3 2 3 1 2 4 5 5 6\n"], edges=["1 1\n7\n", "3 3\n3 3 1\n"])


# 39 Partition Equal Subset Sum
def partition(t):
    d = ints(t); a = d[1:1 + d[0]]; s = sum(a)
    if s % 2:
        return "NO"
    bits = 1
    for v in a:
        bits |= bits << v
    return "YES" if (bits >> (s // 2)) & 1 else "NO"


def partition_brute(t):
    d = ints(t); a = d[1:1 + d[0]]; s = sum(a)
    return "YES" if s % 2 == 0 and any(sum(c) == s // 2 for k in range(len(a) + 1) for c in itertools.combinations(a, k)) else "NO"


add(title="Partition Equal Subset Sum", statement="""Can the array be split into two groups (every element in exactly one group) with equal sums?

Input: n, then n positive integers.
Output: YES or NO.
Constraints: 1 <= n <= 200, 1 <= a[i] <= 100.""",
    hint="If the total is odd the answer is NO. Otherwise ask whether some subset sums to total/2. That is subset-sum: dp[x] is true if sum x can be made; process each number and update dp from high x to low x so each number is used once.",
    time="O(n * sum)", space="O(sum)", solve=partition, brute=partition_brute,
    gen=lambda r: (lambda n: f"{n}\n{A(r.randint(1, 9) for _ in range(n))}\n")(r.randint(1, 10)),
    samples=["4\n1 5 11 5\n", "4\n1 2 3 5\n"], edges=["1\n2\n", "2\n3 3\n", "200\n" + " ".join(["100"] * 200) + "\n"])


# 40 Minimum Path Sum
def minpath(t):
    r, c = ints(t.split("\n")[0]); g = [ints(x) for x in rows(t, r)]
    for i in range(r):
        for j in range(c):
            if i or j:
                g[i][j] += min(g[i - 1][j] if i else 10 ** 18, g[i][j - 1] if j else 10 ** 18)
    return str(g[r - 1][c - 1])


def minpath_brute(t):
    r, c = ints(t.split("\n")[0]); g = [ints(x) for x in rows(t, r)]

    def f(i, j):
        if i == r - 1 and j == c - 1:
            return g[i][j]
        best = min((f(a, b) for a, b in ((i + 1, j), (i, j + 1)) if a < r and b < c))
        return g[i][j] + best
    return str(f(0, 0))


def minpath_gen(r):
    h, w = r.randint(1, 4), r.randint(1, 4)
    return f"{h} {w}\n" + "\n".join(A(r.randint(0, 9) for _ in range(w)) for _ in range(h)) + "\n"


add(title="Minimum Path Sum", statement="""Travel from the top-left to the bottom-right of a grid of non-negative numbers, moving only right or down. Print the smallest possible sum of the numbers on the path (both end cells included).

Input: first line r and c; then r lines of c integers.
Constraints: 1 <= r, c <= 200, 0 <= value <= 100.""",
    hint="The cheapest way to reach a cell comes from the cell above or the cell to the left, whichever is cheaper: best[i][j] = grid[i][j] + min(best[i-1][j], best[i][j-1]). Fill the table row by row.",
    time="O(r * c)", space="O(1) extra (reuse the grid)", solve=minpath, gen=minpath_gen, brute=minpath_brute,
    samples=["3 3\n1 3 1\n1 5 1\n4 2 1\n", "2 3\n1 2 3\n4 5 6\n"], edges=["1 1\n7\n", "1 3\n1 2 3\n", "3 1\n1\n2\n3\n"])
