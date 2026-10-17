"""The number game: a hidden property of the integers 1..100.

After Tenenbaum's (1999) number game, extended with an exact hypothesis class so
that the Bayes-optimal learner is computable.
"""

from __future__ import annotations

import itertools
import math
import re

import numpy as np

from ..safe_eval import compile_expr
from ..space import Space, balanced, dedup_rows
from .base import Domain, Level

LO, HI = 1, 100
XS = np.arange(LO, HI + 1)


def is_prime(n: int) -> bool:
    return n > 1 and all(n % p for p in range(2, math.isqrt(n) + 1))


def is_square(n: int) -> bool:
    return math.isqrt(n) ** 2 == n


def digit_sum(n: int) -> int:
    return sum(map(int, str(n)))


def has_digit(n: int, d: int) -> bool:
    return str(d) in str(n)


def tens(n: int) -> int:
    return n // 10 % 10


HELPERS = {"is_prime": is_prime, "is_square": is_square, "digit_sum": digit_sum,
           "has_digit": has_digit, "tens": tens, "abs": abs, "min": min, "max": max}


def _atoms() -> list[tuple[str, np.ndarray]]:
    v = lambda f: np.array([f(int(x)) for x in XS], dtype=bool)  # noqa: E731
    out: list[tuple[str, np.ndarray]] = []
    for k in range(2, 11):
        for r in range(k):
            out.append((f"x % {k} == {r}", XS % k == r))
            out.append((f"x % {k} != {r}", XS % k != r))
    for t in range(5, 100, 5):
        out.append((f"x >= {t}", XS >= t))
        out.append((f"x < {t}", XS < t))
    for name, f in (("is_prime", is_prime), ("is_square", is_square)):
        out.append((f"{name}(x)", v(f)))
        out.append((f"not {name}(x)", ~v(f)))
    for d in range(10):
        out.append((f"has_digit(x, {d})", v(lambda n: has_digit(n, d))))
        out.append((f"not has_digit(x, {d})", ~v(lambda n: has_digit(n, d))))
    ds = np.array([digit_sum(int(x)) for x in XS])
    out.append(("digit_sum(x) % 2 == 0", ds % 2 == 0))
    out.append(("digit_sum(x) % 2 == 1", ds % 2 == 1))
    for s in range(4, 16, 2):
        out.append((f"digit_sum(x) >= {s}", ds >= s))
        out.append((f"digit_sum(x) < {s}", ds < s))
    tn = XS // 10 % 10
    for d in range(10):
        out.append((f"tens(x) == {d}", tn == d))
        out.append((f"tens(x) != {d}", tn != d))
    return out


class Numbers(Domain):
    name = "numbers"
    binary = True
    levels = {
        "L1": Level("L1", "single atomic property", budget=16, n_test=25),
        "L2": Level("L2", "AND/OR of two atomic properties", budget=16, n_test=25),
    }
    input_format = f"a single integer from {LO} to {HI}, e.g. `QUERY: 37`"
    output_format = "true or false"
    rule_format = ("a Python boolean expression in the variable x, using only arithmetic, comparisons, "
                   "and/or/not and the helpers is_prime, is_square, digit_sum, has_digit, tens; "
                   "e.g. `RULE: x % 3 == 0 and x >= 50`")

    def _build(self, level: str) -> Space:
        atoms = _atoms()
        srcs = [s for s, _ in atoms]
        rows = [r for _, r in atoms]
        if level == "L2":
            A = np.array([r for _, r in atoms])
            for i, j in itertools.combinations(range(len(atoms)), 2):
                srcs.append(f"({srcs[i]}) and ({srcs[j]})")
                rows.append(A[i] & A[j])
            for i, j in itertools.combinations(range(len(atoms)), 2):
                srcs.append(f"({srcs[i]}) or ({srcs[j]})")
                rows.append(A[i] | A[j])
        table = np.array(rows, dtype=bool)
        keep = balanced(table)
        table, srcs = dedup_rows(table[keep], [s for s, k in zip(srcs, keep) if k])
        return Space(srcs, [int(x) for x in XS], table.astype(np.uint8), [False, True])

    def describe(self, level: str) -> str:
        atoms = (
            "Atomic properties of an integer x (each also available negated):\n"
            "  - x % k == r            for k in 2..10 and 0 <= r < k   (negation: x % k != r)\n"
            "  - x >= t                for t in 5, 10, 15, ..., 95      (negation: x < t)\n"
            "  - is_prime(x)           x is a prime number\n"
            "  - is_square(x)          x is a perfect square\n"
            "  - has_digit(x, d)       the decimal digits of x include d, for d in 0..9\n"
            "  - digit_sum(x) % 2 == 0 the sum of the decimal digits of x is even (negation: odd)\n"
            "  - digit_sum(x) >= s     for s in 4, 6, 8, 10, 12, 14     (negation: digit_sum(x) < s)\n"
            "  - tens(x) == d          the tens digit of x, (x // 10) % 10, equals d, for d in 0..9\n"
        )
        shape = {
            "L1": "The hidden rule f(x) is exactly one atomic property (possibly negated).",
            "L2": ("The hidden rule f(x) is either one atomic property, or the AND or the OR of two "
                   "atomic properties (each possibly negated)."),
        }[level]
        return (
            f"Inputs are the integers {LO}..{HI}. The output f(x) is true or false.\n\n{atoms}\n{shape}\n"
            "Only rules that are true for at least 10% and at most 90% of the integers 1..100 are "
            "allowed. Rules that agree on every integer 1..100 count as the same rule; the hidden "
            "rule was drawn uniformly at random from the set of distinct allowed rules."
        )

    def sample_inputs(self, rng: np.random.Generator, n: int) -> list:
        return [int(v) for v in rng.choice(XS, size=n, replace=False)]

    def fmt_input(self, x: int) -> str:
        return str(x)

    def parse_input(self, text: str) -> int:
        m = re.fullmatch(r"\s*\(?\s*(-?\d+)\s*\)?\s*\.?\s*", text)
        if not m:
            raise ValueError(f"expected a single integer from {LO} to {HI}")
        x = int(m.group(1))
        if not LO <= x <= HI:
            raise ValueError(f"{x} is outside the allowed range {LO}..{HI}")
        return x

    def compile_rule(self, text: str):
        fn = compile_expr(text, ["x"], HELPERS)
        return lambda x: bool(fn(x=x))
