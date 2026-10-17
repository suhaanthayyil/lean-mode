"""Summarise reference curves (prior / random / greedy-EIG with exact Bayesian inference) per configuration."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def main(episodes: str, refs: str, out_tex: str | None = None) -> None:
    eps = {}
    for line in open(episodes):
        e = json.loads(line)
        eps[e["id"]] = e
    agg = defaultdict(lambda: defaultdict(list))
    for line in open(refs):
        r = json.loads(line)
        e = eps.get(r["episode_id"])
        if e is None:
            continue
        cfg = f'{e["domain"]}/{e["level"]}' + (f' $\\epsilon$={e["eps"]:g}' if e["eps"] else "")
        ks = [str(k) for k in e["checkpoints"]]
        fin = str(e["budget"])
        a = agg[cfg]
        a["bits_H"].append(np.log2(e["space_size"]))
        a["budget"].append(e["budget"])
        a["prior"].append(r["prior_acc"])
        for name in ("random", "eig"):
            a[f"{name}_auc"].append(np.mean([r[name][k]["bayes_acc"] for k in ks]))
            a[f"{name}_bits"].append(r[name][fin]["bits"])
            a[f"{name}_id"].append(r[name][fin]["map_mass"])
    head = ["config", "log2|H|", "B", "prior", "rand acc", "EIG acc", "rand bits", "EIG bits", "rand id", "EIG id"]
    rows = []
    for cfg, a in agg.items():
        m = {k: float(np.mean(v)) for k, v in a.items()}
        rows.append([cfg, f'{m["bits_H"]:.1f}', f'{m["budget"]:.0f}', f'{m["prior"]:.2f}', f'{m["random_auc"]:.2f}',
                     f'{m["eig_auc"]:.2f}', f'{m["random_bits"]:.1f}', f'{m["eig_bits"]:.1f}', f'{m["random_id"]:.2f}',
                     f'{m["eig_id"]:.2f}', len(a["prior"])])
    print("| " + " | ".join(head + ["n"]) + " |\n|" + "---|" * (len(head) + 1))
    for r in rows:
        print("| " + " | ".join(map(str, r)) + " |")
    if out_tex:
        lines = [r"\begin{tabular}{lrrrrrrrrr}", r"\toprule",
                 r"config & $\log_2|\mathcal{H}|$ & $B$ & prior & \multicolumn{2}{c}{accuracy (AUC)} & "
                 r"\multicolumn{2}{c}{bits at $B$} & \multicolumn{2}{c}{identified at $B$} \\",
                 r"& & & & random & EIG & random & EIG & random & EIG \\", r"\midrule"]
        lines += [" & ".join(map(str, r[:10])).replace("_", r"\_") + r" \\" for r in rows]
        lines += [r"\bottomrule", r"\end{tabular}"]
        Path(out_tex).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
