"""Reference agents with exact Bayesian inference.

``RandomAgent`` runs experiments drawn from the test distribution;
``EIGAgent`` greedily maximises expected information gain over the domain's
query pool. Both predict with the Bayes-optimal rule (posterior-predictive
mode), so their accuracy is the best achievable from the data they collected.
"""

from __future__ import annotations

import zlib
from typing import Hashable

import numpy as np

from ..space import Posterior
from .base import Agent, Obs, Prediction


class BayesAgent(Agent):
    name = "bayes"

    def __init__(self, seed: int = 0):
        self.seed = seed

    def begin(self, ep, domain, mode):
        super().begin(ep, domain, mode)
        self.space = domain.space(ep.level)
        self.post = Posterior(self.space, ep.eps)
        self.rng = np.random.default_rng([ep.seed & 0xFFFFFFFF, self.seed, zlib.crc32(self.name.encode())])
        self._seen = 0

    def _sync(self, history: list[Obs]) -> None:
        if len(history) < self._seen:  # a fresh, shorter history (passive checkpoints)
            self.post, self._seen = Posterior(self.space, self.ep.eps), 0
        for o in history[self._seen:]:
            if o.valid:
                self.post.observe(o.x, o.y)
        self._seen = len(history)

    def choose(self, history: list[Obs]) -> Hashable | None:
        raise NotImplementedError

    def predict(self, history, test_inputs, final):
        self._sync(history)
        rule = self.space.sources[int(np.argmax(self.post.logw))] if final else None
        return Prediction([self.post.predict(x) for x in test_inputs], rule=rule)


class RandomAgent(BayesAgent):
    name = "random"

    def choose(self, history):
        return self.domain.random_query(self.rng)


class EIGAgent(BayesAgent):
    name = "eig"

    def choose(self, history):
        self._sync(history)
        gain = self.post.eig()
        best = np.flatnonzero(gain >= gain.max() - 1e-9)
        return self.space.pool[int(self.rng.choice(best))]


REFERENCE_AGENTS = {"random": RandomAgent, "eig": EIGAgent}
