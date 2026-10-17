"""Scoring: exact information accounting and the gathering/inference decomposition.

For an agent's first k observations D_k at a checkpoint:

  acc            the agent's accuracy on the held-out test inputs
  bayes_acc      accuracy of the Bayes-optimal predictor given the *same* D_k
  bits           information gained, H(prior) - H(posterior | D_k), in bits
  ref_acc        Bayes accuracy after the greedy-EIG reference's own k experiments

and the shortfall from the reference splits exactly into

  ref_acc - acc  =  (ref_acc - bayes_acc)   +   (bayes_acc - acc)
                    gathering regret            inference regret

Because the target is drawn from the uniform prior the agent is told about,
the Bayes predictor maximises expected accuracy given D_k, so inference regret
is non-negative in expectation: it measures information the agent collected
but failed to use. Gathering regret measures how much less useful the agent's
experiments were than the reference's.

The same split is applied to exact identification of the rule at the end of the
budget, where the Bayes-optimal guess is the MAP hypothesis and its success
probability is the posterior mass ``map_mass`` of that hypothesis:

  ref_map_mass - rule_correct = (ref_map_mass - map_mass) + (map_mass - rule_correct)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Hashable, Iterable

import numpy as np

from .agents.base import Obs
from .agents.reference import REFERENCE_AGENTS
from .domains import get_domain
from .episodes import Episode
from .runner import collect
from .space import Posterior


def _restore(v: Hashable) -> Hashable:
    return tuple(v) if isinstance(v, list) else v


def replay(ep: Episode, hist: list[Obs], ks: Iterable[int]) -> dict[int, dict]:
    """Exact posterior statistics after the first k observations, for each k."""
    sp = get_domain(ep.domain).space(ep.level)
    post = Posterior(sp, ep.eps)
    truth = [sp.output(ep.target, x) for x in ep.test_inputs]
    out, j = {}, 0
    for k in sorted(set(ks)):
        while j < k:
            if hist[j].valid:
                post.observe(hist[j].x, hist[j].y)
            j += 1
        preds = [post.predict(x) for x in ep.test_inputs]
        out[k] = {
            "bits": post.bits_gained(),
            "bayes_acc": float(np.mean([p == t for p, t in zip(preds, truth)])),
            "map_mass": post.map_mass(),
            "map_correct": bool(int(np.argmax(post.logw)) == ep.target),
        }
    return out


def query_diagnostics(ep: Episode, hist: list[Obs]) -> list[dict]:
    """Per experiment: its expected information gain, the best available gain, and whether its outcome
    was already determined by earlier results (zero expected gain in a noise-free domain)."""
    sp = get_domain(ep.domain).space(ep.level)
    post = Posterior(sp, ep.eps)
    out = []
    for o in hist:
        if not o.valid:
            out.append({"t": o.t, "valid": False})
            continue
        chosen, best = post.eig_of(o.x), float(post.eig().max())
        out.append({"t": o.t, "valid": True, "eig": chosen, "max_eig": best, "determined": chosen < 1e-9})
        post.observe(o.x, o.y)
    return out


def references(ep: Episode, runs: dict[str, int] | None = None) -> dict:
    """Reference curves for one episode: prior accuracy plus random and greedy-EIG experimenters."""
    runs = runs or {"random": 10, "eig": 3}
    ref: dict = {"episode_id": ep.id, "prior_acc": replay(ep, [], [0])[0]["bayes_acc"],
                 "prior_bits": float(np.log2(ep.space_size))}
    for name, n in runs.items():
        per_run = []
        for r in range(n):
            hist = collect(REFERENCE_AGENTS[name](seed=r), ep, stream=r + 1)
            per_run.append(replay(ep, hist, ep.checkpoints))
        ref[name] = {str(k): {m: float(np.mean([pr[k][m] for pr in per_run])) for m in per_run[0][k]}
                     for k in ep.checkpoints}
    return ref


def load_references(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open() as f:
        return {r["episode_id"]: r for r in map(json.loads, f) if r}


def score_record(rec: dict, ref: dict) -> list[dict]:
    """One row per checkpoint with every metric needed for the paper's tables."""
    ep = Episode.from_json(rec["episode"])
    domain = get_domain(ep.domain)
    sp = domain.space(ep.level)
    hist = [Obs(h["t"], _restore(h["x"]), _restore(h["y"])) for h in rec["history"]]
    truth = [sp.output(ep.target, x) for x in ep.test_inputs]
    stats = replay(ep, hist, [c["k"] for c in rec["checkpoints"]])
    diag = query_diagnostics(ep, hist) if rec["condition"] == "active" else []
    rows = []
    for i, c in enumerate(rec["checkpoints"]):
        k = c["k"]
        pred = [_restore(p) for p in c["pred"]]
        acc = float(np.mean([p is not None and p == t for p, t in zip(pred, truth)]))
        s, eig, rnd = stats[k], ref["eig"][str(k)], ref["random"][str(k)]
        final = k == ep.budget
        rule_correct = (domain.rule_matches(ep.level, c["rule"], ep.target) if c.get("rule") else False) if final else None
        ident = {}
        if final and diag:
            open_steps = [q for q in diag if q["valid"] and q["max_eig"] > 1e-9]  # rule not yet determined
            if open_steps:
                ident["determined_queries"] = float(np.mean([q["determined"] for q in open_steps]))
                ident["eig_ratio"] = float(np.mean([q["eig"] / q["max_eig"] for q in open_steps]))
        if final:
            ident |= {"map_mass": s["map_mass"], "eig_map_mass": eig["map_mass"], "random_map_mass": rnd["map_mass"],
                     "ident_gather_regret": eig["map_mass"] - s["map_mass"],
                     "ident_infer_regret": s["map_mass"] - float(rule_correct)}
        rows.append({
            "agent": rec["agent"], "condition": rec["condition"], "episode_id": ep.id,
            "domain": ep.domain, "level": ep.level, "eps": ep.eps, "config": f"{ep.domain}/{ep.level}"
            + (f"/eps{ep.eps:g}" if ep.eps else ""), "space_bits": float(np.log2(ep.space_size)),
            "k": k, "frac": k / ep.budget, "cp_index": i, "final": final,
            "acc": acc, "parsed": c["parsed"],
            "bayes_acc": s["bayes_acc"], "bits": s["bits"], "map_correct": s["map_correct"],
            "prior_acc": ref["prior_acc"],
            "eig_acc": eig["bayes_acc"], "eig_bits": eig["bits"],
            "random_acc": rnd["bayes_acc"], "random_bits": rnd["bits"],
            "gather_regret": eig["bayes_acc"] - s["bayes_acc"],
            "infer_regret": s["bayes_acc"] - acc,
            "total_regret": eig["bayes_acc"] - acc,
            "rule_correct": rule_correct, **ident,
            "invalid_experiments": sum(not o.valid for o in hist[:k]),
            "repeat_experiments": k - len({o.x for o in hist[:k] if o.valid}) - sum(not o.valid for o in hist[:k]),
        })
    return rows


def score_file(results: Path, refs: dict[str, dict]) -> list[dict]:
    rows = []
    with results.open() as f:
        for line in f:
            rec = json.loads(line)
            if rec["episode_id"] not in refs:
                raise KeyError(f"no reference curves for {rec['episode_id']}; run `bitsbench refs` first")
            rows += score_record(rec, refs[rec["episode_id"]])
    return rows


def bootstrap_ci(values: np.ndarray, n: int = 2000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(n, len(values)))].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))
