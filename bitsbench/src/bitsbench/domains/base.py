"""Domain interface: a family of hidden rules plus the I/O conventions an agent sees."""

from __future__ import annotations

import ast
import hashlib
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Hashable

import numpy as np

from ..space import Space

CACHE_DIR = Path(os.environ.get("BITSBENCH_CACHE", Path.home() / ".cache" / "bitsbench"))


@dataclass(frozen=True)
class Level:
    name: str           # short id, e.g. "L2"
    summary: str        # one-line human summary for tables
    budget: int         # number of experiments
    n_test: int         # held-out prediction items per checkpoint


class Domain(ABC):
    """A benchmark domain.

    Subclasses define the hypothesis class at each level, how inputs/outputs are
    written, the test/random-experiment distribution, and how a submitted rule is
    turned into a function for exact-identification scoring.
    """

    name: str
    version: str = "1"
    levels: dict[str, Level]
    binary: bool = True
    input_format: str        # how the agent must write an input
    output_format: str       # how the agent must write an output in predictions
    rule_format: str         # how the agent must write its final rule

    _spaces: dict[str, Space]

    def __init__(self) -> None:
        self._spaces = {}

    # ---- hypothesis spaces -------------------------------------------------
    @abstractmethod
    def _build(self, level: str) -> Space: ...

    def space(self, level: str) -> Space:
        if level not in self._spaces:
            self._spaces[level] = self._load_or_build(level)
        return self._spaces[level]

    def _load_or_build(self, level: str) -> Space:
        if level not in self.levels:
            raise KeyError(f"{self.name} has no level {level!r}; choose from {list(self.levels)}")
        path = CACHE_DIR / f"{self.name}-{level}-v{self.version}.pkl"
        if path.exists():
            with path.open("rb") as f:
                sources, pool, table, vocab = pickle.load(f)
            return Space(sources, pool, table, vocab, fallback=self._fallback(level, sources))
        sp = self._build(level)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp{os.getpid()}")
        with tmp.open("wb") as f:
            pickle.dump((sp.sources, sp.pool, sp.table, sp.vocab), f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(path)
        return sp

    def _fallback(self, level: str, sources: list[str]) -> Callable[[Hashable], list] | None:
        """Executor for inputs outside the pool (only needed when the pool is not the full input space)."""
        return None

    # ---- prompts -----------------------------------------------------------
    @abstractmethod
    def describe(self, level: str) -> str:
        """Exact natural-language specification of the rule family at ``level``."""

    # ---- distributions -----------------------------------------------------
    @abstractmethod
    def sample_inputs(self, rng: np.random.Generator, n: int) -> list:
        """``n`` distinct inputs from the test distribution (also the random-experiment policy)."""

    def random_query(self, rng: np.random.Generator) -> Hashable:
        return self.sample_inputs(rng, 1)[0]

    # ---- formatting / parsing ----------------------------------------------
    @abstractmethod
    def fmt_input(self, x: Hashable) -> str: ...

    @abstractmethod
    def parse_input(self, text: str) -> Hashable:
        """Parse an agent-written input; raise ``ValueError`` with a helpful message if invalid."""

    def fmt_output(self, y: Hashable) -> str:
        return "true" if y else "false"

    def parse_output(self, value: Any) -> Hashable:
        """Coerce one element of a parsed PREDICTIONS list to an output; raise ValueError if impossible."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            v = value.strip().strip("'\"").lower()
            if v in ("true", "t", "1", "yes", "y"):
                return True
            if v in ("false", "f", "0", "no", "n"):
                return False
        raise ValueError(f"cannot read {value!r} as true/false")

    def parse_prediction_list(self, text: str) -> list:
        """Parse the bracketed list after ``PREDICTIONS:`` into raw Python values."""
        text = text.strip()
        try:
            return list(ast.literal_eval(text))
        except Exception:
            pass
        inner = text.strip()[1:-1] if text.startswith("[") and text.endswith("]") else text
        return [t.strip() for t in inner.split(",") if t.strip()]

    # ---- identification ------------------------------------------------------
    @abstractmethod
    def compile_rule(self, text: str) -> Callable[[Hashable], Hashable]:
        """Turn a submitted rule into a function; raise ``ValueError`` if it cannot be compiled."""

    def rule_matches(self, level: str, text: str, target: int) -> bool:
        """True iff the submitted rule agrees with the target on the entire pool."""
        sp = self.space(level)
        try:
            fn = self.compile_rule(text)
            return all(_safe_call(fn, x) == sp.output(target, x) for x in sp.pool)
        except Exception:
            return False


def _safe_call(fn: Callable, x: Hashable) -> Hashable:
    try:
        return fn(x)
    except Exception:
        return None


def stable_seed(*parts: object) -> int:
    h = hashlib.sha256("\x1f".join(map(str, parts)).encode()).digest()
    return int.from_bytes(h[:8], "little")
