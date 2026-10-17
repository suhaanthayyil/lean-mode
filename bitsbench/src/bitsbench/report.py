"""Aggregate scored checkpoints into leaderboard tables and figures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .metrics import bootstrap_ci

def episode_table(rows: list[dict]) -> pd.DataFrame:
    """Average each episode's checkpoints (area under the learning curve) into one row."""
    df = pd.DataFrame(rows)
    keys = ["agent", "condition", "config", "domain", "level", "eps", "space_bits", "episode_id"]
    num = ["acc", "bayes_acc", "eig_acc", "random_acc", "prior_acc", "bits", "eig_bits", "random_bits",
           "gather_regret", "infer_regret", "total_regret"]
    ep = df.groupby(keys, as_index=False)[num].mean()
    fin = df[df["final"]].groupby(keys, as_index=False).agg(
        final_acc=("acc", "mean"), final_bayes_acc=("bayes_acc", "mean"),
        rule_correct=("rule_correct", lambda s: float(np.mean([bool(v) for v in s]))),
        map_mass=("map_mass", "mean"), eig_map_mass=("eig_map_mass", "mean"),
        random_map_mass=("random_map_mass", "mean"), ident_gather_regret=("ident_gather_regret", "mean"),
        ident_infer_regret=("ident_infer_regret", "mean"), invalid=("invalid_experiments", "mean"),
        repeats=("repeat_experiments", "mean"),
        determined=("determined_queries", lambda s: s.mean() if s.notna().any() else np.nan),
        eig_ratio=("eig_ratio", lambda s: s.mean() if s.notna().any() else np.nan))
    return ep.merge(fin, on=keys)


def config_table(ep: pd.DataFrame) -> pd.DataFrame:
    g = ep.groupby(["agent", "condition", "config", "domain", "level", "eps", "space_bits"])
    out = g.agg(n=("episode_id", "count"), acc=("acc", "mean"), bayes_acc=("bayes_acc", "mean"),
                eig_acc=("eig_acc", "mean"), random_acc=("random_acc", "mean"), prior_acc=("prior_acc", "mean"),
                bits=("bits", "sum"), eig_bits=("eig_bits", "sum"), random_bits=("random_bits", "sum"),
                gather_regret=("gather_regret", "mean"), infer_regret=("infer_regret", "mean"),
                final_acc=("final_acc", "mean"), rule_correct=("rule_correct", "mean"),
                map_mass=("map_mass", "mean"), eig_map_mass=("eig_map_mass", "mean"),
                ident_gather_regret=("ident_gather_regret", "mean"), ident_infer_regret=("ident_infer_regret", "mean"),
                invalid=("invalid", "mean"), repeats=("repeats", "mean"), determined=("determined", "mean"),
                eig_ratio=("eig_ratio", "mean"))
    out["info_eff"] = out["bits"] / out["eig_bits"]
    out["design_eff"] = (out["bits"] - out["random_bits"]) / (out["eig_bits"] - out["random_bits"])
    out["predict"] = (out["acc"] - out["prior_acc"]) / (out["eig_acc"] - out["prior_acc"])
    out["discover"] = out["rule_correct"] / out["eig_map_mass"]
    ci = g["acc"].apply(lambda s: bootstrap_ci(s.to_numpy()))
    out["acc_lo"], out["acc_hi"] = [c[0] for c in ci], [c[1] for c in ci]
    return out.drop(columns=["bits", "eig_bits", "random_bits"]).reset_index()


def leaderboard(cfg: pd.DataFrame) -> pd.DataFrame:
    """Equal weight per configuration."""
    lb = cfg.groupby(["agent", "condition"]).agg(
        configs=("config", "count"), predict=("predict", "mean"), discover=("discover", "mean"),
        acc=("acc", "mean"), p_gather=("gather_regret", "mean"), p_infer=("infer_regret", "mean"),
        ident=("rule_correct", "mean"), d_gather=("ident_gather_regret", "mean"),
        d_infer=("ident_infer_regret", "mean"), info_eff=("info_eff", "mean"), design_eff=("design_eff", "mean"),
        eig_ratio=("eig_ratio", "mean"), determined=("determined", "mean"), invalid=("invalid", "mean"))
    lb["bits_score"] = (lb["predict"] + lb["discover"]) / 2
    cols = ["agent", "condition", "configs", "bits_score", "predict", "discover"]
    return lb.reset_index()[cols + [c for c in lb.columns if c not in cols]].sort_values("bits_score", ascending=False)


