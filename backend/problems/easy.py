import bisect
from collections import Counter

from .base import A, Prob, ints

P = []


def add(**kw):
    P.append(Prob(difficulty="Easy", **kw))


# 1 Two Sum
def two_sum(t):
    d = ints(t); n, target = d[0], d[1]; a = d[2:2 + n]
    first = {}
    for j, v in enumerate(a):
        if target - v in first:
            return f"{first[target - v] + 1} {j + 1}"
        first.setdefault(v, j)
    return "-1 -1"


def two_sum_brute(t):
    d = ints(t); n, target = d[0], d[1]; a = d[2:2 + n]
    for j in range(n):
        for i in range(j):
            if a[i] + a[j] == target:
                return f"{i + 1} {j + 1}"


def two_sum_gen(r):
    n = r.randint(2, 10)
    a = [r.randint(-10, 10) for _ in range(n)]
    i, j = sorted(r.sample(range(n), 2))
    return f"{n} {a[i] + a[j]}\n{A(a)}\n"


def two_sum_big(r):
    n = 20000
    while True:
        a = r.sample(range(1, 10 ** 9), n)
        t = a[-2] + a[-1]
        have = set(a)
        # the only pair summing to t must be the last two, so quadratic solutions scan everything
        # (values are distinct, so exactly 2 values with a partner means exactly one valid pair)
        if sum(1 for v in a if t - v in have and t - v != v) == 2:
            return f"{n} {t}\n{A(a)}\n"


add(title="Two Sum", statement="""Given an array of n integers and a target, find two different positions i < j (1-based) with a[i] + a[j] = target.
A valid pair always exists. If there are several, print the pair whose second position j is smallest, and for that j the smallest i.

Input: first line n and target; second line the n integers.
Output: i and j separated by a space.
Constraints: 2 <= n <= 20000, |a[i]| <= 10^9.""",
    hint="Checking every pair is O(n^2) and too slow for n = 20000. For each number x, which value would you need to have seen already? A hash map from value to position answers that in O(1).",
    time="O(n)", space="O(n)", solve=two_sum, gen=two_sum_gen, brute=two_sum_brute,
    samples=["4 9\n2 7 11 15\n", "3 6\n3 2 4\n"], edges=["2 0\n0 0\n", "5 -3\n-1 -2 5 1 0\n"], big=two_sum_big, tl=3.0)


# 2 Valid Parentheses
def parens(t):
    st, pairs = [], {')': '(', ']': '[', '}': '{'}
    for c in t.strip():
        if c in '([{':
            st.append(c)
        elif not st or st.pop() != pairs[c]:
            return "NO"
    return "NO" if st else "YES"


def parens_brute(t):
    s = t.strip()
    while True:
        n = s.replace("()", "").replace("[]", "").replace("{}", "")
        if n == s:
            return "YES" if s == "" else "NO"
        s = n


def parens_gen(r):
    if r.random() < 0.5:
        close = {'(': ')', '[': ']', '{': '}'}
        st, out = [], []
        for _ in range(r.randint(1, 8)):
            if st and r.random() < 0.5:
                out.append(close[st.pop()])
            else:
                c = r.choice('([{'); st.append(c); out.append(c)
        while st:
            out.append(close[st.pop()])
        if r.random() < 0.4:
            out[r.randrange(len(out))] = r.choice(')]}([{')
        return "".join(out) + "\n"
    return "".join(r.choice('()[]{}') for _ in range(r.randint(1, 10))) + "\n"


add(title="Valid Parentheses", statement="""A string contains only the characters ( ) [ ] { }. It is valid if every opening bracket is closed by the same type of bracket, in the correct order.

Input: one line with the string (length 1 to 100000).
Output: YES if valid, otherwise NO.""",
    hint="Brackets close in the reverse order they opened, which is exactly how a stack behaves. Push openers; when you see a closer, the top of the stack must be its partner.",
    time="O(n)", space="O(n)", solve=parens, gen=parens_gen, brute=parens_brute,
    samples=["()[]{}\n", "([)]\n"], edges=["(\n", ")\n", "{[()]}\n", "((((((\n"])


# 3 Valid Palindrome
def palin(t):
    c = [x.lower() for x in t.rstrip("\n") if x.isalnum()]
    return "YES" if c == c[::-1] else "NO"


