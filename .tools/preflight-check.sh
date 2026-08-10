#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Local toolchains (jq wrapper + Node/npm/gemini on Windows user install)
export PATH="$(pwd)/.tools/bin:${LOCALAPPDATA:-}/Programs/nodejs:${APPDATA:-}/npm:/d/Users/v55235230/AppData/Local/Programs/nodejs:/d/Users/v55235230/AppData/Roaming/npm:${PATH}"

PROJECT_NAME=qpon-bigdata
OUTPUT_DIR=qpon-bigdata-knowledge
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
PROMPT_DIR=".gemini/skills/archaeology-commander/resources/prompts"

echo "TIMESTAMP=${TIMESTAMP}"
echo "PROJECT_NAME=${PROJECT_NAME}"
echo "OUTPUT_DIR=${OUTPUT_DIR}"

mkdir -p "${OUTPUT_DIR}/.logs/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

# Windows/MSYS: if 'latest' is a real directory from a prior failed run, remove it first.
# Prefer symlink; fall back to pointer file so set -e does not abort Preflight.
LOG_PARENT="${OUTPUT_DIR}/.logs"
if [ -e "${LOG_PARENT}/latest" ] && [ ! -L "${LOG_PARENT}/latest" ]; then
  rm -rf "${LOG_PARENT}/latest"
  echo "1_log_latest_cleanup=REMOVED_NON_SYMLINK_DIR"
fi
if ln -sfn "${TIMESTAMP}" "${LOG_PARENT}/latest" 2>/tmp/preflight_ln_err; then
  echo "1_log_symlink=OK"
else
  echo "1_log_symlink=WARN ($(tr '\n' ' ' </tmp/preflight_ln_err))"
  printf '%s\n' "${TIMESTAMP}" > "${LOG_PARENT}/LATEST_RUN.txt"
  echo "1_log_pointer=OK"
fi
echo "1_log_and_output=OK"

PROTOCOL_OK=0
if [ -f "collaboration-protocol.md" ] || [ -f "scripts/knowledge-archaeology/collaboration-protocol.md" ]; then
  PROTOCOL_OK=1
  echo "2_protocol_source=OK"
else
  echo "2_protocol_source=FAIL"
fi

if command -v jq >/dev/null 2>&1; then
  echo "3_jq=OK ($(jq --version))"
  JQ_OK=1
else
  echo "3_jq=FAIL"
  JQ_OK=0
fi

if command -v gemini >/dev/null 2>&1; then
  GEMINI_VER=$(gemini --version 2>/dev/null | head -1 || true)
  echo "4_gemini=OK ($(command -v gemini)) version=${GEMINI_VER}"
  GEMINI_OK=1
else
  echo "4_gemini=FAIL"
  GEMINI_OK=0
fi

if [ -d "${PROMPT_DIR}" ]; then
  echo "5_prompts=OK (count=$(ls "${PROMPT_DIR}" | wc -l))"
  PROMPTS_OK=1
else
  echo "5_prompts=FAIL"
  PROMPTS_OK=0
fi

if command -v cursor >/dev/null 2>&1; then
  echo "6_cursor=OK ($(command -v cursor))"
else
  echo "6_cursor=FAIL"
fi

KB_MD_COUNT=$(find "${OUTPUT_DIR}" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "${KB_MD_COUNT}" -gt 0 ]; then
  echo "7_knowledge_base_exists=true (md=${KB_MD_COUNT})"
else
  echo "7_knowledge_base_exists=false"
fi

echo "---SUMMARY---"
if [ "${JQ_OK}" -eq 1 ] && [ "${PROMPTS_OK}" -eq 1 ] && [ "${PROTOCOL_OK}" -eq 1 ]; then
  if [ "${GEMINI_OK}" -eq 1 ]; then
    echo "PREFLIGHT=PASS"
    exit 0
  else
    echo "PREFLIGHT=BLOCKED_GEMINI_MISSING"
    exit 2
  fi
else
  echo "PREFLIGHT=FAIL"
  exit 1
fi
