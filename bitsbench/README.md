# BITS-Bench

**Do language-model agents gather the information they need, and do they use what they gather?**

Research agents fail for two very different reasons: they run uninformative experiments, or they
draw the wrong conclusions from informative ones. End-to-end discovery benchmarks (ASI-Bench,
DiscoveryWorld, BoxingGym, ACED-Bench, ...) report *whether* an agent succeeded, but cannot say
*which* of the two went wrong, because they have no ground truth for what an ideal reasoner could
have concluded from the agent's own data.

BITS-Bench supplies that ground truth. Every task hides a rule drawn **uniformly from a finite,
fully enumerated hypothesis space** (up to 312k semantically distinct rules). The agent runs
experiments under a fixed budget. Because the space is enumerated, the **exact Bayesian posterior**
after any sequence of experiments is computable. That gives, for every agent and every checkpoint:

* the **information** its experiments gathered, in bits, exactly;
* the accuracy of the **Bayes-optimal predictor given the agent's own experiments**;
* the same for reference experimenters (uniformly random, and greedy expected-information-gain).

The agent's shortfall from the reference then splits **exactly** into two parts:

```
ref_acc - acc  =  (ref_acc - bayes_acc(own data))  +  (bayes_acc(own data) - acc)
                   gathering regret                   inference regret
```

Inference regret is non-negative in expectation, because the target really is drawn from the prior
the agent is told about. The same split is applied to **exact identification** of the rule.

## Domains