def _md(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(format(v, floatfmt) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def _tex(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    cols = list(df.columns)
    body = [" & ".join(format(v, floatfmt) if isinstance(v, float) else str(v).replace("_", r"\_") for v in r) + r" \\"
            for _, r in df.iterrows()]
    head = " & ".join(c.replace("_", r"\_") for c in cols) + r" \\"
    return "\n".join([r"\begin{tabular}{" + "l" * 2 + "r" * (len(cols) - 2) + "}", r"\toprule", head, r"\midrule",
                      *body, r"\bottomrule", r"\end{tabular}"])


def plot_curves(rows: list[dict], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.DataFrame(rows)
    df = df[df["condition"] == "active"]
    configs = sorted(df["config"].unique())
    if not configs:
        return
    ncol = min(4, len(configs))
    nrow = int(np.ceil(len(configs) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 2.8 * nrow), squeeze=False, sharey=True)
    for ax, cfg in zip(axes.flat, configs):
        d = df[df["config"] == cfg]
        ref = d.groupby("k")[["eig_acc", "random_acc", "prior_acc"]].mean()
        ax.plot(ref.index, ref["eig_acc"], "k-", lw=1.5, label="greedy-EIG (Bayes)")
        ax.plot(ref.index, ref["random_acc"], "k:", lw=1.5, label="random (Bayes)")
        for agent, da in d.groupby("agent"):
            m = da.groupby("k")[["acc", "bayes_acc"]].mean()
            (line,) = ax.plot(m.index, m["acc"], "o-", ms=3, label=agent)
            ax.plot(m.index, m["bayes_acc"], "--", color=line.get_color(), lw=1, alpha=0.7)
        ax.set_title(cfg, fontsize=9)
        ax.set_xscale("log", base=2)
        ax.set_xlabel("experiments")
        ax.grid(alpha=0.3)
    for ax in axes.flat[len(configs):]:
        ax.axis("off")
    axes[0, 0].set_ylabel("test accuracy")
    h, lbl = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lbl, loc="lower center", ncol=min(6, len(lbl)), fontsize=8, frameon=False)
    fig.text(0.99, 0.01, "dashed: Bayes-optimal accuracy given the agent's own experiments", ha="right", fontsize=7)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_decomposition(lb: pd.DataFrame, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = lb.sort_values("bits_score")
    if d.empty:
        return
    labels = [f"{a} ({c})" for a, c in zip(d["agent"], d["condition"])]
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.45 * len(d) + 1.4), sharey=True)
    y = np.arange(len(d))
    for ax, g, i, title in ((axes[0], "p_gather", "p_infer", "Predict: accuracy below reference"),
                            (axes[1], "d_gather", "d_infer", "Discover: identification below reference")):
        ax.barh(y, d[g], color="#4C72B0", label="gathering regret")
        ax.barh(y, d[i], left=d[g].clip(lower=0), color="#DD8452", label="inference regret")
        ax.set_title(title, fontsize=9)
        ax.grid(axis="x", alpha=0.3)
    axes[0].set_yticks(y, labels)
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def write_report(rows: list[dict], out_dir: Path) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "checkpoints.csv", index=False)
    ep = episode_table(rows)
    ep.to_csv(out_dir / "episodes.csv", index=False)
    cfg = config_table(ep)
    cfg.to_csv(out_dir / "configs.csv", index=False)
    lb = leaderboard(cfg)
    lb.to_csv(out_dir / "leaderboard.csv", index=False)
    per_cfg = cfg.pivot_table(index=["agent", "condition"], columns="config", values="predict").reset_index()
    md = ["# BITS-Bench report", "", "## Leaderboard (equal weight per configuration)", "",
          "- `predict`: test accuracy above the prior baseline as a fraction of the greedy-EIG Bayes reference's, "
          "averaged over checkpoints. `p_gather + p_infer` = accuracy below that reference.",
          "- `discover`: exact-identification rate of the final RULE as a fraction of the reference's MAP mass. "
          "`d_gather + d_infer` = identification below that reference.",
          "- `bits_score` = mean of predict and discover; `info_eff` = bits gathered / reference bits; "
          "`design_eff` = (bits - random bits) / (reference bits - random bits).",
          "- `eig_ratio`: mean expected information gain of the agent's experiments relative to the best available "
          "experiment at that step; `determined`: fraction of experiments whose outcome was already entailed by "
          "earlier results (noise-free domains). Both are for the active condition only.",
          "", _md(lb), "", "## Predict score per configuration", "", _md(per_cfg), "",
          "## Per configuration", "", _md(cfg.drop(columns=["domain", "level", "eps"]))]
    (out_dir / "report.md").write_text("\n".join(md) + "\n")
    (out_dir / "leaderboard.tex").write_text(_tex(lb) + "\n")
    plot_curves(rows, out_dir / "curves.png")
    plot_decomposition(lb, out_dir / "decomposition.png")
    return {"episodes": ep, "configs": cfg, "leaderboard": lb}
