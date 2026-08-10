#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="$ROOT/.tools/bin:${LOCALAPPDATA:-}/Programs/nodejs:${APPDATA:-}/npm:/d/Users/v55235230/AppData/Local/Programs/nodejs:/d/Users/v55235230/AppData/Roaming/npm:$PATH"

PROJECT_NAME=qpon-bigdata
PROJECT_DISPLAY=qpon-bigdata
OUTPUT_DIR=qpon-bigdata-knowledge
LEGACY_DOCS_DIR=old-readme/
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
LOG_DIR="${OUTPUT_DIR}/.logs/${TIMESTAMP}"
PROMPT_DIR=".gemini/skills/archaeology-commander/resources/prompts"
STATE_FILE="${OUTPUT_DIR}/.tmp/pipeline-state.env"

mkdir -p "${OUTPUT_DIR}/.tmp" "${LOG_DIR}" "${LEGACY_DOCS_DIR}"
if [ -e "${OUTPUT_DIR}/.logs/latest" ] && [ ! -L "${OUTPUT_DIR}/.logs/latest" ]; then
  rm -rf "${OUTPUT_DIR}/.logs/latest"
fi
ln -sfn "${TIMESTAMP}" "${OUTPUT_DIR}/.logs/latest" 2>/dev/null || \
  printf '%s\n' "${TIMESTAMP}" > "${OUTPUT_DIR}/.logs/LATEST_RUN.txt"

# --- NO_DOCS placeholder (SKIP_STEP0) ---
cat > "${OUTPUT_DIR}/Legacy_${PROJECT_NAME}_Claims.md" <<EOF
# Legacy Claims: ${PROJECT_NAME}

> [!WARNING] 无旧文档
> ${LEGACY_DOCS_DIR} 目录不存在或为空，本步骤跳过声称提取。
> 后续步骤的先验知识注入层将留空，直接基于代码事实构建知识库。

---

> [!SUCCESS] 旧文档情报萃取闭环验证
> - LEGACY_STATUS: NO_DOCS
> - 扫描范围：${LEGACY_DOCS_DIR} 下实际存在 [0] 个文件
> - 提取结果：识别了 [0] 条涉及 ${PROJECT_NAME} 的声称（LEGACY_COUNT=0）
> - 待确认项：[0] 条标记为【待确认】的声称
> - EOF 状态：N/A
EOF

# --- Structure probe ---
{
  echo "===ROOT_DIRS==="
  ls -1d */ 2>/dev/null | sed 's|/$||' || true
  echo "===POM==="
  find . -maxdepth 2 -name 'pom.xml' 2>/dev/null | sort || true
  echo "===DAG_PACKAGES==="
  ls -1d dags/*/ 2>/dev/null | sed 's|/$||' || true
  echo "===DAG_PY_COUNT==="
  find dags -type f -name '*.py' 2>/dev/null | wc -l | tr -d ' '
} > "${LOG_DIR}/structure-probe.txt"

ACTUAL_MODULE_PREFIX=NON_JAVA
if find . -maxdepth 2 -name 'pom.xml' 2>/dev/null | grep -q .; then
  # Prefer prefix from *-start style dirs if present; else keep detected
  ACTUAL_MODULE_PREFIX=$(ls -1d */ 2>/dev/null | sed 's|/$||' | grep -E -- '-start$' | head -1 | sed 's|-start$||' || true)
  if [ -z "${ACTUAL_MODULE_PREFIX}" ]; then
    ACTUAL_MODULE_PREFIX=HAS_POM_BUT_NO_START
  fi
fi

cat > "${STATE_FILE}" <<EOF
PROJECT_NAME=${PROJECT_NAME}
PROJECT_DISPLAY=${PROJECT_DISPLAY}
OUTPUT_DIR=${OUTPUT_DIR}
LEGACY_DOCS_DIR=${LEGACY_DOCS_DIR}
PROMPT_DIR=${PROMPT_DIR}
TIMESTAMP=${TIMESTAMP}
LOG_DIR=${LOG_DIR}
ACTUAL_MODULE_PREFIX=${ACTUAL_MODULE_PREFIX}
SKIP_STEP0=true
EVOLUTION_MODE=false
RUN_BASE=FULL_REBUILD
LEGACY_MODE=NO_DOCS
SCAN_ROOT=dags
RELAY_STRATEGY=无先验接力偏好，请按标准考古规范执行。
EOF

echo "INIT_OK"
echo "STATE_FILE=${STATE_FILE}"
echo "ACTUAL_MODULE_PREFIX=${ACTUAL_MODULE_PREFIX}"
echo "LOG_DIR=${LOG_DIR}"
cat "${LOG_DIR}/structure-probe.txt"
