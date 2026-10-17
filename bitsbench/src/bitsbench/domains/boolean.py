"""Hidden Boolean functions of 8 input bits (a black-box logic circuit)."""

from __future__ import annotations

import itertools
import re

import numpy as np

from ..safe_eval import compile_expr
from ..space import Space, balanced, dedup_rows
from .base import Domain, Level

N = 8
POOL = ["".join(b) for b in itertools.product("01", repeat=N)]
BITS = np.array([[c == "1" for c in s] for s in POOL], dtype=bool)  # [256, N]
VARS = [f"x{i}" for i in range(N)]


def _literal_sets(max_k: int) -> list[list[tuple[str, np.ndarray, str, np.ndarray]]]:
    """For each k <= max_k: (conj_src, conj_row, disj_src, disj_row) over all k-literal sets."""
    out = []
    for k in range(1, max_k + 1):
        items = []
        for vs in itertools.combinations(range(N), k):
            for signs in itertools.product((True, False), repeat=k):
                lits = [f"x{v}" if s else f"not x{v}" for v, s in zip(vs, signs)]
                cols = [BITS[:, v] if s else ~BITS[:, v] for v, s in zip(vs, signs)]
                items.append((" and ".join(lits), np.logical_and.reduce(cols),
                              " or ".join(lits), np.logical_or.reduce(cols)))
        out.append(items)
    return out


class Boolean(Domain):
    name = "boolean"
    binary = True
    levels = {
        "L1": Level("L1", "AND or OR of <=3 literals", budget=16, n_test=25),
        "L2": Level("L2", "+ 2-term DNF / 2-clause CNF, <=2 literals each", budget=16, n_test=25),
        "L3": Level("L3", "+ 2-term DNF / 2-clause CNF, <=3 literals each", budget=24, n_test=25),
    }
    input_format = "8 bits x0..x7 written as a string of 0s and 1s, e.g. `QUERY: 01100101` (x0 is leftmost)"
    output_format = "true or false"
    rule_format = ("a Python boolean expression in the variables x0..x7 (each 0 or 1) using and/or/not, "
                   "e.g. `RULE: (x1 and not x4) or (x2 and x7)`")

    def _build(self, level: str) -> Space:
        sets = _literal_sets(3)
        srcs: list[str] = []
        rows: list[np.ndarray] = []
        for items in sets:  # AND / OR of 1..3 literals
            for cs, cr, ds, dr in items:
                srcs += [cs, ds]
                rows += [cr, dr]
        if level in ("L2", "L3"):
            for max_k in ((2,) if level == "L2" else (2, 3)):
                terms = [it for items in sets[:max_k] for it in items]
                lo = 0 if max_k == 2 else sum(len(s) for s in sets[:2])  # only new pairs at k=3
                for i, j in itertools.combinations(range(len(terms)), 2):
                    if max(i, j) < lo:
                        continue
                    (ci, cri, di, dri), (cj, crj, dj, drj) = terms[i], terms[j]
                    srcs += [f"({ci}) or ({cj})", f"({di}) and ({dj})"]
                    rows += [cri | crj, dri & drj]
        table = np.array(rows, dtype=bool)
        keep = balanced(table)
        table, srcs = dedup_rows(table[keep], [s for s, k in zip(srcs, keep) if k])
        return Space(srcs, POOL, table.astype(np.uint8), [False, True])

    def describe(self, level: str) -> str:
        base = ("Inputs are strings of 8 bits x0 x1 ... x7 (x0 is the leftmost character), so there are "
                "256 possible inputs. The output f(x) is true or false. A literal is a variable xi or its "
                "negation (not xi).\n\n")
        shape = {
            "L1": "The hidden rule is the AND of 1 to 3 literals, or the OR of 1 to 3 literals.",
            "L2": ("The hidden rule is one of:\n"
                   "  - the AND of 1 to 3 literals, or the OR of 1 to 3 literals;\n"
                   "  - an OR of two terms, each term an AND of 1 or 2 literals (e.g. (x1 and not x3) or x6);\n"
                   "  - an AND of two clauses, each clause an OR of 1 or 2 literals (e.g. (x0 or x5) and not x2)."),
            "L3": ("The hidden rule is one of:\n"
                   "  - the AND of 1 to 3 literals, or the OR of 1 to 3 literals;\n"
                   "  - an OR of two terms, each term an AND of 1 to 3 literals;\n"
                   "  - an AND of two clauses, each clause an OR of 1 to 3 literals."),
        }[level]
        return (base + shape + "\n\nOnly rules that are true on at least 10% and at most 90% of the 256 inputs "
                "are allowed. Rules that agree on all 256 inputs count as the same rule; the hidden rule was "
                "drawn uniformly at random from the set of distinct allowed rules.")

    def sample_inputs(self, rng: np.random.Generator, n: int) -> list:
        return [POOL[i] for i in rng.choice(len(POOL), size=n, replace=False)]

    def fmt_input(self, x: str) -> str:
        return x

    def parse_input(self, text: str) -> str:
        s = re.sub(r"[\s,\[\]()'\"`]", "", text)
        if not re.fullmatch(r"[01]+", s):
            raise ValueError("expected a string of 8 characters, each 0 or 1, e.g. 01100101")
        if len(s) != N:
            raise ValueError(f"expected exactly {N} bits but got {len(s)}")
        return s

    def compile_rule(self, text: str):
        fn = compile_expr(text, VARS, {})
        return lambda x: bool(fn(**{v: int(c) for v, c in zip(VARS, x)}))
