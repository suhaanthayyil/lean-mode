# lean-mode

A token-efficiency skill for coding agents. Three independent layers, each measured, each
optional:

| layer | what it does | upstream claim | what **this repo measured** |
|---|---|---|---|
| **RTK** | filters/compacts shell output before it reaches the model | ~95% on shell ops | **not measured** (not exercised by the benchmark below) |
| **caveman-ultra** | compresses the agent's own prose output | ~75% fewer output tokens | **+0.1% output tokens — no effect** |
| **entire-graph** | search-first code navigation instead of grep/read exploration | ~50% session-token cut | **−12.2% real tokens**, −2.8% cost, **+15.5% total tokens** |

> **Read this before believing any percentage.** The upstream column is what each tool claims.
> The right-hand column is what an honest A/B on this repo actually produced — and it does **not**
> reproduce the headline claims. The win is real but narrow: it concentrates on
> exploration-heavy tasks and is partly cancelled by the cost of the doctrine prompt itself.
> Full method, per-task numbers and limits: [`bench/`](bench/) — the harness is shipped so you can
> re-run it and disagree with me.

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

**2. There is no `entire graph impact` subcommand.** Blast radius is:

```bash
entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
```

## Optional dependencies

| tool | needed for | if missing |
|---|---|---|
| [`rtk`](https://github.com/) | shell-output filtering | layer skipped |
| `caveman` plugin | `/caveman lite\|full\|ultra` modes | output rules applied manually |
| `entire` CLI + `graph` plugin | search-first navigation | grep/read fallback |

## License

MIT
