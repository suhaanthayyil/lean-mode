"""Hidden list-transforming programs: pipelines of up to three primitives."""

from __future__ import annotations

import ast
import itertools
import re
from typing import Callable

import numpy as np

from ..space import Space, dedup_rows
from .base import Domain, Level

MAX_LEN, MAX_VAL = 6, 9


def _dedup(xs: list[int]) -> list[int]:
    seen: set[int] = set()
    return [v for v in xs if not (v in seen or seen.add(v))]


def _cumsum(xs: list[int]) -> list[int]:
    out, s = [], 0
    for v in xs:
        s = (s + v) % 10
        out.append(s)
    return out


# (name, description, function). Every function maps a list of ints 0..9 to a list of ints 0..9.
PRIMITIVES: list[tuple[str, str, Callable[[list[int]], list[int]]]] = [
    ("reverse", "reverse the list", lambda xs: xs[::-1]),
    ("sort", "sort in ascending order", sorted),
    ("sort_desc", "sort in descending order", lambda xs: sorted(xs, reverse=True)),
    ("dedup", "remove repeated values, keeping the first occurrence of each", _dedup),
    ("rotate_left", "move the first element to the end", lambda xs: xs[1:] + xs[:1]),
    ("rotate_right", "move the last element to the front", lambda xs: xs[-1:] + xs[:-1]),
    *[(f"take({k})", f"keep only the first {k} element(s)", lambda xs, k=k: xs[:k]) for k in (1, 2, 3)],
    *[(f"drop({k})", f"remove the first {k} element(s)", lambda xs, k=k: xs[k:]) for k in (1, 2)],
    *[(f"add({k})", f"add {k} to every element, modulo 10", lambda xs, k=k: [(v + k) % 10 for v in xs]) for k in (1, 2, 5)],
    *[(f"mul({k})", f"multiply every element by {k}, modulo 10", lambda xs, k=k: [(v * k) % 10 for v in xs]) for k in (2, 3)],
    ("keep_even", "keep only the even elements", lambda xs: [v for v in xs if v % 2 == 0]),
    ("keep_odd", "keep only the odd elements", lambda xs: [v for v in xs if v % 2 == 1]),
    ("keep_gt(4)", "keep only the elements greater than 4", lambda xs: [v for v in xs if v > 4]),
    ("keep_lt(5)", "keep only the elements less than 5", lambda xs: [v for v in xs if v < 5]),
    ("every_other", "keep the elements at positions 0, 2, 4, ... (first, third, fifth, ...)", lambda xs: xs[::2]),
    ("cumsum", "running sums modulo 10: [a, a+b, a+b+c, ...]", _cumsum),
    ("max", "the one-element list [largest element] (an empty list stays empty)", lambda xs: [max(xs)] if xs else []),
    ("min", "the one-element list [smallest element] (an empty list stays empty)", lambda xs: [min(xs)] if xs else []),
    ("sum", "the one-element list [sum of the elements modulo 10]", lambda xs: [sum(xs) % 10]),
    ("length", "the one-element list [number of elements]", lambda xs: [len(xs)]),
]
PRIM = {name: fn for name, _, fn in PRIMITIVES}


def _reference_pool() -> list[tuple[int, ...]]:
    """All lists of length 1..3 plus 400 fixed random lists of length 4..6."""
    pool = [tuple(t) for n in (1, 2, 3) for t in itertools.product(range(10), repeat=n)]
    rng = np.random.default_rng(20261017)
    extra: set[tuple[int, ...]] = set()
    while len(extra) < 400:
        extra.add(tuple(int(v) for v in rng.integers(0, 10, size=int(rng.integers(4, MAX_LEN + 1)))))
    return pool + sorted(extra, key=lambda t: (len(t), t))


def run_pipeline(names: list[str], xs: tuple[int, ...]) -> tuple[int, ...]:
    out = list(xs)
    for n in names:
        out = PRIM[n](out)
    return tuple(out)


