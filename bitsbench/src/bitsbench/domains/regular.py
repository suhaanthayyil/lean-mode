"""Hidden regular languages over {a, b}, recognised by small DFAs."""

from __future__ import annotations

import itertools
import re

import numpy as np

from ..space import Space
from .base import Domain, Level

MAX_LEN = 8
POOL = ["".join(s) for n in range(1, MAX_LEN + 1) for s in itertools.product("ab", repeat=n)]


def _dfa_source(delta: np.ndarray, accept: tuple[int, ...]) -> str:
    k = len(delta)
    trans = "; ".join(f"q{q}: a->q{delta[q, 0]} b->q{delta[q, 1]}" for q in range(k))
    acc = ", ".join(f"q{q}" for q in accept) or "none"
    return f"DFA[{k} states, start q0, accept {{{acc}}}; {trans}]"


def _states_after(deltas: np.ndarray) -> np.ndarray:
    """State reached by every DFA on every pool string: int8 [n_dfa, len(POOL)]."""
    rows = np.arange(len(deltas))
    state = {"": np.zeros(len(deltas), np.int8)}
    for s in POOL:  # POOL is ordered so prefixes come first
        state[s] = deltas[rows, state[s[:-1]], 0 if s[-1] == "a" else 1]
    return np.stack([state[s] for s in POOL], axis=1)


class Regular(Domain):
    name = "regular"
    binary = True
    levels = {
        "L1": Level("L1", "DFA with <=3 states", budget=16, n_test=25),
        "L2": Level("L2", "DFA with <=4 states", budget=16, n_test=25),
    }
    input_format = f"a string of 1 to {MAX_LEN} characters, each a or b, e.g. `QUERY: abba`"
    output_format = "true or false"
    rule_format = ("either a Python regular expression matching exactly the strings in the language "
                   "(tested with re.fullmatch), e.g. `RULE: (a|b)*ab`, or a DFA written as "
                   "`RULE: DFA[start q0, accept {q1}; q0: a->q0 b->q1; q1: a->q0 b->q1]`")

    def _build(self, level: str) -> Space:
        max_states = {"L1": 3, "L2": 4}[level]
        lo, hi = 0.1 * len(POOL), 0.9 * len(POOL)
        seen: set[bytes] = set()
        rows: list[np.ndarray] = []
        srcs: list[str] = []
        for k in range(1, max_states + 1):  # fewest states first => minimal representatives
            deltas = np.array(list(itertools.product(range(k), repeat=2 * k)), dtype=np.int8).reshape(-1, k, 2)
            states = _states_after(deltas)
            for accept in itertools.product((False, True), repeat=k):
                acc = np.array(accept)
                member = acc[states]
                cnt = member.sum(axis=1)
                ok = np.flatnonzero((cnt >= lo) & (cnt <= hi))
                if len(ok) == 0:
                    continue
                packed = np.packbits(member[ok], axis=1)
                _, first = np.unique(packed, axis=0, return_index=True)
                for i in np.sort(first):
                    key = packed[i].tobytes()
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(member[ok[i]])
                    srcs.append(_dfa_source(deltas[ok[i]], tuple(q for q in range(k) if accept[q])))
        return Space(srcs, POOL, np.array(rows, dtype=np.uint8), [False, True])

    def describe(self, level: str) -> str:
        k = {"L1": 3, "L2": 4}[level]
        return (
            f"Inputs are strings of length 1 to {MAX_LEN} over the alphabet {{a, b}} "
            f"({len(POOL)} possible inputs). The output f(s) is true if s belongs to a hidden regular "
            f"language L and false otherwise.\n\n"
            f"L is recognised by a deterministic finite automaton (DFA) with at most {k} states: a start "
            "state, a transition on a and on b from every state, and a set of accepting states. Examples "
            "of such languages: strings ending in b; strings with an even number of a's; strings "
            "containing ab; strings whose length is a multiple of 3.\n\n"
            f"Only languages containing at least 10% and at most 90% of the {len(POOL)} possible inputs "
            f"are allowed. Languages that agree on every string of length 1 to {MAX_LEN} count as the "
            "same; the hidden language was drawn uniformly at random from the set of distinct allowed "
            "languages."
        )

    def sample_inputs(self, rng: np.random.Generator, n: int) -> list:
        return [POOL[i] for i in rng.choice(len(POOL), size=n, replace=False)]

    def fmt_input(self, x: str) -> str:
        return x

    def parse_input(self, text: str) -> str:
        s = text.strip().strip("`'\"").strip()
        if not re.fullmatch(r"[ab]+", s):
            raise ValueError("expected a non-empty string made only of the letters a and b")
        if len(s) > MAX_LEN:
            raise ValueError(f"string is longer than {MAX_LEN} characters")
        return s

    def compile_rule(self, text: str):
        src = text.strip().strip("`").strip()
        if src.upper().startswith("DFA"):
            return _compile_dfa(src)
        if len(src) > 500:
            raise ValueError("regular expression too long")
        try:
            pat = re.compile(src)
        except re.error as e:
            raise ValueError(f"invalid regular expression: {e}") from None
        return lambda s: pat.fullmatch(s) is not None


def _compile_dfa(src: str):
    """Parse the ``DFA[start q0, accept {...}; q0: a->q1 b->q0; ...]`` notation used for rule sources."""
    trans = {int(q): (int(a), int(b)) for q, a, b in re.findall(r"q(\d+)\s*:\s*a\s*->\s*q(\d+)\s*,?\s*b\s*->\s*q(\d+)", src)}
    m_acc = re.search(r"accept\s*\{([^}]*)\}", src)
    m_start = re.search(r"start\s*q(\d+)", src)
    if not trans or m_acc is None:
        raise ValueError("could not read the DFA: expected 'accept {...}' and transitions like 'q0: a->q1 b->q0'")
    accept = {int(q) for q in re.findall(r"q(\d+)", m_acc.group(1))}
    start = int(m_start.group(1)) if m_start else 0
    if any(a not in trans or b not in trans for a, b in trans.values()) or start not in trans:
        raise ValueError("every state used must have its own transitions")

    def run(s: str) -> bool:
        q = start
        for ch in s:
            q = trans[q][0 if ch == "a" else 1]
        return q in accept

    return run
