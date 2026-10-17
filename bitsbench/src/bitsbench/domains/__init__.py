"""Domain registry."""

from __future__ import annotations

from .base import Domain, Level
from .boolean import Boolean
from .lists import Lists
from .numbers import Numbers
from .regular import Regular

_REGISTRY: dict[str, type[Domain]] = {d.name: d for d in (Numbers, Boolean, Regular, Lists)}
_INSTANCES: dict[str, Domain] = {}


def get_domain(name: str) -> Domain:
    if name not in _REGISTRY:
        raise KeyError(f"unknown domain {name!r}; choose from {sorted(_REGISTRY)}")
    if name not in _INSTANCES:
        _INSTANCES[name] = _REGISTRY[name]()
    return _INSTANCES[name]


def all_configs() -> list[tuple[str, str]]:
    """Every (domain, level) pair in the benchmark."""
    return [(n, lv) for n, cls in _REGISTRY.items() for lv in cls.levels]


__all__ = ["Domain", "Level", "get_domain", "all_configs"]
