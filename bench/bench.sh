#!/usr/bin/env bash
# lean-mode A/B token benchmark.
#
# TREATMENT (single variable): the lean-mode DOCTRINE in the prompt
#   (entire graph search-first + --format agent + line-range reads + rtk prefixes + caveman-ultra output)
# Arm A (base) = identical task, identical model/tools/repo, NO doctrine.
# Arm B (lean) = same + doctrine prepended.
#
# FAIRNESS CONTROLS (why this is not cheating):
#  1. Fresh clone of the target repo per run -> no cross-run state, no edits leaking.
#  2. --setting-sources project in a clone with NO project settings -> the global RTK hook
#     (present in ~/.claude/settings.json) cannot silently give the BASE arm rtk. Neither arm
#     gets hooks; arm B invokes rtk explicitly because its doctrine says to.
#  3. Repo content byte-identical in both arms (the .entire graph guide is NOT pre-installed in
#     either) -> the only difference is the prompt.
#  4. Both arms get the SAME tools (Read Grep Glob Bash), same model, same --max-turns.
#     Arm A *could* use entire graph if it chose to; nothing blocks it. That can only SHRINK
#     the measured gap, never inflate it (conservative direction).
#  5. Tasks fixed BEFORE any results were seen; includes T4, a control where lean-mode predicts
#     NO gain (file already named -> doctrine says skip the graph). No post-hoc task selection.
#  6. RUNS=3 per (task,arm) -> mean +/- spread reported. No single-run claims.
#  7. Metrics read from claude's own JSON envelope (real usage), never estimated:
#     real = cache_creation + input + output ; total = real + cache_read ; plus $cost and turns.
#     All metrics reported for every task -> no metric shopping.
#  8. Read-only tasks ("do not edit") -> isolates the locate/explore phase, which is what
#     lean-mode actually targets. Stated as a scope limit, not hidden.
set -uo pipefail

SRC="${SRC:-/Users/suhaan/devenv/graphloop-build/entire-loop}"
OUT="${OUT:-/Users/suhaan/devenv/graphloop-build/leanbench/results}"
MODEL="${MODEL:-sonnet}"
RUNS="${RUNS:-3}"
MAXTURNS="${MAXTURNS:-30}"
mkdir -p "$OUT"

# ---- tasks (FIXED IN ADVANCE) ----
task_id=(T1 T2 T3 T4)
task_txt=(
"Where is the external measure command actually executed as a subprocess? Report the file:line and the function name."
"Which functions call runMeasureShell? Report every caller with file:line."
"Explain how a verifier-dropped proposal is prevented from resurfacing after a process resume. Report the relevant symbols with file:line."
"In internal/org/router.go, what threshold values decide the full-audit route? Report the values."
)

COMMON_SUFFIX="

Report concisely. Do NOT edit, create, or delete any file."

DOCTRINE="You are in lean-mode. Follow this doctrine exactly — it is measured to cut tokens:

1. SEARCH FIRST. Your first action for locating code must be ONE call:
     entire graph search --repo . --profile full --format agent --top-k 5 --query \"<the task in one sentence>\"
   Never grep/find/cat to locate code before searching. ALWAYS pass --format agent --top-k 5
   (the default --format json is ~5x larger).
2. Impact / who-calls-X is ONE call (there is NO 'entire graph impact' subcommand):
     entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
3. After searching, read a LINE RANGE (~120 lines max) around the reported line. NEVER read a
   whole file to explore. Do not chain search->def->callers to explore. Do not re-verify a
   deterministic result with a second tool.
4. Prefix shell ops with rtk when available: rtk read <file>, rtk grep <pat>, rtk git status.
5. If the task already names an exact small file, just read it — skip the graph.
6. Output caveman-ultra: drop articles/filler/hedging, fragments OK, abbreviate prose words.
   Keep VERBATIM: code, file paths, symbol names, CLI flags, error strings, numbers.

TASK:
"

run_one() { # arm task_idx run_no
  local arm="$1" ti="$2" rn="$3"
  local id="${task_id[$ti]}"
  local tag="${id}-${arm}-r${rn}"
  local dst; dst="$(mktemp -d "/tmp/leanbench-${tag}-XXXX")"
  # control 3: byte-identical clean clone for BOTH arms
  git clone --quiet --local --no-hardlinks "$SRC" "$dst/repo" 2>/dev/null || { echo "CLONE FAIL $tag"; return 1; }
  rm -rf "$dst/repo/.entire" "$dst/repo/.claude" 2>/dev/null
  # strip any pre-installed graph-guide block so neither arm gets the doctrine for free
  for f in "$dst/repo/CLAUDE.md" "$dst/repo/AGENTS.md"; do
    [ -f "$f" ] && sed -i '' '/entire-graph:begin/,/entire-graph:end/d' "$f" 2>/dev/null
  done

  local prompt
  if [ "$arm" = lean ]; then prompt="${DOCTRINE}${task_txt[$ti]}${COMMON_SUFFIX}"
  else                       prompt="${task_txt[$ti]}${COMMON_SUFFIX}"; fi

  ( cd "$dst/repo" && exec claude -p "$prompt" \
      --model "$MODEL" --output-format json --max-turns "$MAXTURNS" \
      --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
      --allowedTools Read Grep Glob Bash \
      --dangerously-skip-permissions < /dev/null ) > "$OUT/$tag.json" 2> "$OUT/$tag.err"
  echo "done $tag"
  rm -rf "$dst"
}

echo "lean-mode bench: model=$MODEL runs=$RUNS tasks=${#task_id[@]} arms=2  -> $OUT"
for rn in $(seq 1 "$RUNS"); do
  for ti in "${!task_id[@]}"; do
    run_one base "$ti" "$rn"
    run_one lean "$ti" "$rn"
  done
done
echo "BENCH COMPLETE"
