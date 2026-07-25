#!/usr/bin/env bash
# Install the lean-mode skill for Claude Code (user scope).
#   bash install.sh          copy   into ~/.claude/skills/lean-mode
#   bash install.sh --link   symlink into ~/.claude/skills/lean-mode (repo = source of truth)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/skills/lean-mode"
DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/lean-mode"
MODE=copy
[ "${1:-}" = "--link" ] && MODE=link

[ -f "$SRC/SKILL.md" ] || { echo "error: $SRC/SKILL.md not found" >&2; exit 1; }
mkdir -p "$(dirname "$DST")"

if [ -e "$DST" ] || [ -L "$DST" ]; then
  BK="$DST.bak.$$"
  echo "existing install found -> backing up to $BK"
  mv "$DST" "$BK"
fi

if [ "$MODE" = link ]; then
  ln -s "$SRC" "$DST"
  echo "linked  $DST -> $SRC"
else
  mkdir -p "$DST"
  cp -R "$SRC/." "$DST/"
  echo "copied  $SRC -> $DST"
fi
chmod +x "$DST/scripts/lean-setup.sh" 2>/dev/null || true

echo
bash "$DST/scripts/lean-setup.sh" || true
echo
echo "installed. use it with:  /lean-mode   (or say \"lean mode\")"
