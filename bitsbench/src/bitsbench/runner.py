"""Run agents on episodes and write one JSON record per episode."""

from __future__ import annotations

import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable

from .agents.base import Agent, Obs
from .agents.reference import REFERENCE_AGENTS
from .domains import get_domain
from .episodes import Episode, Oracle

CONDITIONS = ("active", "passive_random", "passive_eig")


def _jsonable(v):
    return list(v) if isinstance(v, tuple) else v


def collect(policy: Agent, ep: Episode, stream: int = 0) -> list[Obs]:
    """Let ``policy`` run the full experiment budget and return its observations."""
    oracle = Oracle(ep, stream)
    policy.begin(ep, oracle.domain, "active")
    hist: list[Obs] = []
    for t in range(1, ep.budget + 1):
        x = policy.choose(hist)
        hist.append(Obs(t, x, oracle.query(x, t) if x is not None else None))
    return hist


def run_episode(agent: Agent, ep: Episode, condition: str = "active") -> dict:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}; choose from {CONDITIONS}")
    domain = get_domain(ep.domain)
    t0 = time.time()
    checkpoints = []

    def checkpoint(hist: list[Obs]) -> None:
        final = len(hist) == ep.budget
        p = agent.predict(hist, ep.test_inputs, final)
        checkpoints.append({"k": len(hist), "pred": [_jsonable(y) for y in p.outputs], "parsed": p.ok,
                            "rule": p.rule})

    if condition == "active":
        oracle = Oracle(ep)
        agent.begin(ep, domain, "active")
        hist: list[Obs] = []
        for t in range(1, ep.budget + 1):
            x = agent.choose(hist)
            hist.append(Obs(t, x, oracle.query(x, t) if x is not None else None))
            if t in ep.checkpoints:
                checkpoint(hist)
    else:
        policy = REFERENCE_AGENTS[condition.removeprefix("passive_")](seed=0)
        hist = collect(policy, ep)
        agent.begin(ep, domain, "passive")
        for k in ep.checkpoints:
            checkpoint(hist[:k])

    return {
        "episode_id": ep.id,
        "agent": agent.name,
        "condition": condition,
        "episode": ep.to_json(),
        "history": [{"t": o.t, "x": _jsonable(o.x), "y": _jsonable(o.y)} for o in hist],
        "checkpoints": checkpoints,
        "agent_info": agent.end(),
        "seconds": round(time.time() - t0, 2),
    }


def run_many(make_agent: Callable[[], Agent], episodes: Iterable[Episode], condition: str, out: Path,
             workers: int = 4, progress: bool = True) -> list[dict]:
    """Run every episode not already in ``out`` (resumable); returns the new records."""
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        with out.open() as f:
            for line in f:
                r = json.loads(line)
                done.add((r["episode_id"], r["condition"]))
    todo = [ep for ep in episodes if (ep.id, condition) not in done]
    lock = threading.Lock()
    new: list[dict] = []
    errors = out.with_suffix(".errors.jsonl")

    def work(ep: Episode) -> dict:
        return run_episode(make_agent(), ep, condition)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = {pool.submit(work, ep): ep for ep in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            ep = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:  # keep going; failed episodes are retried on the next run
                with lock, errors.open("a") as f:
                    f.write(json.dumps({"episode_id": ep.id, "condition": condition, "error": repr(e),
                                        "traceback": traceback.format_exc()}) + "\n")
                if progress:
                    print(f"[{i}/{len(todo)}] {ep.id} ERROR {e!r}", flush=True)
                continue
            with lock, out.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            new.append(rec)
            if progress:
                print(f"[{i}/{len(todo)}] {ep.id} {condition} done in {rec['seconds']}s", flush=True)
    return new