| config      | hypothesis class                                            |    \|H\| | bits | budget |
|-------------|-------------------------------------------------------------|---------:|-----:|-------:|
| numbers/L1  | one atomic property of x in 1..100 (Tenenbaum's number game) |      194 |  7.6 |     16 |
| numbers/L2  | AND/OR of two atomic properties                              |   17,930 | 14.1 |     16 |
| boolean/L1  | AND or OR of <=3 literals over 8 bits                        |    1,136 | 10.1 |     16 |
| boolean/L2  | + 2-term DNF / 2-clause CNF (<=2 literals each)              |   11,944 | 13.5 |     16 |
| boolean/L3  | + 2-term DNF / 2-clause CNF (<=3 literals each)              |  312,104 | 18.3 |     24 |
| regular/L1  | regular language over {a,b} with a <=3-state DFA             |      864 |  9.8 |     16 |
| regular/L2  | ... with a <=4-state DFA                                     |   48,350 | 15.6 |     16 |
| lists/L1    | one list primitive (26 primitives)                           |       26 |  4.7 |      8 |
| lists/L2    | pipeline of <=2 primitives                                   |      442 |  8.8 |      8 |
| lists/L3    | pipeline of <=3 primitives                                   |    5,796 | 12.5 |      8 |

Binary domains are restricted to rules that are true on 10–90% of inputs. Hypotheses equal on the
input space are merged, so the prior is uniform over *distinct functions*. The `noisy` suite adds
observation noise (each binary result flipped with probability 0.1) on the four binary L1
configurations. In that suite repeated experiments carry information, and inference must be robust.

## Protocol

1. The agent gets the exact rule-family specification (see `bitsbench prompt numbers L2`).
2. It runs experiments one at a time (`QUERY: <input>`), seeing every result so far.
3. At checkpoints after 1/8, 1/4, 1/2 and all of the budget, it predicts f on 15–25 held-out inputs.
   Each checkpoint is answered in a **fork** of the conversation that is then discarded. The test
   inputs never enter the history the agent experiments from, so it cannot query them.
4. At the last checkpoint it also states the rule (`RULE: ...`). The rule is compiled and checked
   for exact equivalence over the whole input space. Python expressions, regexes, DFAs and DSL
   pipelines are all accepted.

**Conditions.**
- `active`: the agent designs its own experiments.
- `passive_random`: the agent only predicts, from experiments chosen uniformly at random.
- `passive_eig`: the agent only predicts, from experiments chosen by the greedy-EIG reference.

Comparing the three separates the value of the agent's experiment choices from its inference, as
a behavioural complement to the analytic decomposition.

## Metrics

| metric          | meaning                                                                                   |
|-----------------|-------------------------------------------------------------------------------------------|
| `predict`       | test accuracy above the prior baseline, as a fraction of the greedy-EIG Bayes reference's, averaged over checkpoints |
| `discover`      | exact-identification rate of the final rule ÷ the reference's MAP posterior mass         |
| `bits_score`    | mean of `predict` and `discover` (headline; equal weight per configuration)              |
| `p_gather`, `p_infer` | accuracy decomposition (sum = accuracy below reference)                             |
| `d_gather`, `d_infer` | identification decomposition                                                       |
| `info_eff`      | bits gathered ÷ reference bits                                                            |
| `design_eff`    | (bits − random bits) ÷ (reference bits − random bits); negative = worse than random experiments |

Reference experimenters with exact Bayesian inference, on the dev split (30 episodes per config):
see `paper/` for the full table. A random experimenter recovers most of the *prediction*
accuracy, but on the binary domains it identifies the exact rule only 13–62% of the time, against
88–100% for greedy EIG. Identification is where experimental design shows.

## Quickstart

```bash
pip install -e ".[all]"          # numpy + pandas; SDKs and matplotlib are optional extras
bitsbench info                   # configurations and hypothesis-space sizes (first call builds caches, ~20 s)
bitsbench play numbers L1        # play an episode yourself

# reference curves (once per episode file; ~minutes on 4 cores)
bitsbench refs --episodes data/dev_all.jsonl --out data/dev_refs.jsonl --workers 4

# run models (resumable: re-running skips finished episodes; --cache makes interrupted ones cheap)
bitsbench run --model anthropic:<model-id> --effort high --episodes data/dev_core.jsonl \
    --out results/<label>.jsonl --workers 8 --cache results/cache.sqlite
bitsbench run --model openai:<model-id> --effort high --episodes data/dev_core.jsonl --out results/<label>.jsonl
bitsbench run --model compat:Qwen/Qwen3-32B --base-url http://localhost:8000/v1 --api-key-env VLLM_KEY \
    --episodes data/dev_core.jsonl --out results/qwen3-32b.jsonl
bitsbench run --model anthropic:<model-id> --effort high --condition passive_eig ...

# score everything: leaderboard, per-config tables, LaTeX, learning curves, decomposition plot
bitsbench report --results results/*.jsonl --refs data/dev_refs.jsonl --out reports/dev
```

`--model mock` runs the whole pipeline offline with a random agent, and `--model ref:eig` /
`ref:random` run the reference agents through the same path. `scripts/run_grid.sh models.txt` runs the
paper's full grid for the models listed in `models.txt` (format in `scripts/models.example.txt`).

**Model settings.** Results are only comparable at fixed settings, so pass `--effort` explicitly
(provider defaults differ between models and change over time). Refusal fallbacks to other models are deliberately left
off: every reply must come from the named model. Refusals and `max_tokens` stops are counted in
each record's `agent_info.usage`.

## Splits and contamination

Episodes are procedurally generated from `(split, salt, domain, level, eps, index)`.

- **dev** uses a public salt; its files are in `data/`.
- **test** uses a private salt (`$BITSBENCH_TEST_SALT`), held by the maintainers for the leaderboard.
  `bitsbench episodes --split test --hide-targets` produces a releasable file without targets.

Because the rule families are fixed but instances are fresh draws from spaces of up to 2^18 rules,
memorising released episodes does not help on new ones. Hypothesis-space sizes are pinned in
`tests/test_spaces.py`, so any change to a rule family is a visible, versioned change.

## Layout

```
src/bitsbench/
  space.py        finite hypothesis spaces, exact posterior, entropy, EIG
  domains/        numbers, boolean, regular, lists (+ base class and registry)
  episodes.py     seeded episode generation, splits, the (noisy) oracle
  agents/         LLM agent (prompts, parsing, forked checkpoints), reference agents, human player
  clients.py      Anthropic SDK, OpenAI-compatible SDK, mock, on-disk response cache
  runner.py       episode loop for all three conditions, resumable parallel runs
  metrics.py      replay, references, decomposition
  report.py       tables and figures
paper/            ICML draft (LaTeX)
scripts/          experiment grid
tests/            53 tests (pytest)
```

## Limitations

The rule families are formal and small, by design: exactness needs enumerable spaces. BITS-Bench
measures a precondition for automated research, not research ability itself. Greedy EIG is a strong
reference, not an upper bound: an agent can beat it on information gathered in a particular episode.
Inference regret, however, is bounded below by zero in expectation.
