---
name: lean-mode
description: >
  Set up and enforce the token-efficiency stack for this machine: RTK (shell-output filter,
  ~95% saving on shell ops), caveman-ultra output compression (~75% fewer output tokens), and
  entire-graph search-first code navigation (replaces grep/read exploration, measured ~50%
  session-token cut). Use when the user says "lean mode", "token efficiency", "set up rtk /
  caveman / entire graph", "reduce token usage", "make agents cheaper", or invokes /lean-mode.
  Also apply when starting heavy exploration or delegation work in a repo.
---

# lean-mode — token-efficiency stack

Three independent layers. Each degrades gracefully: if a tool is absent, **skip it silently —
never install it.** Verify, use what's present, report what's missing once.

## Setup (idempotent)

```bash
bash "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/lean-mode}/scripts/lean-setup.sh"        # verify only
bash "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/lean-mode}/scripts/lean-setup.sh" --install-guide   # + install repo graph guide
```
`--install-guide` runs `entire graph init-agents --repo .`, which writes `.entire/graph-agent.md`
and appends ONE delimited block (`<!-- entire-graph:begin/end -->`) to `AGENTS.md` + `CLAUDE.md`.
Additive — existing content is preserved. Safe to re-run.

---

## 1. RTK — shell-output filter

Verify: `rtk --version`, `rtk gain`. If `command not found` → skip RTK, do not install.
A Claude Code hook may already rewrite these transparently — **do not fight the hook.**

Verified subcommands: `ls tree read smart git gh glab aws psql pnpm err test json deps env
find diff log dotnet docker kubectl oc summary grep rg`.

```bash
rtk read <file>          # filtered file read
rtk grep <pat>           # compact grep (also: rtk rg)
rtk git status           # compact git
rtk go test ./...        # test output → failures only
rtk find . -name '*.go'  # compact find (native flags OK)
rtk gh pr view 123       # compact gh
```
`rtk gain` / `rtk gain --history` = savings analytics. `rtk discover` = missed opportunities.
**Never** `rtk proxy` unless debugging RTK itself.

## 2. Caveman-ultra — output compression

All prose (final reports + intermediate): drop articles/filler/pleasantries/hedging. Fragments
OK. Abbreviate prose words (DB/auth/cfg/req/res/fn/impl). Arrows for causality (X → Y). One word
when one word works. No tool-call narration, no decorative tables/emoji, no raw log dumps —
quote the shortest decisive line.

**NEVER abbreviate or alter:** code symbols, function/API names, CLI flags, file paths, error
strings, numbers. Code blocks unchanged.

**Write normally (compression OFF):** security warnings, irreversible-action confirmations,
commit messages, PR bodies, and any multi-step sequence where fragment order risks misread.

Full modes live in the `caveman` plugin (`/caveman lite|full|ultra`, `/caveman-stats`).

## 3. entire graph — search-first code navigation

Verify: `entire graph version`. Official doctrine: `entire graph agent-guide` (39 lines — read it
once; this section mirrors it).

**One call, then act.** Per task type — use these exact forms (`--format agent` is load-bearing,
see below):

```bash
# locate code (ALWAYS first for find/fix tasks)
entire graph search --repo . --profile full --format agent --top-k 5 \
  --query "<task or bug in one sentence>"

# impact / who calls X    (NOTE: there is NO `entire graph impact` subcommand)
entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent

# what changed
entire graph diff --base A --head B --json

# language coverage (inventory-only langs have no relations)
entire graph capabilities --json
```

### ALWAYS pass `--format agent` (measured)
Default output is `--format json`, which dumps a full `stats`/`completeness`/relation-census
block into context. Measured on a 73-file Go repo, same query:

| cmd | `json` | `agent` | `text` |
|---|---|---|---|
| `search` | 9610 B | 3683 B · **1866 B** with `--top-k 5` | 1128 B |
| `neighbors` | 2077 B | **293 B** | 293 B |

`agent --top-k 5` = **−81%** vs default on search, **−86%** on neighbors. Prefer `agent` over
`text`: `text` is locations-only, which forces an extra file read (measured net-negative) —
`agent` keeps the snippet, so the top hit is often enough to edit from.

Other flags that matter: `--max-context-bytes N`, `--depth 1|2`, `--internal-only`,
`--exclude-tests`.

### Hard rules (each violation costs real money)
1. **SEARCH FIRST** — no grep/find/cat to locate code before searching.
2. **ONE search, then act.** Second search only if the first clearly missed.
3. After search: read a **line range (~120 lines max)** around the reported line, then edit.
4. **Never read a whole file to explore.**
5. **Do not chain** `search → def → callers` to "explore the tool" — the #1 measured waste.
6. **Do not re-verify** results with a second tool before editing — results are deterministic.
7. No builds/test suites unless the task requires them.

### When NOT to use the graph
Task already names the exact small file → just read it. The graph pays for itself by removing
exploration; with nothing to explore, skip it.

### Known edge case
`entire graph search --max-snippet-lines 1` crashes (`invalid search result at rank N`). Use ≥2.

---

## 4. Delegation rule (biggest lever in agent-heavy sessions)

Subagent/workflow return text is injected into the parent context — that is the largest
controllable spend. Bake into **every** subagent/workflow prompt you author:

- **Output directive:** "Respond caveman-ultra — drop articles/filler/hedging, fragments OK,
  abbreviate prose words. Keep VERBATIM: code, file paths, symbol/API names, CLI flags,
  commands, exact error strings, numbers."
- **Tooling directive:** "Use `rtk`-prefixed shell commands (`rtk read/grep/git/test`) and
  `entire graph search` before any grep/find/whole-file read."

Caveat: bundled/named workflows (e.g. `deep-research`) have fixed internal prompts — cannot be
retrofitted mid-run. Only prompts you author get the treatment.

**Compress style, never substance.** Findings, numbers, `file:line`, and errors stay exact.