class Lists(Domain):
    name = "lists"
    binary = False
    levels = {
        "L1": Level("L1", "one primitive", budget=8, n_test=15),
        "L2": Level("L2", "pipeline of <=2 primitives", budget=8, n_test=15),
        "L3": Level("L3", "pipeline of <=3 primitives", budget=8, n_test=15),
    }
    input_format = f"a list of 1 to {MAX_LEN} integers, each 0..{MAX_VAL}, e.g. `QUERY: [3, 1, 4, 1]`"
    output_format = "a list of integers, e.g. [1, 3]"
    rule_format = "a pipeline of primitive names separated by |, applied left to right, e.g. `RULE: sort | take(2) | add(1)`"

    def _build(self, level: str) -> Space:
        depth = {"L1": 1, "L2": 2, "L3": 3}[level]
        pool = _reference_pool()
        names = [n for n, _, _ in PRIMITIVES]
        vocab: dict[tuple[int, ...], int] = {}
        enc = lambda y: vocab.setdefault(y, len(vocab))  # noqa: E731
        srcs: list[str] = []
        rows: list[np.ndarray] = []
        frontier: list[tuple[list[str], list[list[int]]]] = [([], [list(x) for x in pool])]
        seen: set[bytes] = set()
        for d in range(depth):  # extend pipelines one primitive at a time
            nxt = []
            for prog, outs in frontier:
                for n in names:
                    new = [PRIM[n](o) for o in outs]
                    row = np.array([enc(tuple(o)) for o in new], dtype=np.int32)
                    key = row.tobytes()
                    if key in seen:  # equal on the pool => every extension is equal too
                        continue
                    seen.add(key)
                    srcs.append(" | ".join(prog + [n]))
                    rows.append(row)
                    if d + 1 < depth:
                        nxt.append((prog + [n], new))
            frontier = nxt
        table, srcs = dedup_rows(np.array(rows), srcs)
        inv = [None] * len(vocab)
        for y, i in vocab.items():
            inv[i] = y
        return Space(srcs, pool, table, inv, fallback=self._fallback(level, srcs))

    def _fallback(self, level, sources):
        progs = [s.split(" | ") for s in sources]
        return lambda x: [run_pipeline(p, x) for p in progs]

    def describe(self, level: str) -> str:
        depth = {"L1": "exactly one primitive", "L2": "one or two primitives", "L3": "one, two or three primitives"}[level]
        prims = "\n".join(f"  - {n:<13} {d}" for n, d, _ in PRIMITIVES)
        return (
            f"Inputs are lists of 1 to {MAX_LEN} integers, each between 0 and {MAX_VAL}. The output f(x) "
            "is another list of integers (possibly empty).\n\n"
            f"The hidden rule is a pipeline of {depth}, applied left to right (the output of each "
            "primitive is the input of the next). The primitives are:\n"
            f"{prims}\n\n"
            "Pipelines that compute the same function count as the same rule (we identify pipelines that "
            "agree on every list of length 1-3 and on a fixed set of 400 longer lists). The hidden rule was "
            "drawn uniformly at random from the set of distinct functions."
        )

    def sample_inputs(self, rng: np.random.Generator, n: int) -> list:
        out: set[tuple[int, ...]] = set()
        while len(out) < n:
            out.add(tuple(int(v) for v in rng.integers(0, 10, size=int(rng.integers(2, MAX_LEN + 1)))))
        return sorted(out, key=lambda t: rng.random())

    def fmt_input(self, x: tuple[int, ...]) -> str:
        return "[" + ", ".join(map(str, x)) + "]"

    def fmt_output(self, y: tuple[int, ...]) -> str:
        return self.fmt_input(y)

    def parse_input(self, text: str) -> tuple[int, ...]:
        s = text.strip().strip("`").strip()
        try:
            v = ast.literal_eval(s)
        except Exception:
            raise ValueError("expected a list of integers in square brackets, e.g. [3, 1, 4]") from None
        if not isinstance(v, (list, tuple)) or not all(isinstance(e, int) and not isinstance(e, bool) for e in v):
            raise ValueError("expected a list of integers in square brackets, e.g. [3, 1, 4]")
        if not 1 <= len(v) <= MAX_LEN:
            raise ValueError(f"the list must have between 1 and {MAX_LEN} elements")
        if not all(0 <= e <= MAX_VAL for e in v):
            raise ValueError(f"every element must be between 0 and {MAX_VAL}")
        return tuple(v)

    def parse_output(self, value) -> tuple[int, ...]:
        if isinstance(value, str):
            value = ast.literal_eval(value.strip())
        if isinstance(value, (list, tuple)) and all(isinstance(e, int) and not isinstance(e, bool) for e in value):
            return tuple(value)
        raise ValueError(f"cannot read {value!r} as a list of integers")

    def parse_prediction_list(self, text: str) -> list:
        v = ast.literal_eval(text.strip())
        if not isinstance(v, (list, tuple)):
            raise ValueError("expected a list of lists")
        return list(v)

    def compile_rule(self, text: str):
        toks = [re.sub(r"\s+", "", t) for t in text.strip().strip("`").split("|")]
        if not toks or any(t not in PRIM for t in toks):
            bad = [t for t in toks if t not in PRIM]
            raise ValueError(f"unknown primitive(s): {bad}")
        return lambda x: run_pipeline(toks, x)
