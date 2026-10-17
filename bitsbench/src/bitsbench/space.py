"""Finite hypothesis spaces with exact Bayesian inference.

Every BITS-Bench task draws its hidden rule uniformly from a finite, fully
enumerated set of semantically distinct hypotheses. That makes the posterior
after any sequence of experiments exact, so we can measure precisely how much
information an agent's experiments gathered and how much of it the agent used.
"""

from __future__ import annotations

from typing import Callable, Hashable, Sequence

import numpy as np

_CHUNK = 1 << 16


def binary_entropy(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=np.float64), 1e-12, 1 - 1e-12)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


class Space:
    """A finite set of hypotheses, each a deterministic function input -> output.

    ``table[h, j]`` is the output code of hypothesis ``h`` on ``pool[j]``; codes
    index ``vocab``. For domains whose pool is the whole input space, every
    input is in the pool. Otherwise ``fallback(x)`` executes all hypotheses on an
    out-of-pool input and returns their raw outputs.
    """

    def __init__(
        self,
        sources: Sequence[str],
        pool: Sequence[Hashable],
        table: np.ndarray,
        vocab: Sequence[Hashable],
        fallback: Callable[[Hashable], list] | None = None,
    ):
        self.sources = list(sources)
        self.pool = list(pool)
        self.pool_index = {x: j for j, x in enumerate(self.pool)}
        self.table = table
        self.vocab = list(vocab)
        self.code = {y: i for i, y in enumerate(self.vocab)}
        self.binary = len(self.vocab) == 2 and set(self.vocab) == {False, True}
        self._fallback = fallback
        self._extra: dict[Hashable, np.ndarray] = {}

    def __len__(self) -> int:
        return len(self.sources)

    @property
    def prior_bits(self) -> float:
        return float(np.log2(len(self)))

    def encode(self, y: Hashable) -> int:
        if y not in self.code:
            self.code[y] = len(self.vocab)
            self.vocab.append(y)
        return self.code[y]

    def column(self, x: Hashable) -> np.ndarray:
        """Output codes of every hypothesis on input ``x``."""
        j = self.pool_index.get(x)
        if j is not None:
            return self.table[:, j]
        if x not in self._extra:
            if self._fallback is None:
                raise KeyError(f"input {x!r} is outside this space's domain")
            self._extra[x] = np.array([self.encode(y) for y in self._fallback(x)], dtype=np.int32)
        return self._extra[x]

    def output(self, h: int, x: Hashable) -> Hashable:
        return self.vocab[int(self.column(x)[h])]


class Posterior:
    """Exact posterior over a ``Space`` under a uniform prior.

    With ``eps > 0`` (binary domains only) each observation is assumed to be the
    true output flipped independently with probability ``eps``.
    """

    def __init__(self, space: Space, eps: float = 0.0):
        if eps and not space.binary:
            raise ValueError("observation noise is only defined for binary outputs")
        self.space = space
        self.eps = float(eps)
        self.logw = np.zeros(len(space))
        self.n_obs = 0

    def copy(self) -> "Posterior":
        p = Posterior.__new__(Posterior)
        p.space, p.eps, p.logw, p.n_obs = self.space, self.eps, self.logw.copy(), self.n_obs
        return p

    def observe(self, x: Hashable, y: Hashable) -> None:
        match = self.space.column(x) == self.space.code.get(y, -1)
        if self.eps == 0:
            self.logw[~match] = -np.inf
        else:
            self.logw += np.where(match, np.log1p(-self.eps), np.log(self.eps))
        self.n_obs += 1

    def weights(self) -> np.ndarray:
        m = self.logw.max()
        if not np.isfinite(m):
            raise RuntimeError("posterior collapsed: observations inconsistent with every hypothesis")
        w = np.exp(self.logw - m)
        return w / w.sum()

    def entropy_bits(self) -> float:
        w = self.weights()
        w = w[w > 0]
        return float(-(w * np.log2(w)).sum())

    def bits_gained(self) -> float:
        return self.space.prior_bits - self.entropy_bits()

    def map_mass(self) -> float:
        return float(self.weights().max())

    def predictive(self, x: Hashable) -> np.ndarray:
        """Posterior predictive over output codes for the *true* f(x)."""
        col = self.space.column(x)
        return np.bincount(col, weights=self.weights(), minlength=len(self.space.vocab))

    def predict(self, x: Hashable) -> Hashable:
        """Bayes-optimal (maximum posterior predictive) guess of f(x)."""
        return self.space.vocab[int(np.argmax(self.predictive(x)))]

    def eig_of(self, x: Hashable) -> float:
        """Expected information gain (bits) of querying one input, in or out of the pool."""
        q = self.predictive(x)
        if self.space.binary and self.eps:
            p1 = (1 - self.eps) * q[1] + self.eps * q[0]
            return float(binary_entropy(np.array(p1)) - binary_entropy(np.array(self.eps)))
        q = q[q > 0]
        return float(max(0.0, -(q * np.log2(q)).sum()))

    def eig(self) -> np.ndarray:
        """Expected information gain (bits) of querying each pool input."""
        sp, w = self.space, self.weights()
        if sp.binary:
            p1 = _weighted_column_means(sp.table, w)
            if self.eps:
                p1 = (1 - self.eps) * p1 + self.eps * (1 - p1)
                return binary_entropy(p1) - binary_entropy(np.array(self.eps))
            return binary_entropy(p1)
        support = w > 0
        sub, ws = sp.table[support], w[support]
        out = np.empty(sub.shape[1])
        for j in range(sub.shape[1]):
            q = np.bincount(sub[:, j], weights=ws)
            q = q[q > 0]
            out[j] = -(q * np.log2(q)).sum()
        return out


def _weighted_column_means(table: np.ndarray, w: np.ndarray) -> np.ndarray:
    """``w @ table`` without materialising a float copy of a large table."""
    nz = np.flatnonzero(w)
    if len(nz) < len(w) // 2:
        return np.clip((w[nz] @ table[nz].astype(np.float64)), 0.0, 1.0)
    acc = np.zeros(table.shape[1], dtype=np.float64)
    for s in range(0, table.shape[0], _CHUNK):
        acc += w[s : s + _CHUNK].astype(np.float32) @ table[s : s + _CHUNK].astype(np.float32)
    return np.clip(acc, 0.0, 1.0)


def dedup_rows(table: np.ndarray, sources: Sequence[str]) -> tuple[np.ndarray, list[str]]:
    """Keep the first hypothesis of each semantic equivalence class (identical rows).

    Callers list hypotheses simplest-first, so each class is represented by its
    shortest description.
    """
    key = np.packbits(table.astype(bool), axis=1) if table.dtype == bool else table
    _, idx = np.unique(key, axis=0, return_index=True)
    idx = np.sort(idx)
    return table[idx], [sources[i] for i in idx]


def balanced(table: np.ndarray, lo: float = 0.1, hi: float = 0.9) -> np.ndarray:
    """Mask of binary hypotheses whose positive rate over the pool is in [lo, hi]."""
    r = table.mean(axis=1)
    return (r >= lo) & (r <= hi)
