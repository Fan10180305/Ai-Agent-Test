#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="$ROOT/.tools/bin:/d/Users/v55235230/AppData/Local/Programs/nodejs:/d/Users/v55235230/AppData/Roaming/npm:${LOCALAPPDATA:-}/Programs/nodejs:${APPDATA:-}/npm:$PATH"

STATE_FILE="${OUTPUT_STATE:-$ROOT/qpon-bigdata-knowledge/.tmp/pipeline-state.env}"
# shellcheck disable=SC1090
source "$STATE_FILE"

STEP_TEMPLATE="${1:?usage: run-step.sh <step-template-basename> [step-log-name]}"
STEP_NAME="${2:-$STEP_TEMPLATE}"
PRIOR_FILE="${3:-}"
MODULE_NAME="${4:-}"
MODULE_SUFFIX="${5:-}"
MODULE_CORE="${6:-}"

TEMPLATE_PATH="${PROMPT_DIR}/${STEP_TEMPLATE}.md"
NEXT_PROMPT="${OUTPUT_DIR}/.tmp/next-prompt.md"
ARCHIVED_PROMPT="${OUTPUT_DIR}/${STEP_NAME}_prompt.md"
STEP_LOG="${LOG_DIR}/${STEP_NAME}.log"
SUCCESS_FILE="${LOG_DIR}/${STEP_NAME}.success.txt"
RELAY_FILE="${LOG_DIR}/${STEP_NAME}.relay.txt"

[[ -f "$TEMPLATE_PATH" ]] || { echo "MISSING_TEMPLATE=$TEMPLATE_PATH"; exit 1; }
mkdir -p "${OUTPUT_DIR}/.tmp" "${LOG_DIR}"

PRIOR_SUMMARY="无先验知识（Step 0 为 NO_DOCS，或首步）。"
if [[ -n "$PRIOR_FILE" && -f "$PRIOR_FILE" ]]; then
  PRIOR_SUMMARY=$(cat "$PRIOR_FILE")
fi

python .tools/render_prompt.py \
  --state "$STATE_FILE" \
  --template "$TEMPLATE_PATH" \
  --out "$NEXT_PROMPT" \
  --prior-summary "$PRIOR_SUMMARY" \
  --module-name "$MODULE_NAME" \
  --module-suffix "$MODULE_SUFFIX" \
  --module-core-classes "$MODULE_CORE"

cp "$NEXT_PROMPT" "$ARCHIVED_PROMPT"

echo "[$(date '+%F %T')] START ${STEP_NAME}" | tee -a "${LOG_DIR}/pipeline.log"

# Prefer account default model (avoid hardcoding unavailable model ids)
set +e
cat "$NEXT_PROMPT" | gemini -p '' --yolo --skip-trust > "$STEP_LOG" 2>&1
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  echo "[$(date '+%F %T')] RETRY ${STEP_NAME} rc=$RC" | tee -a "${LOG_DIR}/pipeline.log"
  sleep 10
  set +e
  cat "$NEXT_PROMPT" | gemini -p '' --yolo --skip-trust > "$STEP_LOG" 2>&1
  RC=$?
  set -e
fi

grep -A 20 '\[!SUCCESS\]' "$STEP_LOG" | head -25 > "$SUCCESS_FILE" || true
grep -A 10 '\[!RELAY\]' "$STEP_LOG" | head -12 > "$RELAY_FILE" || true

if [[ ! -s "$SUCCESS_FILE" ]]; then
  echo "[$(date '+%F %T')] FAIL ${STEP_NAME} missing [!SUCCESS] rc=$RC" | tee -a "${LOG_DIR}/pipeline.log"
  echo "LOG=$STEP_LOG"
  exit 3
fi

# Update relay strategy for next step
if [[ -s "$RELAY_FILE" ]]; then
  # Store multi-line relay into state as a single escaped-ish blob file
  cp "$RELAY_FILE" "${OUTPUT_DIR}/.tmp/last-relay.txt"
  # Keep RELAY_STRATEGY as a one-line pointer-ish summary for render L1
  RELAY_ONE_LINE=$(tr '\n' ' ' < "$RELAY_FILE" | sed 's/  */ /g' | cut -c1-800)
  # rewrite RELAY_STRATEGY in state file
  grep -v '^RELAY_STRATEGY=' "$STATE_FILE" > "${STATE_FILE}.tmp" || true
  printf 'RELAY_STRATEGY=%s\n' "$RELAY_ONE_LINE" >> "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"
else
  echo "[$(date '+%F %T')] WARN ${STEP_NAME} missing [!RELAY], degrade default" | tee -a "${LOG_DIR}/pipeline.log"
  grep -v '^RELAY_STRATEGY=' "$STATE_FILE" > "${STATE_FILE}.tmp" || true
  printf 'RELAY_STRATEGY=%s\n' "无先验接力偏好，请按标准考古规范执行。" >> "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

echo "[$(date '+%F %T')] OK ${STEP_NAME}" | tee -a "${LOG_DIR}/pipeline.log"
echo "SUCCESS_FILE=$SUCCESS_FILE"
echo "RELAY_FILE=$RELAY_FILE"
echo "LOG=$STEP_LOG"
exit 0
