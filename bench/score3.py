#!/usr/bin/env python3
"""Score the multi-arm bench with cache-warmth-aware metrics.

WHY THIS SUPERSEDES score2.py: `real` (= cache_creation+input+output) contains an ~8.8k
cache_creation term for the harness prefix (system prompt + tool schemas) that is paid only on a
COLD cache. Measured floor: an identical trivial run gave real=8767 (cc=8760) cold and real=7
(cc=0) warm. So `real` flips by ~8.8k on run interleaving — timing, not treatment. Metrics used
here instead:
  total  = cc+in+cr+out   the prefix is counted exactly once either way -> warmth-robust
  cost   billed reality (still mildly warmth-sensitive: cc 1.25x vs cr 0.1x)
  out    output tokens    purely treatment-driven
  turns  purely treatment-driven; drives total, since each turn re-reads the context
MEDIAN over runs (not mean) so one thrashing run cannot carry a cell.
"""
import glob, json, os, statistics as st, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "results2"
TASKS = ["T1", "T2", "T3", "T4"]
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["base", "lean1", "lean2", "lean3", "lean4"]
LBL = {"T1": "T1 locate", "T2": "T2 impact", "T3": "T3 multi-hop", "T4": "T4 named-file CONTROL"}
KEYS = ("total", "cost", "out", "turns", "real")

def load(t, a):
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, f"{t}-{a}-r*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        u = d.get("usage", {}) or {}
        i, o = u.get("input_tokens", 0) or 0, u.get("output_tokens", 0) or 0
        cc, cr = u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0
        rows.append({"total": cc + i + cr + o, "real": cc + i + o, "out": o,
                     "cost": float(d.get("total_cost_usd") or 0), "turns": d.get("num_turns") or 0,
                     "cold": cc > 5000, "err": bool(d.get("is_error")) or bool(d.get("api_error_status")),
                     "file": os.path.basename(f)})
    return rows

def med(rows, k):
    v = [r[k] for r in rows]
    return (st.median(v), max(v) - min(v), len(v)) if v else (None, None, 0)

def pct(b, l): return None if not b else (l - b) / b * 100.0

warn, cells = [], {}
print(f"lean-mode bench — MEDIAN of n runs — {OUT}\n")
for t in TASKS:
    print(LBL[t])
    for a in ARMS:
        rows = load(t, a)
        if not rows: continue
        for r in rows:
            if r["err"]: warn.append(f"{t}/{a} {r['file']} errored")
        cells[(t, a)] = {k: med(rows, k) for k in KEYS}
        s = cells[(t, a)]
        cold = sum(1 for r in rows if r["cold"])
        line = (f"  {a:6} n={s['total'][2]} total={s['total'][0]:>7.0f}(±{s['total'][1]:>6.0f})"
                f" ${s['cost'][0]:.4f} out={s['out'][0]:>5.0f} turns={s['turns'][0]:.1f}"
                f" cold={cold}/{len(rows)}")
        if a != "base" and (t, "base") in cells:
            b = cells[(t, "base")]
            d = pct(b["total"][0], s["total"][0])
            spr = max(b["total"][1], s["total"][1]); dab = abs(s["total"][0] - b["total"][0])
            line += f"  Δtotal {d:+.1f}% {'SIG' if dab > spr else 'noise'}"
        print(line)
    print()

print("AGGREGATE — median-of-medians across tasks")
base = {k: st.median([cells[(t, 'base')][k][0] for t in TASKS if (t, 'base') in cells]) for k in KEYS}
print(f"  base   total={base['total']:>7.0f} ${base['cost']:.4f} out={base['out']:>5.0f} turns={base['turns']:.1f}")
best = None
for a in ARMS:
    if a == "base": continue
    have = [t for t in TASKS if (t, a) in cells]
    if not have: continue
    v = {k: st.median([cells[(t, a)][k][0] for t in have]) for k in KEYS}
    dt, dc, do_, dtu = (pct(base['total'], v['total']), pct(base['cost'], v['cost']),
                        pct(base['out'], v['out']), pct(base['turns'], v['turns']))
    print(f"  {a:6} total={v['total']:>7.0f} ${v['cost']:.4f} out={v['out']:>5.0f} turns={v['turns']:.1f}"
          f"   Δtotal {dt:+.1f}%  Δcost {dc:+.1f}%  Δout {do_:+.1f}%  Δturns {dtu:+.1f}%")
    if best is None or dt < best[1]: best = (a, dt, dc, do_, dtu)

print("\nGOAL: -30% (which metrics clear it?)")
if best:
    a, dt, dc, do_, dtu = best
    print(f"  best arm = {a}")
    for name, val in (("total tokens", dt), ("cost", dc), ("output", do_), ("turns", dtu)):
        print(f"    {name:13} {val:+.1f}%  {'*** >=30% ***' if val <= -30 else ''}")
print("\n" + ("WARNINGS:\n  " + "\n  ".join(warn) if warn else "no errored runs."))
