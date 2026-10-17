"""Agent interface shared by reference agents, LLM agents and human players."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Hashable

from ..domains.base import Domain
from ..episodes import Episode


@dataclass
class Obs:
    """One experiment: ``x`` is None when the agent failed to produce a valid input."""

    t: int
    x: Hashable | None
    y: Hashable | None

    @property
    def valid(self) -> bool:
        return self.x is not None


@dataclass
class Prediction:
    outputs: list            # one entry per test input; None where unparseable
    rule: str | None = None  # submitted rule (final checkpoint only)
    ok: bool = True          # False if the reply could not be parsed at all
    info: dict = field(default_factory=dict)


class Agent(ABC):
    """Runs one episode at a time.

    ``mode`` is "active" (the agent chooses experiments) or "passive" (the
    runner supplies experiments chosen by someone else and only asks for
    predictions).
    """

    name: str = "agent"

    def begin(self, ep: Episode, domain: Domain, mode: str) -> None:
        self.ep, self.domain, self.mode = ep, domain, mode

    @abstractmethod
    def choose(self, history: list[Obs]) -> Hashable | None:
        """Next experiment, or None if the agent failed to produce a valid one."""

    @abstractmethod
    def predict(self, history: list[Obs], test_inputs: list, final: bool) -> Prediction: ...

    def end(self) -> dict:
        """Called once per episode; returns agent-specific info (usage, transcript) to store."""
        return {}