def palin_gen(r):
    letters = "abcAB12"
    if r.random() < 0.5:
        h = [r.choice(letters) for _ in range(r.randint(1, 5))]
        core = h + ([r.choice(letters)] if r.random() < 0.5 else []) + h[::-1]
        core = [c.swapcase() if r.random() < 0.3 else c for c in core]
    else:
        core = [r.choice(letters) for _ in range(r.randint(2, 8))]
    out = []
    for c in core:
        if r.random() < 0.3:
            out.append(r.choice(" ,.!:-"))
        out.append(c)
    return "".join(out) + "\n"


add(title="Valid Palindrome", statement="""Decide whether a sentence is a palindrome when you consider only letters and digits and ignore upper/lower case.

Input: one line (it may contain spaces and punctuation, and has at least one letter or digit).
Output: YES or NO.""",
    hint="Keep two pointers, one at each end, and skip anything that is not a letter or digit. Compare lower-cased characters. You can do it without building a second string.",
    time="O(n)", space="O(1)", solve=palin, gen=palin_gen,
    samples=["A man, a plan, a canal: Panama\n", "race a car\n"], edges=["a\n", "0P\n", ".,a,.\n"])


# 4 Maximum Subarray
def kadane(t):
    d = ints(t); a = d[1:1 + d[0]]; best = cur = a[0]
    for v in a[1:]:
        cur = max(v, cur + v); best = max(best, cur)
    return str(best)


def kadane_brute(t):
    d = ints(t); a = d[1:1 + d[0]]
    return str(max(sum(a[i:j]) for i in range(len(a)) for j in range(i + 1, len(a) + 1)))


def kadane_gen(r, n=None, lim=10):
    n = n or r.randint(1, 10)
    return f"{n}\n{A(r.randint(-lim, lim) for _ in range(n))}\n"


add(title="Maximum Subarray", statement="""Find the largest possible sum of a non-empty contiguous part of the array.

Input: n on the first line, then n integers.
Output: the maximum sum.
Constraints: 1 <= n <= 20000, |a[i]| <= 10000.""",
    hint="Walk left to right and track the best sum of a subarray that ends at the current element. At each step either extend the previous run or start fresh at this element, whichever is larger.",
    time="O(n)", space="O(1)", solve=kadane, gen=kadane_gen, brute=kadane_brute,
    samples=["9\n-2 1 -3 4 -1 2 1 -5 4\n", "1\n5\n"], edges=["3\n-3 -1 -2\n", "4\n1 2 3 4\n"],
    big=lambda r: kadane_gen(r, 20000, 10000), tl=3.0)


# 5 Best Time to Buy and Sell Stock
def stock(t):
    d = ints(t); a = d[1:1 + d[0]]; lo = a[0]; best = 0
    for v in a:
        lo = min(lo, v); best = max(best, v - lo)
    return str(best)


def stock_brute(t):
    d = ints(t); a = d[1:1 + d[0]]
    return str(max([0] + [a[j] - a[i] for i in range(len(a)) for j in range(i + 1, len(a))]))


def stock_gen(r, n=None, lim=20):
    n = n or r.randint(1, 10)
    return f"{n}\n{A(r.randint(0, lim) for _ in range(n))}\n"


add(title="Best Time to Buy and Sell Stock", statement="""Prices of a stock on n consecutive days are given. You may buy on one day and sell on a later day, once. Print the maximum profit, or 0 if no profit is possible.

Input: n, then n prices.
Output: the maximum profit.
Constraints: 1 <= n <= 20000, 0 <= price <= 10^9.""",
    hint="For each day as the selling day, the best buy day is the cheapest price seen so far. Keep a running minimum while scanning once.",
    time="O(n)", space="O(1)", solve=stock, gen=stock_gen, brute=stock_brute,
    samples=["6\n7 1 5 3 6 4\n", "5\n7 6 4 3 1\n"], edges=["1\n5\n", "2\n1 2\n"],
    big=lambda r: stock_gen(r, 20000, 10 ** 9), tl=3.0)


# 6 Contains Duplicate
def dup(t):
    d = ints(t); a = d[1:1 + d[0]]
    return "YES" if len(set(a)) != len(a) else "NO"


def dup_gen(r):
    n = r.randint(1, 8)
    a = r.sample(range(-12, 12), n) if r.random() < 0.5 else [r.randint(-12, 12) for _ in range(n)]
    return f"{n}\n{A(a)}\n"


