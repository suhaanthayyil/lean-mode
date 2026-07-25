#!/usr/bin/env python3
"""Score the lean-mode A/B bench. Reports every metric for every task (no metric shopping),
mean +/- spread across runs, and flags any run that errored or hit max-turns."""
import glob, json, os, statistics as st, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "results"
TASKS = ["T1", "T2", "T3", "T4"]
ARMS = ["base", "lean"]
LABEL = {
    "T1": "T1 locate (graph-favourable)",
    "T2": "T2 impact/who-calls",
    "T3": "T3 multi-hop explain",
    "T4": "T4 file already named (CONTROL — lean predicts no gain)",
}

def load(t, a):
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, f"{t}-{a}-r*.json"))):
        try:
            d = json.load(open(f))
        except Exception as e:
            rows.append({"file": f, "bad": f"unparseable: {e}"}); continue
        u = d.get("usage", {}) or {}
        inp = u.get("input_tokens", 0) or 0
        outp = u.get("output_tokens", 0) or 0
        cc = u.get("cache_creation_input_tokens", 0) or 0
        cr = u.get("cache_read_input_tokens", 0) or 0
        rows.append({
            "file": os.path.basename(f),
            "real": cc + inp + outp,          # tokens actually processed once
            "total": cc + inp + outp + cr,    # incl. cheap cache reads
            "out": outp,
            "cost": float(d.get("total_cost_usd") or 0),
            "turns": d.get("num_turns"),
            "err": bool(d.get("is_error")),
            "api_err": d.get("api_error_status"),
            "bad": None,
        })
    return rows

def agg(rows, k):
    v = [r[k] for r in rows if not r.get("bad") and r.get(k) is not None]
    if not v: return None, None, 0
    return st.mean(v), (max(v) - min(v)), len(v)

def pct(b, l):
    if not b: return None
    return (l - b) / b * 100.0

print(f"lean-mode A/B — source: {OUT}\n")
warn = []
totals = {a: {"real": [], "total": [], "out": [], "cost": []} for a in ARMS}

for t in TASKS:
    print(LABEL[t])
    per = {}
    for a in ARMS:
        rows = load(t, a)
        if not rows:
            print(f"  {a:4} : NO DATA"); per[a] = None; continue
        for r in rows:
            if r.get("bad"): warn.append(f"{t}/{a} {r['file']}: {r['bad']}")
            elif r["err"] or r["api_err"]: warn.append(f"{t}/{a} {r['file']}: is_error={r['err']} api={r['api_err']}")
        m = {k: agg(rows, k) for k in ("real", "total", "out", "cost", "turns")}
        if m["real"][0] is None:
            print(f"  {a:4} : {len(rows)} file(s) but no usable metrics (all errored/unparseable)")
            per[a] = None; continue
        per[a] = m
        for k in ("real", "total", "out", "cost"):
            if m[k][0] is not None: totals[a][k].append(m[k][0])
        turns = m["turns"][0] if m["turns"][0] is not None else float("nan")
        print(f"  {a:4} n={m['real'][2]}  real={m['real'][0]:>8.0f} (spread {m['real'][1]:>6.0f})"
              f"  total={m['total'][0]:>8.0f}  out={m['out'][0]:>6.0f}"
              f"  ${m['cost'][0]:.4f}  turns={turns:.1f}")
    if per.get("base") and per.get("lean"):
        d = {k: pct(per["base"][k][0], per["lean"][k][0]) for k in ("real", "total", "out", "cost")}
        # noise guard: is the mean delta bigger than the larger arm's own run-to-run spread?
        spread = max(per["base"]["real"][1], per["lean"]["real"][1])
        delta_abs = abs(per["lean"]["real"][0] - per["base"]["real"][0])
        verdict = "SIGNAL" if delta_abs > spread else "WITHIN NOISE"
        print(f"  Δ lean vs base:  real {d['real']:+.1f}%   total {d['total']:+.1f}%"
              f"   out {d['out']:+.1f}%   cost {d['cost']:+.1f}%   [{verdict}:"
              f" |Δreal|={delta_abs:.0f} vs spread={spread:.0f}]")
    print()

print("AGGREGATE (unweighted mean of per-task means)")
for a in ARMS:
    if totals[a]["real"]:
        print(f"  {a:4} real={st.mean(totals[a]['real']):>8.0f}  total={st.mean(totals[a]['total']):>9.0f}"
              f"  out={st.mean(totals[a]['out']):>6.0f}  ${st.mean(totals[a]['cost']):.4f}")
if totals["base"]["real"] and totals["lean"]["real"]:
    for k in ("real", "total", "out", "cost"):
        print(f"  Δ {k:5} {pct(st.mean(totals['base'][k]), st.mean(totals['lean'][k])):+.1f}%")

if warn:
    print("\nWARNINGS (runs that errored / hit limits — do not silently average these):")
    for w in warn: print("  -", w)
else:
    print("\nno errored runs.")
