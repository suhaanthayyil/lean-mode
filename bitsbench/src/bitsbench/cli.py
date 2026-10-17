"""Command-line interface: ``bitsbench <command> ...``."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .domains import all_configs, get_domain


def cmd_info(a):
    print(f"{'config':<14} {'|H|':>8} {'bits':>6} {'budget':>6} {'tests':>5}  summary")
    for d, lv in all_configs():
        dom = get_domain(d)
        sp, L = dom.space(lv), dom.levels[lv]
        print(f"{d + '/' + lv:<14} {len(sp):>8} {sp.prior_bits:>6.1f} {L.budget:>6} {L.n_test:>5}  {L.summary}")


def cmd_prompt(a):
    from .agents.llm import system_prompt
    from .episodes import make_episode

    print(system_prompt(get_domain(a.domain), make_episode("dev", a.domain, a.level, 0, a.eps), a.mode))


def cmd_episodes(a):
    from .episodes import make_suite, save_episodes

    eps = make_suite(a.suite, a.split, a.n)
    save_episodes(eps, Path(a.out), include_targets=not a.hide_targets)
    print(f"wrote {len(eps)} episodes to {a.out}")


def _ref_worker(job: tuple[dict, dict]) -> dict:
    from .episodes import Episode
    from .metrics import references

    ep, runs = job
    return references(Episode.from_json(ep), runs)


def cmd_refs(a):
    from .episodes import load_episodes
    from .metrics import load_references

    out = Path(a.out)
    have = load_references(out)
    todo = [ep for ep in load_episodes(Path(a.episodes)) if ep.id not in have]
    for d, lv in sorted({(ep.domain, ep.level) for ep in todo}):  # build space caches once, before forking
        get_domain(d).space(lv)
    jobs = [(ep.to_json(), {"random": a.random_runs, "eig": a.eig_runs}) for ep in todo]
    out.parent.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool, out.open("a") as f:
        for i, ref in enumerate(pool.map(_ref_worker, jobs, chunksize=1), 1):
            f.write(json.dumps(ref) + "\n")
            f.flush()
            if i % 10 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] references", flush=True)


def _agent_factory(a):
    from .agents.llm import LLMAgent
    from .agents.reference import REFERENCE_AGENTS
    from .clients import make_client

    if a.model.startswith("ref:"):
        cls = REFERENCE_AGENTS[a.model.removeprefix("ref:")]
        return lambda: cls(seed=0)
    cache = Path(a.cache) if a.cache else None

    def make():
        client = make_client(a.model, effort=a.effort, max_tokens=a.max_tokens, base_url=a.base_url,
                             api_key_env=a.api_key_env, temperature=a.temperature,
                             thinking_display=a.thinking_display, cache=cache)
        return LLMAgent(client, keep_transcript=not a.no_transcript)

    return make


def cmd_run(a):
    from .episodes import load_episodes
    from .runner import run_many

    eps = load_episodes(Path(a.episodes))
    if a.only:
        eps = [e for e in eps if f"{e.domain}/{e.level}" in a.only or e.domain in a.only]
    if a.limit:
        eps = eps[: a.limit]
    if any(e.target is None for e in eps):
        sys.exit("these episodes have hidden targets; they can only be run by the holder of the full file")
    run_many(_agent_factory(a), eps, a.condition, Path(a.out), workers=a.workers)


def cmd_report(a):
    from .metrics import load_references, score_file
    from .report import write_report

    refs = load_references(Path(a.refs))
    rows = []
    for r in a.results:
        rows += score_file(Path(r), refs)
    if not rows:
        sys.exit("no results to score")
    tables = write_report(rows, Path(a.out))
    lb = tables["leaderboard"]
    with __import__("pandas").option_context("display.width", 200, "display.max_columns", 20):
        print(lb.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nreport written to {a.out}/report.md")


def cmd_play(a):
    from .agents.human import HumanAgent
    from .episodes import make_episode
    from .metrics import references, score_record
    from .runner import run_episode

    ep = make_episode(a.split, a.domain, a.level, a.index, a.eps)
    rec = run_episode(HumanAgent(), ep, "active")
    rows = score_record(rec, references(ep, {"random": 5, "eig": 2}))
    print(f"\nThe rule was: {ep.target_source}")
    for r in rows:
        print(f"  after {r['k']:>2} experiments: your accuracy {r['acc']:.2f} | Bayes-optimal from your data "
              f"{r['bayes_acc']:.2f} | greedy-EIG reference {r['eig_acc']:.2f} | bits gathered {r['bits']:.1f} "
              f"of {r['space_bits']:.1f}")
    if a.out:
        with open(a.out, "a") as f:
            f.write(json.dumps(rec) + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bitsbench", description="BITS-Bench: active discovery with exact Bayesian references")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="list configurations and hypothesis-space sizes").set_defaults(fn=cmd_info)

    s = sub.add_parser("prompt", help="print the system prompt for a configuration")
    s.add_argument("domain"), s.add_argument("level")
    s.add_argument("--eps", type=float, default=0.0)
    s.add_argument("--mode", choices=["active", "passive"], default="active")
    s.set_defaults(fn=cmd_prompt)

    s = sub.add_parser("episodes", help="generate an episode file")
    s.add_argument("--suite", default="core")
    s.add_argument("--split", default="dev")
    s.add_argument("--n", type=int, help="episodes per configuration (overrides the suite default)")
    s.add_argument("--out", required=True)
    s.add_argument("--hide-targets", action="store_true", help="omit targets (for public release of a private split)")
    s.set_defaults(fn=cmd_episodes)

    s = sub.add_parser("refs", help="compute reference curves (random and greedy-EIG experimenters)")
    s.add_argument("--episodes", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--random-runs", type=int, default=10)
    s.add_argument("--eig-runs", type=int, default=3)
    s.add_argument("--workers", type=int, default=4)
    s.set_defaults(fn=cmd_refs)

    s = sub.add_parser("run", help="run an agent on episodes")
    s.add_argument("--model", required=True,
                   help="anthropic:<model> | openai:<model> | compat:<model> (with --base-url) | mock | ref:eig | ref:random")
    s.add_argument("--episodes", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--condition", default="active", choices=["active", "passive_random", "passive_eig"])
    s.add_argument("--workers", type=int, default=4)
    s.add_argument("--effort", help="Anthropic output_config.effort or OpenAI reasoning_effort")
    s.add_argument("--max-tokens", type=int)
    s.add_argument("--base-url")
    s.add_argument("--api-key-env")
    s.add_argument("--temperature", type=float)
    s.add_argument("--thinking-display", choices=["summarized", "omitted"],
                   help="Anthropic only: request summarized thinking for transcripts")
    s.add_argument("--cache", help="sqlite file caching every model call (makes interrupted runs cheap to resume)")
    s.add_argument("--only", nargs="*", help="restrict to domains or domain/level configs")
    s.add_argument("--limit", type=int)
    s.add_argument("--no-transcript", action="store_true")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("report", help="score results and write tables and figures")
    s.add_argument("--results", nargs="+", required=True)
    s.add_argument("--refs", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("play", help="play an episode yourself in the terminal")
    s.add_argument("domain"), s.add_argument("level")
    s.add_argument("--index", type=int, default=0)
    s.add_argument("--split", default="play")
    s.add_argument("--eps", type=float, default=0.0)
    s.add_argument("--out", help="append your episode record to this JSONL file")
    s.set_defaults(fn=cmd_play)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
