#!/usr/bin/env bash
# The paper's experiment grid; every run is resumable.
#   usage: scripts/run_grid.sh MODELS_FILE      (format: see scripts/models.example.txt)
#   ANTHROPIC_API_KEY / OPENAI_API_KEY must be set for the corresponding providers;
#   compat: entries use $BASE_URL (e.g. a local vLLM server) and $COMPAT_KEY_ENV.
set -euo pipefail
cd "$(dirname "$0")/.."

MODELS_FILE=${1:?usage: scripts/run_grid.sh MODELS_FILE}
EPISODES=${EPISODES:-data/dev_core.jsonl}
NOISY=${NOISY:-data/dev_noisy.jsonl}
REFS=${REFS:-data/dev_refs.jsonl}
OUT=${OUT:-results/dev}
WORKERS=${WORKERS:-8}
mkdir -p "$OUT"

mapfile -t MODELS < <(grep -vE '^[[:space:]]*(#|$)' "$MODELS_FILE")

if [ ! -f "$REFS" ]; then
  cat "$EPISODES" "$NOISY" > "$OUT/episodes.jsonl"
  bitsbench refs --episodes "$OUT/episodes.jsonl" --out "$REFS" --workers 4
fi

for entry in "${MODELS[@]}"; do
  IFS='|' read -r spec effort label <<<"$entry"
  args=(--model "$spec" --workers "$WORKERS" --cache "$OUT/cache.sqlite")
  [ -n "$effort" ] && args+=(--effort "$effort")
  if [[ "$spec" == compat:* ]]; then
    args+=(--base-url "${BASE_URL:?compat models need BASE_URL}" --api-key-env "${COMPAT_KEY_ENV:-OPENAI_API_KEY}")
  fi
  for cond in active passive_random passive_eig; do
    bitsbench run "${args[@]}" --episodes "$EPISODES" --condition "$cond" --out "$OUT/$label.jsonl"
  done
  bitsbench run "${args[@]}" --episodes "$NOISY" --condition active --out "$OUT/$label.jsonl"
done

for ref in eig random; do
  bitsbench run --model "ref:$ref" --episodes "$EPISODES" --out "$OUT/ref-$ref.jsonl"
  bitsbench run --model "ref:$ref" --episodes "$NOISY" --out "$OUT/ref-$ref.jsonl"
done

bitsbench report --results "$OUT"/*.jsonl --refs "$REFS" --out "reports/$(basename "$OUT")"
