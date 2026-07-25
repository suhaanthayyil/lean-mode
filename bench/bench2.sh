#!/usr/bin/env bash
# lean-mode v2 bench — multi-variant. Same fairness controls as bench.sh (see its header):
# fresh clone/run, --setting-sources project (no RTK hook leak to base), no .entire guide in ANY
# arm, identical model/tools/max-turns/task text, tasks fixed in advance incl. the T4 control,
# metrics from claude's JSON envelope only.
#
# VARIANTS (the treatment is the prompt prefix, nothing else):
#   base   no doctrine (faithful baseline: grep + whole-file read)
#   lean1  v1 doctrine, ~1.5k tok  (the shipped one; measured -12.2% real / +15.5% total)
#   lean2  TINY doctrine (~120 tok) + HARD ranged-read rule + top-k 3
#   lean3  lean2 + explicit turn-minimisation (answer from search output alone when sufficient)
set -uo pipefail

SRC="${SRC:-/Users/suhaan/devenv/graphloop-build/entire-loop}"
OUT="${OUT:-/Users/suhaan/devenv/graphloop-build/leanbench/results2}"
MODEL="${MODEL:-sonnet}"
RUNS="${RUNS:-3}"
MAXTURNS="${MAXTURNS:-30}"
ARMS="${ARMS:-base lean1 lean2 lean3}"   # add lean4 via ARMS=
mkdir -p "$OUT"

task_id=(T1 T2 T3 T4)
task_txt=(
"Where is the external measure command actually executed as a subprocess? Report the file:line and the function name."
"Which functions call runMeasureShell? Report every caller with file:line."
"Explain how a verifier-dropped proposal is prevented from resurfacing after a process resume. Report the relevant symbols with file:line."
"In internal/org/router.go, what threshold values decide the full-audit route? Report the values."
)
SUFFIX="

Report concisely. Do NOT edit, create, or delete any file."

read -r -d '' D_LEAN1 <<'EOF'
You are in lean-mode. Follow this doctrine exactly — it is measured to cut tokens:

1. SEARCH FIRST. Your first action for locating code must be ONE call:
     entire graph search --repo . --profile full --format agent --top-k 5 --query "<the task in one sentence>"
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
EOF

# lean2: minimal tokens, hard ranged-read rule (the v1 arm ignored offset/limit entirely)
read -r -d '' D_LEAN2 <<'EOF'
Locate code with ONE call, then act:
  entire graph search --repo . --profile full --format agent --top-k 3 --query "<task>"
  callers: entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
Then Read ONLY with offset+limit (limit<=120) around the reported line. Never read a whole file,
never grep to locate, never re-verify. If the task names an exact file, read that range directly.
Answer terse.

TASK:
EOF

# lean3: lean2 + stop-early / turn minimisation
read -r -d '' D_LEAN3 <<'EOF'
Locate code with ONE call, then act:
  entire graph search --repo . --profile full --format agent --top-k 3 --query "<task>"
  callers: entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
The search output already contains file:line + a code snippet. If it answers the task, ANSWER
IMMEDIATELY without any further tool call. Otherwise Read ONCE with offset+limit (limit<=120)
around the reported line. Never read a whole file, never grep to locate, never re-verify, never
open a second file unless the answer is provably not in the first. Minimise turns. Answer terse.

TASK:
EOF


read -r -d '' D_LEAN4 <<'EOF'
If the task already names a specific file, go STRAIGHT to it with a ranged Read (offset+limit,
limit<=120) — do NOT search, do NOT list, do NOT grep. Otherwise locate with ONE call:
  entire graph search --repo . --profile full --format agent --top-k 3 --query "<task>"
  callers: entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
That search output already contains file:line + a code snippet. If it answers the task, ANSWER
IMMEDIATELY with no further tool call. Otherwise ONE ranged Read around the reported line.
Never read a whole file, never grep to locate, never re-verify, never open a second file unless the
answer is provably not in the first. Minimise turns — every extra turn re-reads the whole context.
Answer terse.

TASK:
EOF


# lean5 = lean4 doctrine, adapted for a Bash-only tool surface (ranged read via sed)
read -r -d '' D_LEAN5 <<'EOF'
You have ONLY the Bash tool. Use it as follows and minimise turns.
If the task names a specific file, read just the relevant window directly:
  sed -n '<start>,<end>p' <file>          # <=120 lines, no whole-file cat
Otherwise locate with ONE call:
  entire graph search --repo . --profile full --format agent --top-k 3 --query "<task>"
  callers: entire graph neighbors --repo . --symbol X --relation CALLS --direction in --format agent
That output already has file:line + a snippet. If it answers the task, ANSWER IMMEDIATELY with no
further call. Otherwise ONE sed window around the reported line. Never cat a whole file, never grep
to locate, never re-verify, never open a second file unless the answer is provably not in the first.
Answer terse.

TASK:
EOF

doctrine_for() {
  case "$1" in
    base)  printf '' ;;
    lean1) printf '%s\n' "$D_LEAN1" ;;
    lean2) printf '%s\n' "$D_LEAN2" ;;
    lean3) printf '%s\n' "$D_LEAN3" ;;
    lean4) printf '%s\n' "$D_LEAN4" ;;
    lean5) printf '%s\n' "$D_LEAN5" ;;
  esac
}

run_one() { # arm task_idx run_no
  local arm="$1" ti="$2" rn="$3"
  local tag="${task_id[$ti]}-${arm}-r${rn}"
  [ -s "$OUT/$tag.json" ] && { echo "skip $tag (exists)"; return 0; }
  local dst; dst="$(mktemp -d "/tmp/lb2-${tag}-XXXX")"
  git clone --quiet --local --no-hardlinks "$SRC" "$dst/repo" 2>/dev/null || { echo "CLONE FAIL $tag"; return 1; }
  rm -rf "$dst/repo/.entire" "$dst/repo/.claude" 2>/dev/null
  for f in "$dst/repo/CLAUDE.md" "$dst/repo/AGENTS.md"; do
    [ -f "$f" ] && sed -i '' '/entire-graph:begin/,/entire-graph:end/d' "$f" 2>/dev/null
  done
  local prompt; prompt="$(doctrine_for "$arm")${task_txt[$ti]}${SUFFIX}"
  # per-arm tool surface. lean5 tests the research-backed "fewer tool definitions" lever:
  # tool schemas ride in the cached prefix and are re-read (0.1x) every turn.
  local tools; case "$arm" in
    lean5) tools="Bash" ;;
    *)     tools="Read Grep Glob Bash" ;;
  esac
  ( cd "$dst/repo" && exec claude -p "$prompt" \
      --model "$MODEL" --output-format json --max-turns "$MAXTURNS" \
      --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
      --allowedTools $tools \
      --dangerously-skip-permissions < /dev/null ) > "$OUT/$tag.json" 2> "$OUT/$tag.err"
  echo "done $tag"
  rm -rf "$dst"
}

echo "bench2: model=$MODEL runs=$RUNS arms=[$ARMS] -> $OUT"
for rn in $(seq 1 "$RUNS"); do
  for ti in "${!task_id[@]}"; do
    for a in $ARMS; do run_one "$a" "$ti" "$rn"; done
  done
done
echo "BENCH2 COMPLETE"
