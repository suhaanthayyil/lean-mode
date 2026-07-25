# lean-mode A/B benchmark

Does the lean-mode doctrine actually save tokens? Measured, not assumed.

```bash
RUNS=3 bash bench.sh          # 4 tasks x 2 arms x 3 runs = 24 runs (~$3 on sonnet)
python3 score.py results      # per-task + aggregate, mean and spread
```

## Result (2026-07-24, sonnet, 73-file Go repo, 3 runs/cell, 24 runs, 0 errored)

| task | real tokens | total tokens | output | $cost | verdict |
|---|---|---|---|---|---|
| T1 locate | **−12.5%** | +22.1% | +38.4% | −1.0% | signal |
| T2 impact/who-calls | −1.8% | −24.5% | −46.7% | −10.0% | within noise |
| T3 multi-hop explain | **−23.7%** | +25.3% | −4.9% | −6.1% | signal |
| T4 file already named (control) | −0.7% | +25.9% | +20.8% | +8.1% | within noise — **as predicted** |
| **aggregate** | **−12.2%** | **+15.5%** | +0.1% | −2.8% | |

`real` = cache_creation + input + output (tokens processed once). `total` = real + cache_read.
Signal vs noise = is the mean delta larger than the arms' own run-to-run spread.

### Honest reading

- **The ~50% session-token claim is not reproduced.** Real tokens −12.2%; **$cost −2.8%, which is
  near noise.** Cost is the economic ground truth.
- **Total tokens get 15.5% WORSE.** The doctrine block (~1.5k tokens) rides in every prompt and is
  re-read each turn, and it adds turns on some tasks. That overhead cancels much of the retrieval
  saving. Bigger prompt → bigger cached prefix → more cache_read.
- **caveman-ultra did nothing to output volume (+0.1%).** It cut output on T2 (−46.7%) but the agent
  reported *more* detail on T1 (+38.4%) and T4 (+20.8%), cancelling out. Style compression ≠ fewer
  output tokens when the agent chooses to say more.
- **The win is real where there is something to explore:** T3 (multi-hop) −23.7% and T1 (locate)
  −12.5% both exceed their spread.
- **The control behaved as the doctrine predicts.** T4 names the file, doctrine says skip the graph,
  and the measured gain is ~0 (and cost +8.1% — the doctrine is a net *loss* on trivial tasks).
  A rigged benchmark would not include a task it loses.
- **RTK is unmeasured.** Neither arm had the RTK hook (see control 2) and these read-only tasks used
  `Read`/`Grep`, not shell-heavy ops. Its ~95% claim stands untested here.

### Fairness controls (why this is not cheating)

1. Fresh `git clone` per run — no cross-run state.
2. `--setting-sources project` in a clone with no project settings. **Critical:** the RTK hook lives
   in `~/.claude/settings.json` and would have silently handed the *baseline* rtk. Neither arm gets
   hooks; the lean arm invokes rtk only because its prompt says to.
3. Repo content byte-identical in both arms — the `.entire/` graph guide is pre-installed in
   **neither**, so the baseline cannot get the doctrine for free. The only difference is the prompt.
4. Same model, same tools (`Read Grep Glob Bash`), same `--max-turns`, same task text. The baseline
   *could* have used `entire graph`; nothing blocked it. That can only shrink the gap, never inflate
   it — the conservative direction.
5. Tasks fixed **before** any results were seen, and include T4, a control where lean-mode predicts
   no gain. No post-hoc task selection.
6. 3 runs per cell; spread reported; a delta smaller than the spread is labelled *within noise*.
7. Metrics read from Claude's own JSON envelope. Never estimated. **Every** metric reported for
   every task — no metric shopping.
8. **Treatment verified to fire.** A `stream-json` run confirms the lean arm's first action is
   `entire graph search --repo . --profile full --format agent --top-k 5`, and the baseline's is
   `Grep` + a whole-file `Read` with zero `entire graph` references. Without this check the
   benchmark would only be measuring "longer prompt".

### Limits

Small n (4 tasks, 1 repo, 1 model, 3 runs). Read-only locate/explain tasks — this isolates the
exploration phase, which is what the doctrine targets, and says nothing about edit-heavy work.
Per-task spread is large (up to 2994 real tokens on T3). Treat the per-task signs as directional
and the aggregate as approximate.
