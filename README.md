# lean-mode

A token-efficiency skill for coding agents. Three independent layers, each measured, each
optional:

| layer | what it does | upstream claim | what **this repo measured** |
|---|---|---|---|
| **entire-graph** | search-first navigation + turn minimisation instead of grep/whole-file exploration | ~50% session-token cut | **−17.3% total tokens / −12.3% cost** on a mixed task set; **−33% to −67% on impact & multi-hop tasks**; **~0 to +35% (worse) on trivial named-file tasks** |
| **caveman-ultra** | compresses the agent's own prose output | ~75% fewer output tokens | **no effect — output went UP (+14% to +23%)**. Only cutting the *tool surface* reduced output (−25.6%) |
| **RTK** | filters/compacts shell output before it reaches the model | ~95% on shell ops | **not measured** (not exercised by the benchmark) |

> **Read this before believing any percentage.** 120 measured runs (sonnet, n=6/cell, median) say the
> upstream headline claims do **not** hold as stated. What you actually buy depends entirely on the
> task: big wins on exploration-heavy work, a net *loss* on tasks that already name their file — so
> the "skip the graph when the file is named" rule is the token-optimal move, not boilerplate.
>
> Two findings that invalidated my own earlier numbers, both documented in [`bench/VERDICT.md`](bench/VERDICT.md):
> **(a)** `real` (cache_creation+input+output) is a *contaminated* metric — the ~8.8k harness prefix
> flips between `cache_creation` and `cache_read` on run timing, not treatment, so the −12.2% I first
> published was partly artifact. Everything is now reported in `total` / `$cost` / `output` / `turns`.
> **(b)** a *tiny* instruction block has **no** cache discount: below the model's minimum cacheable
> prefix (1024 tokens on Sonnet) caching silently no-ops and those tokens bill at full 1.0×.
>
> The harness, scorer, raw results and the floor measurement are all shipped in [`bench/`](bench/) so
> you can re-run it and disagree with me.

Plus the lever most people miss: a **delegation rule** that pushes both compressions into every
subagent/workflow prompt you author — subagent return text is injected into the parent context,
which is usually the largest controllable spend in an agent-heavy session.

Each layer degrades gracefully. If a tool isn't installed, the skill skips it — it never
auto-installs anything.

## Install

### As a Claude Code plugin (recommended)

```
/plugin marketplace add suhaanthayyil/lean-mode
/plugin install lean-mode@lean-mode
```

### As a plain skill (or for any other agent)

```bash
git clone https://github.com/suhaanthayyil/lean-mode
cd lean-mode
bash install.sh            # copy into ~/.claude/skills/lean-mode
bash install.sh --link     # symlink instead (repo stays the source of truth)
```

The skill is plain Markdown + one Bash script, so it works with any agent that can read a
doctrine file and run a shell command — not just Claude Code.

## Use

```
/lean-mode
```
…or just say "lean mode" / "token efficiency" / "reduce token usage".

Verify the stack at any time:

```bash
bash skills/lean-mode/scripts/lean-setup.sh                  # status only
bash skills/lean-mode/scripts/lean-setup.sh --install-guide  # + install the repo graph guide
```

Example output:

```
lean-mode status
----------------
rtk            OK   rtk 0.43.0   (prefix: rtk read|grep|git|test|find|gh)
caveman        OK   plugin present   (/caveman lite|full|ultra)
entire graph   OK   version dev   (search-first: entire graph search --repo . --profile full --query ...)
  repo guide   OK   ./.entire/graph-agent.md present
----------------
active: 3/3   missing: 0
```

`--install-guide` runs `entire graph init-agents`, which writes `.entire/graph-agent.md` and
appends one delimited `<!-- entire-graph:begin/end -->` block to `AGENTS.md` / `CLAUDE.md`.
Additive and safe to re-run.

## The measured bits

Two findings that are easy to get wrong, both measured on a 73-file Go repo:

**1. Always pass `--format agent`.** The default `--format json` dumps a full
`stats`/`completeness`/relation-census block into context.

| command | `json` | `agent` | `agent --top-k 5` | `text` |
|---|---|---|---|---|
| `search` | 9610 B | 3683 B | **1866 B (−81%)** | 1128 B |
| `neighbors` | 2077 B | **293 B (−86%)** | — | 293 B |

`agent` beats the even-smaller `text` in practice: `text` is locations-only, so it forces an
extra file read. `agent` keeps the snippet, and the top hit is often enough to edit from.

**2. Pick the right impact command for the question.** Both exist; they answer different things
(byte counts measured on the same symbol):

```bash
# "who calls X" — narrowest and cheapest (291 B)
entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent

# "what breaks if I change X" — one call for the full blast radius: callers, callees, type
# consumers, data flow, co-changing files (1740 B, replaces several queries)
entire graph impact --repo . --symbol X --format text
```

An earlier version of this file claimed `entire graph impact` did not exist. That was wrong: the
subcommand is in `internal/cli/root.go`, and the error came from a **stale installed binary**
predating it. If `entire graph impact` reports `unknown command`, rebuild and reinstall the plugin
rather than working around it.

## Optional dependencies

| tool | needed for | if missing |
|---|---|---|
| [`rtk`](https://github.com/) | shell-output filtering | layer skipped |
| `caveman` plugin | `/caveman lite\|full\|ultra` modes | output rules applied manually |
| `entire` CLI + `graph` plugin | search-first navigation | grep/read fallback |

## License

MIT
