#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# install.sh — 知识库考古流水线安装脚本
#
# 用法：在【目标项目根目录】执行
#   cd /path/to/your-project
#   bash /path/to/ai-knowledge/install.sh
#
# 自举用法（允许在 ai-knowledge 仓库自身安装到自己）：
#   cd /path/to/ai-knowledge
#   bash ./install.sh --allow-self-install
#
# 安装结果（全部在项目目录内，完整自包含）：
#
#   .ai-knowledge/
#     config.json                    ← 项目配置
#     USAGE.md                       ← 使用说明
#     uninstall.sh                   ← 卸载脚本
#     collaboration-protocol.md      ← 协作协议原文
#     prompts/                       ← 完整 prompt 模板（12 个）
#     scripts/                       ← 执行脚本（run-archaeology.sh）
#
#   .gemini/skills/archaeology-commander/SKILL.md   ← Gemini 项目级 SKILL
#   .gemini/rules/collaboration-protocol.md         ← Gemini 协作协议
#   old-readme/                                     ← 旧文档目录
# ═══════════════════════════════════════════════════════════════════════════════

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "${PROJECT_DIR}")"
ALLOW_SELF_INSTALL=false

for arg in "$@"; do
    case "$arg" in
        --allow-self-install)
            ALLOW_SELF_INSTALL=true
            ;;
        *)
            echo "❌ 错误：未知参数：$arg"
            echo "    用法：bash ${BASH_SOURCE[0]} [--allow-self-install]"
            exit 1
            ;;
    esac
done

# ── 防呆检测：禁止在 Home 目录安装；仓库自身目录仅在显式开关下允许 ─────────────
if [[ "${PROJECT_DIR}" == "${HOME}" ]]; then
    echo "❌ 错误：当前目录是 Home 目录（${HOME}），禁止在此安装。"
    echo "    请先 cd 进入你的目标项目目录，再重新执行本脚本。"
    echo "    示例：cd ~/Desktop/work/your-project && bash ${BASH_SOURCE[0]}"
    exit 1
fi
if [[ "${PROJECT_DIR}" == "${REPO_DIR}" && "${ALLOW_SELF_INSTALL}" != "true" ]]; then
    echo "❌ 错误：当前目录是 ai-knowledge 仓库自身，默认禁止直接自安装。"
    echo "    如需在仓库自身进行自举验证，请显式执行："
    echo "    bash ${BASH_SOURCE[0]} --allow-self-install"
    echo "    或先 cd 进入其他目标项目目录后再执行本脚本。"
    exit 1
fi
OUTPUT_DIR="${PROJECT_NAME}-knowledge"
AI_KNOWLEDGE_DIR="${PROJECT_DIR}/.ai-knowledge"

echo "工具仓库：${REPO_DIR}"
echo "目标项目：${PROJECT_DIR}"
echo "项目名称：${PROJECT_NAME}"
echo "产出目录：${OUTPUT_DIR}/"
echo ""

# ── 1. 安装工具包到 .ai-knowledge/ ───────────────────────────────────────────
echo "[1/4] 安装工具包到 .ai-knowledge/..."
mkdir -p "${AI_KNOWLEDGE_DIR}/prompts"

# prompts（从 Skill 资源目录同步）
cp -f "${REPO_DIR}/.gemini/skills/archaeology-commander/resources/prompts/"*.md "${AI_KNOWLEDGE_DIR}/prompts/"
echo "    ✓ .ai-knowledge/prompts/ ($(ls "${AI_KNOWLEDGE_DIR}/prompts/" | wc -l | tr -d ' ') 个模板)"

# 协作协议原文
cp -f "${REPO_DIR}/collaboration-protocol.md" "${AI_KNOWLEDGE_DIR}/collaboration-protocol.md"
echo "    ✓ .ai-knowledge/collaboration-protocol.md"

# 使用说明
cp -f "${REPO_DIR}/USAGE.md" "${AI_KNOWLEDGE_DIR}/USAGE.md"
echo "    ✓ .ai-knowledge/USAGE.md"

# 卸载脚本
cp -f "${REPO_DIR}/uninstall.sh" "${AI_KNOWLEDGE_DIR}/uninstall.sh"
chmod +x "${AI_KNOWLEDGE_DIR}/uninstall.sh"
echo "    ✓ .ai-knowledge/uninstall.sh"