add(title="Contains Duplicate", statement="""Print YES if some value appears at least twice in the array, otherwise NO.

Input: n, then n integers.
Constraints: 1 <= n <= 20000, |a[i]| <= 10^9.""",
    hint="Remember what you have already seen. A set lets you check membership in O(1) as you scan. Sorting also works if you compare neighbours.",
    time="O(n)", space="O(n)", solve=dup, gen=dup_gen,
    samples=["4\n1 2 3 1\n", "4\n1 2 3 4\n"], edges=["1\n7\n", "2\n5 5\n"],
    big=lambda r: f"20000\n{A(r.sample(range(-10**9, 10**9), 20000))}\n", tl=3.0)


# 7 Valid Anagram
def anagram(t):
    s, u = t.split()
    return "YES" if sorted(s) == sorted(u) else "NO"


def anagram_gen(r):
    s = "".join(r.choice("abc") for _ in range(r.randint(1, 6)))
    u = list(s); r.shuffle(u)
    if r.random() < 0.4:
        u[r.randrange(len(u))] = r.choice("abcd")
    if r.random() < 0.2:
        u.append("a")
    return f"{s}\n{''.join(u)}\n"


add(title="Valid Anagram", statement="""Two lowercase words are anagrams if one can be rearranged into the other using every letter exactly once.

Input: two lines, the words s and t (length 1 to 50000).
Output: YES or NO.""",
    hint="Anagrams have identical letter counts. Count the 26 letters of s, subtract those of t, and check everything is zero. Different lengths can never match.",
    time="O(n)", space="O(1)", solve=anagram, gen=anagram_gen,
    samples=["anagram\nnagaram\n", "rat\ncar\n"], edges=["a\na\n", "ab\nabc\n"])


# 8 Reverse Integer
def rev_int(t):
    x = int(t); r = int(str(abs(x))[::-1]) * (1 if x >= 0 else -1)
    return str(r) if -2 ** 31 <= r <= 2 ** 31 - 1 else "0"


def rev_gen(r):
    return str(r.choice([-1, 1]) * r.randint(0, 10 ** r.randint(0, 9))) + "\n"


add(title="Reverse Integer", statement="""Reverse the digits of a 32-bit signed integer, keeping its sign (trailing zeros disappear: 120 becomes 21). If the reversed value does not fit in a signed 32-bit integer (-2147483648 to 2147483647), print 0.

Input: one integer x with -2^31 <= x <= 2^31 - 1.
Output: the reversed integer, or 0 on overflow.""",
    hint="Peel digits off with x % 10 and x // 10, pushing them onto a result with result * 10 + digit. Check the 32-bit range at the end (or before each multiply in languages with fixed-size ints).",
    time="O(log x)", space="O(1)", solve=rev_int, gen=rev_gen,
    samples=["123\n", "-120\n"], edges=["0\n", "1534236469\n", "-2147483648\n", "2147483647\n", "1463847412\n"])


