"""Episode generation: deterministic, seeded, with a private-salt test split."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Hashable, Iterable

import numpy as np

from . import __version__
from .domains import all_configs, get_domain
from .domains.base import stable_seed


@dataclass
class Episode:
    id: str
    split: str
    domain: str
    level: str
    eps: float
    index: int
    seed: int
    target: int
    target_source: str
    test_inputs: list
    budget: int
    checkpoints: list[int]
    space_size: int
    version: str = __version__
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: dict) -> "Episode":
        ep = cls(**d)
        ep.test_inputs = [_restore(ep.domain, x) for x in ep.test_inputs]
        return ep


def _restore(domain: str, x: Hashable) -> Hashable:
    return tuple(x) if isinstance(x, list) else x


def checkpoints_for(budget: int) -> list[int]:
    return sorted({max(1, budget // 8), max(1, budget // 4), max(1, budget // 2), budget})


def _salt(split: str) -> str:
    if split == "dev":
        return "public-dev"
    if split == "test":
        salt = os.environ.get("BITSBENCH_TEST_SALT")
        if not salt:
            raise RuntimeError("the test split needs the private salt in $BITSBENCH_TEST_SALT")
        return salt
    return split  # any other name is its own public split (e.g. "pilot")


def make_episode(split: str, domain: str, level: str, index: int, eps: float = 0.0) -> Episode:
    d = get_domain(domain)
    if eps and not d.binary:
        raise ValueError(f"noise is only supported for binary domains, not {domain}")
    sp = d.space(level)
    lv = d.levels[level]
    seed = stable_seed("bitsbench", split, _salt(split), domain, level, f"{eps:g}", index)
    rng = np.random.default_rng(seed)
    target = int(rng.integers(len(sp)))
    tests = d.sample_inputs(rng, lv.n_test)
    eid = f"{split}/{domain}/{level}/eps{eps:g}/{index:04d}"
    return Episode(eid, split, domain, level, float(eps), index, seed, target, sp.sources[target],
                   tests, lv.budget, checkpoints_for(lv.budget), len(sp))


# A suite is a list of (domain, level, eps, n_episodes).
SUITES: dict[str, list[tuple[str, str, float, int]]] = {
    "core": [(d, lv, 0.0, 30) for d, lv in all_configs()],
    "noisy": [(d, lv, 0.1, 30) for d, lv in all_configs() if d != "lists" and lv == "L1"],
    "mini": [(d, lv, 0.0, 3) for d, lv in all_configs()],
}


def make_suite(suite: str, split: str = "dev", n: int | None = None) -> list[Episode]:
    eps_list = []
    for domain, level, eps, k in SUITES[suite]:
        for i in range(n if n is not None else k):
            eps_list.append(make_episode(split, domain, level, i, eps))
    return eps_list


def save_episodes(episodes: Iterable[Episode], path: Path, include_targets: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for ep in episodes:
            d = ep.to_json()
            if not include_targets:
                d["target"], d["target_source"] = None, None
            f.write(json.dumps(d) + "\n")


def load_episodes(path: Path) -> list[Episode]:
    with path.open() as f:
        return [Episode.from_json(json.loads(line)) for line in f if line.strip()]


def noise_flip(ep: Episode, t: int, eps: float) -> bool:
    """Whether the oracle corrupts experiment ``t`` (1-based); deterministic per episode."""
    return eps > 0 and np.random.default_rng([ep.seed & 0xFFFFFFFF, 0x6E6F697365, t]).random() < eps


class Oracle:
    """The black box: answers experiments with the target's (possibly noisy) output."""

    def __init__(self, ep: Episode, stream: int = 0):
        self.ep = ep
        self.domain = get_domain(ep.domain)
        self.space = self.domain.space(ep.level)
        self.stream = stream  # reference agents use distinct noise streams per run

    def truth(self, x: Hashable) -> Hashable:
        return self.space.output(self.ep.target, x)

    def query(self, x: Hashable, t: int) -> Hashable:
        y = self.truth(x)
        if self.ep.eps and noise_flip(self.ep, t + 1000 * self.stream, self.ep.eps):
            y = not y
        return y