# 项目配置
cat > "${AI_KNOWLEDGE_DIR}/config.json" <<EOF
{
  "project_name": "${PROJECT_NAME}",
  "project_dir": "${PROJECT_DIR}",
  "output_dir": "${OUTPUT_DIR}",
  "tool_home": "${AI_KNOWLEDGE_DIR}",
  "prompt_dir": "${AI_KNOWLEDGE_DIR}/prompts",
  "installed_from": "${REPO_DIR}",
  "installed_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
echo "    ✓ .ai-knowledge/config.json"
 
# 执行脚本
mkdir -p "${AI_KNOWLEDGE_DIR}/scripts/logs"
cp -f "${REPO_DIR}/scripts/knowledge-archaeology/run-archaeology.sh" "${AI_KNOWLEDGE_DIR}/scripts/"
chmod +x "${AI_KNOWLEDGE_DIR}/scripts/run-archaeology.sh"
echo "    ✓ .ai-knowledge/scripts/run-archaeology.sh"

# ── 2. 安装 Gemini SKILL（项目级）────────────────────────────────────────────
echo "[2/4] 安装 Gemini SKILL（项目级）..."
mkdir -p "${PROJECT_DIR}/.gemini/skills/archaeology-commander"
_src="${REPO_DIR}/.gemini/skills/archaeology-commander/SKILL.md"
_dst="${PROJECT_DIR}/.gemini/skills/archaeology-commander/SKILL.md"
if [[ "$(realpath "${_src}")" != "$(realpath "${_dst}" 2>/dev/null)" ]]; then
    cp -f "${_src}" "${_dst}"
fi
echo "    ✓ .gemini/skills/archaeology-commander/SKILL.md"

# resources/prompts（SKILL.md frontmatter 声明的依赖，必须随 Skill 一起部署）
mkdir -p "${PROJECT_DIR}/.gemini/skills/archaeology-commander/resources/prompts"
_res_src="${REPO_DIR}/.gemini/skills/archaeology-commander/resources/prompts"
_res_dst="${PROJECT_DIR}/.gemini/skills/archaeology-commander/resources/prompts"
if [[ "$(realpath "${_res_src}")" != "$(realpath "${_res_dst}" 2>/dev/null)" ]]; then
    cp -f "${_res_src}/"*.md "${_res_dst}/"
fi
echo "    ✓ .gemini/skills/archaeology-commander/resources/prompts/ ($(ls "${_res_dst}/" | wc -l | tr -d ' ') 个模板)"

# ── 3. 安装协作协议到 Gemini 规则目录 ────────────────────────────────────────
echo "[3/4] 安装协作协议到 Gemini 规则目录..."
mkdir -p "${PROJECT_DIR}/.gemini/rules"
cat << 'FRONTMATTER_EOF' > "${PROJECT_DIR}/.gemini/rules/collaboration-protocol.md"
---
description: 知识库流水线底层协作法典
globs: **/*
trigger: always_on
---
FRONTMATTER_EOF
cat "${REPO_DIR}/collaboration-protocol.md" >> "${PROJECT_DIR}/.gemini/rules/collaboration-protocol.md"
echo "    ✓ .gemini/rules/collaboration-protocol.md"

# ── 4. 创建旧文档目录 ─────────────────────────────────────────────────────────
echo "[4/4] 准备旧文档目录..."
mkdir -p "${PROJECT_DIR}/old-readme"
echo "    ✓ old-readme/ （如已存在则保留原有内容）"

# ── 验证 ──────────────────────────────────────────────────────────────────────
echo ""
echo "── 验证安装结果 ──────────────────────────────────────────────────────────"
PASS=0; FAIL=0
_check() {
    if [[ -e "$1" ]]; then
        echo "  ✓ $1"
        PASS=$((PASS+1))
    else
        echo "  ✗ $1 （缺失）"
        FAIL=$((FAIL+1))
    fi
}
_check "${AI_KNOWLEDGE_DIR}/config.json"
_check "${AI_KNOWLEDGE_DIR}/USAGE.md"
_check "${AI_KNOWLEDGE_DIR}/uninstall.sh"
_check "${AI_KNOWLEDGE_DIR}/collaboration-protocol.md"
_check "${AI_KNOWLEDGE_DIR}/prompts/step-01-skeleton.md"
_check "${AI_KNOWLEDGE_DIR}/scripts/run-archaeology.sh"
_check "${PROJECT_DIR}/.gemini/skills/archaeology-commander/SKILL.md"
_check "${PROJECT_DIR}/.gemini/skills/archaeology-commander/resources/prompts/step-01-skeleton.md"
_check "${PROJECT_DIR}/.gemini/rules/collaboration-protocol.md"
_check "${PROJECT_DIR}/old-readme"
echo ""
if (( FAIL == 0 )); then
    echo "✅ 安装完成（${PASS} 项全部通过）"
else
    echo "❌ 安装异常：${FAIL} 项缺失，请检查上方错误"
    exit 1
fi
echo ""
echo "下一步："
echo "  1. 重启 Gemini CLI 使 SKILL 生效"
echo "  2. 进入项目目录，执行 gemini --yolo，输入：运行考古流水线"
echo "     （项目名称已自动配置为 ${PROJECT_NAME}）"
echo ""
echo "或者运行脚本模式："
echo "  bash .ai-knowledge/scripts/run-archaeology.sh ${PROJECT_NAME}"
echo ""
echo "使用说明：cat .ai-knowledge/USAGE.md"
echo "如需卸载：bash .ai-knowledge/uninstall.sh"