# 9 Missing Number
def missing(t):
    d = ints(t); n = d[0]; return str(n * (n + 1) // 2 - sum(d[1:1 + n]))


def missing_gen(r):
    n = r.randint(1, 9)
    a = list(range(n + 1)); a.remove(r.choice(a)); r.shuffle(a)
    return f"{n}\n{A(a)}\n"


add(title="Missing Number", statement="""An array holds n distinct integers taken from 0..n, so exactly one number of that range is missing. Print it.

Input: n, then n integers.
Constraints: 1 <= n <= 20000.""",
    hint="The numbers 0..n add up to n(n+1)/2. Subtract the sum of the array. XOR-ing all indices and values also works and avoids overflow in fixed-size integer languages.",
    time="O(n)", space="O(1)", solve=missing, gen=missing_gen,
    samples=["3\n3 0 1\n", "2\n0 1\n"], edges=["1\n0\n", "1\n1\n"])


# 10 Single Number
def single(t):
    d = ints(t); a = d[1:1 + d[0]]; c = Counter(a)
    return str(next(v for v in c if c[v] == 1))


def single_gen(r):
    k = r.randint(0, 5); vals = r.sample(range(-9, 10), k + 1)
    a = vals[:k] * 2 + [vals[k]]; r.shuffle(a)
    return f"{len(a)}\n{A(a)}\n"


add(title="Single Number", statement="""Every value in the array appears exactly twice, except one value that appears once. Print that value.

Input: n (odd), then n integers.
Constraints: 1 <= n <= 20001, |a[i]| <= 10^9.""",
    hint="A value XOR itself is 0, and XOR is order-independent. XOR the whole array and the pairs cancel, leaving the single number. No extra memory needed.",
    time="O(n)", space="O(1)", solve=single, gen=single_gen,
    samples=["3\n2 2 1\n", "5\n4 1 2 1 2\n"], edges=["1\n-7\n", "3\n-1 5 -1\n"])


# 11 Majority Element
def majority(t):
    d = ints(t); a = d[1:1 + d[0]]; c = Counter(a)
    return str(c.most_common(1)[0][0])


def majority_gen(r):
    n = r.randint(1, 11); x = r.randint(-5, 5)
    a = [x] * (n // 2 + 1) + [r.randint(-5, 5) for _ in range(n - n // 2 - 1)]; r.shuffle(a)
    return f"{n}\n{A(a)}\n"


add(title="Majority Element", statement="""A majority element appears more than n/2 times. The array is guaranteed to have one; print it.

Input: n, then n integers.
Constraints: 1 <= n <= 20000.""",
    hint="Boyer-Moore voting: keep a candidate and a counter. Same value as candidate: counter up; different: counter down; at zero take a new candidate. The majority can never be fully cancelled out.",
    time="O(n)", space="O(1)", solve=majority, gen=majority_gen,
    samples=["3\n3 2 3\n", "7\n2 2 1 1 1 2 2\n"], edges=["1\n9\n", "2\n4 4\n"])


# 12 Move Zeroes
def move_zeroes(t):
    d = ints(t); a = d[1:1 + d[0]]
    return A([v for v in a if v] + [0] * a.count(0))


def mz_gen(r):
    n = r.randint(1, 10); return f"{n}\n{A(r.choice([0, 0, r.randint(-9, 9)]) for _ in range(n))}\n"


add(title="Move Zeroes", statement="""Move every 0 to the end of the array while keeping the relative order of the non-zero elements.

Input: n, then n integers.
Output: the resulting array on one line, space separated.
Constraints: 1 <= n <= 20000.""",
    hint="Use a write pointer for the next non-zero slot. Scan once, copying each non-zero value to the write pointer; afterwards fill the rest with zeros.",
    time="O(n)", space="O(1)", solve=move_zeroes, gen=mz_gen,
    samples=["5\n0 1 0 3 12\n", "1\n0\n"], edges=["3\n1 2 3\n", "3\n0 0 0\n"])


# 13 Climbing Stairs
def stairs(t):
    n = int(t); a, b = 1, 2
    for _ in range(n - 1):
        a, b = b, a + b
    return str(a)


add(title="Climbing Stairs", statement="""You climb a staircase of n steps taking 1 or 2 steps at a time. In how many distinct ways can you reach the top?

Input: one integer n, 1 <= n <= 45.
Output: the number of ways.""",
    hint="To stand on step n you came from step n-1 or n-2, so ways(n) = ways(n-1) + ways(n-2). That is Fibonacci; keep only the last two values.",
    time="O(n)", space="O(1)", solve=stairs, gen=lambda r: f"{r.randint(1, 45)}\n",
    samples=["2\n", "3\n"], edges=["1\n", "45\n", "44\n"])


# 14 Merge Two Sorted Arrays
def merge2(t):
    d = ints(t); n, m = d[0], d[1]; a = d[2:2 + n]; b = d[2 + n:2 + n + m]
    i = j = 0; out = []
    while i < n or j < m:
        if j >= m or (i < n and a[i] <= b[j]):
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    return A(out)


def merge2_brute(t):
    d = ints(t); n, m = d[0], d[1]
    return A(sorted(d[2:2 + n + m]))


def merge2_gen(r):
    n, m = r.randint(1, 6), r.randint(1, 6)
    a = sorted(r.randint(-9, 9) for _ in range(n)); b = sorted(r.randint(-9, 9) for _ in range(m))
    return f"{n} {m}\n{A(a)}\n{A(b)}\n"


add(title="Merge Two Sorted Arrays", statement="""Merge two arrays that are each sorted in non-decreasing order into one sorted array.

Input: first line n and m; second line n integers; third line m integers.
Output: the merged array, space separated.
Constraints: 1 <= n, m <= 20000.""",
    hint="Use one pointer per array and always take the smaller front element. When one array runs out, append the rest of the other. No need to sort again.",
    time="O(n + m)", space="O(n + m)", solve=merge2, gen=merge2_gen, brute=merge2_brute,
    samples=["3 3\n1 2 4\n1 3 4\n", "1 2\n5\n1 9\n"], edges=["1 1\n2 2\n", "2 1\n1 2\n3\n"])


# 15 Longest Common Prefix
def lcp(t):
    w = t.split("\n")[1].split(); p = w[0]
    for s in w[1:]:
        while not s.startswith(p):
            p = p[:-1]
    return p or "EMPTY"


def lcp_gen(r):
    pre = "".join(r.choice("ab") for _ in range(r.randint(0, 4))); n = r.randint(1, 5)
    ws = [pre + "".join(r.choice("abc") for _ in range(r.randint(1, 4))) for _ in range(n)]
    return f"{n}\n{' '.join(ws)}\n"


add(title="Longest Common Prefix", statement="""Find the longest string that is a prefix of every given word. If there is none, print EMPTY.

Input: n on the first line; the n lowercase words, space separated, on the second line.
Constraints: 1 <= n <= 200, word length 1 to 200.""",
    hint="The common prefix can be no longer than the shortest word. Start with the first word as the candidate and shorten it until each next word starts with it.",
    time="O(total characters)", space="O(1)", solve=lcp, gen=lcp_gen,
    samples=["3\nflower flow flight\n", "3\ndog racecar car\n"], edges=["1\nabc\n", "2\nab ab\n"])


# 16 Roman to Integer
ROM = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def roman(t):
    s = t.strip(); tot = 0
    for i, c in enumerate(s):
        v = ROM[c]
        tot += -v if i + 1 < len(s) and ROM[s[i + 1]] > v else v
    return str(tot)


def to_roman(n):
    out = ""
    for v, s in [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                 (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out += s; n -= v
    return out


def roman_brute(t):
    # inverse check: converting the answer back must reproduce the input
    return str(next(n for n in range(1, 4000) if to_roman(n) == t.strip()))


add(title="Roman to Integer", statement="""Convert a valid Roman numeral to an integer. Symbols: I=1 V=5 X=10 L=50 C=100 D=500 M=1000. A smaller symbol before a larger one is subtracted (IV = 4, IX = 9, XL = 40, XC = 90, CD = 400, CM = 900).

Input: one Roman numeral representing 1..3999.
Output: its value.""",
    hint="Scan left to right. If the current symbol is smaller than the next one, subtract it; otherwise add it.",
    time="O(n)", space="O(1)", solve=roman, gen=lambda r: to_roman(r.randint(1, 3999)) + "\n", brute=roman_brute,
    samples=["III\n", "MCMXCIV\n"], edges=["IV\n", "MMMCMXCIX\n", "LVIII\n"])


# 17 Binary Search Queries
def bsearch(t):
    d = ints(t); n, q = d[0], d[1]; a = d[2:2 + n]; qs = d[2 + n:2 + n + q]; out = []
    for x in qs:
        i = bisect.bisect_left(a, x); out.append(str(i if i < n and a[i] == x else -1))
    return "\n".join(out)


def bsearch_brute(t):
    d = ints(t); n, q = d[0], d[1]; a = d[2:2 + n]; qs = d[2 + n:2 + n + q]
    return "\n".join(str(a.index(x)) if x in a else "-1" for x in qs)


def bs_gen(r, n=None, q=None, lim=40):
    n = n or r.randint(1, 8); q = q or r.randint(1, 6)
    a = sorted(r.sample(range(-lim, lim), n))
    qs = [r.choice(a) if r.random() < .5 else r.randint(-lim - 5, lim + 5) for _ in range(q)]
    return f"{n} {q}\n{A(a)}\n{A(qs)}\n"


add(title="Binary Search Queries", statement="""A sorted array of distinct integers is given, followed by q queries. For each query value print its 0-based index in the array, or -1 if it is absent.

Input: first line n and q; second line the n sorted integers; third line the q query values.
Output: q lines, one answer per query.
Constraints: 1 <= n, q <= 20000, |values| <= 10^9.""",
    hint="The array is sorted, so each query can halve the search range: compare with the middle element and discard one half. A linear scan per query is O(n*q) = 4*10^8 operations at the limit.",
    time="O(q log n)", space="O(1)", solve=bsearch, gen=bs_gen, brute=bsearch_brute,
    samples=["5 3\n-1 0 3 5 9\n9 2 -1\n", "1 2\n4\n4 5\n"], edges=["2 2\n1 2\n0 3\n"],
    big=lambda r: bs_gen(r, 20000, 20000, 10 ** 6), tl=3.0)
