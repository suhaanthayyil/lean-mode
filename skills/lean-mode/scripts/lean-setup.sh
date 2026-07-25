#!/usr/bin/env bash
# lean-mode setup — verify the token-efficiency stack; never installs a missing tool.
# Usage: lean-setup.sh [--install-guide] [--repo PATH]
#   --install-guide  run `entire graph init-agents` (additive: writes .entire/graph-agent.md and
#                    appends one delimited block to AGENTS.md/CLAUDE.md; safe to re-run)
set -uo pipefail

REPO="."
INSTALL_GUIDE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --install-guide) INSTALL_GUIDE=1 ;;
    --repo) shift; REPO="${1:-.}" ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

have() { command -v "$1" >/dev/null 2>&1; }
ok=0; miss=0

echo "lean-mode status"
echo "----------------"

# 1. RTK
if have rtk; then
  v="$(rtk --version 2>/dev/null | head -1)"
  echo "rtk            OK   $v   (prefix: rtk read|grep|git|test|find|gh)"
  ok=$((ok+1))
else
  echo "rtk            --   absent; skipping (do NOT auto-install)"
  miss=$((miss+1))
fi

# 2. caveman plugin (output compression modes)
cav="$(ls -d "$HOME"/.claude/plugins/cache/caveman/* 2>/dev/null | head -1)"
if [ -n "$cav" ]; then
  echo "caveman        OK   plugin present   (/caveman lite|full|ultra)"
  ok=$((ok+1))
else
  echo "caveman        --   plugin absent; use the output rules in SKILL.md manually"
  miss=$((miss+1))
fi

# 3. entire graph
if have entire && entire graph version >/dev/null 2>&1; then
  gv="$(entire graph version 2>/dev/null | head -1)"
  echo "entire graph   OK   version $gv   (search-first: entire graph search --repo . --profile full --query ...)"
  ok=$((ok+1))

  if [ -f "$REPO/.entire/graph-agent.md" ]; then
    echo "  repo guide   OK   $REPO/.entire/graph-agent.md present"
  elif [ "$INSTALL_GUIDE" -eq 1 ]; then
    echo "  repo guide   installing into $REPO ..."
    entire graph init-agents --repo "$REPO" 2>&1 | sed 's/^/    /'
  else
    echo "  repo guide   --   not installed; re-run with --install-guide"
  fi
else
  echo "entire graph   --   absent; skipping (grep/read fallback)"
  miss=$((miss+1))
fi

echo "----------------"
echo "active: $ok/3   missing: $miss"
echo
echo "reminders:"
echo "  - SEARCH FIRST; one search, then read a ~120-line range and edit."
echo "  - ALWAYS --format agent --top-k 5 (default json is ~5x bigger: 9610B vs 1866B measured)"
echo "  - who-calls-X = neighbors --relation CALLS --direction in (291B); blast radius = impact (1740B)"
echo "  - 'unknown command impact' means a STALE installed binary — rebuild + entire plugin install"
echo "  - bake caveman-ultra + rtk directives into every subagent/workflow prompt you author."
