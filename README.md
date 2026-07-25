# lean-mode

A token-efficiency skill for coding agents. Three independent layers, each measured, each
optional:

| layer | what it does | claimed effect | status |
|---|---|---|---|
| **RTK** | filters/compacts shell output before it reaches the model | ~95% on shell ops | upstream claim, not independently verified here |
| **caveman-ultra** | compresses the agent's own prose output | ~75% fewer output tokens | upstream claim, not independently verified here |
| **entire-graph** | search-first code navigation instead of grep/read exploration | ~50% session-token cut | upstream claim (`entire graph agent-guide`), not independently verified here |

> **Honesty note.** The three percentages above are the *upstream* claims of each tool, not
> measurements taken by this repo. The only numbers this repo has independently measured are the
> `--format` deltas in [The measured bits](#the-measured-bits) (−81% / −86%, exact byte counts).
> An end-to-end A/B benchmark of the doctrine is in progress; this table will be replaced with
> measured means ± spread when it lands. Treat unverified claims as unverified.

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
