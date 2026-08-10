#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# uninstall.sh — 知识库考古流水线卸载脚本
#
# 用法：在【目标项目根目录】执行
#   cd /path/to/your-project
#   bash /path/to/ai-knowledge/uninstall.sh
#
# 删除内容（仅删除 install.sh 安装的文件，不触碰知识库产出）：
#   .cursor/skills/archaeology-commander/     ← 项目级 Cursor SKILL
#   .gemini/skills/archaeology-commander/     ← 项目级 Gemini SKILL
#   .cursor/rules/collaboration-protocol.mdc  ← Cursor 协作协议
#   .gemini/rules/collaboration-protocol.md   ← Gemini 协作协议
#   .ai-knowledge/                            ← 项目配置目录
#
# 不删除的内容：
#   old-readme/                               ← 用户的旧文档，不自动删除
#   {project}-knowledge/                      ← 知识库产出，不自动删除
#
# 如需同时删除知识库产出，加 --purge 参数：
#   bash /path/to/ai-knowledge/uninstall.sh --purge
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "${PROJECT_DIR}")"
PURGE=false

for arg in "$@"; do
    [[ "$arg" == "--purge" ]] && PURGE=true
done

echo "目标项目：${PROJECT_DIR}"
echo "项目名称：${PROJECT_NAME}"
if $PURGE; then
    echo "模式：完整清除（含知识库产出）"
else
    echo "模式：仅删除工具文件（保留知识库产出）"
fi
echo ""

# ── 确认 ──────────────────────────────────────────────────────────────────────
read -r -p "确认删除？[y/N] " confirm
if [[ "${confirm:-N}" != "y" && "${confirm:-N}" != "Y" ]]; then
    echo "已取消。"
    exit 0
fi
echo ""

REMOVED=0

_remove() {
    local target="$1"
    if [[ -e "$target" || -L "$target" ]]; then
        rm -rf "$target"
        echo "  ✓ 已删除：$target"
        REMOVED=$((REMOVED+1))
    else
        echo "  - 不存在（跳过）：$target"
    fi
}

# ── 删除工具安装文件 ──────────────────────────────────────────────────────────
echo "[1/3] 删除 Gemini SKILL..."
# _remove "${PROJECT_DIR}/.gemini/skills/archaeology-commander"

echo "[2/3] 删除协作协议..."
_remove "${PROJECT_DIR}/.gemini/rules/collaboration-protocol.md"

echo "[3/3] 删除工具包目录（含 prompts、USAGE、config）..."
_remove "${PROJECT_DIR}/.ai-knowledge"

# ── purge 模式：额外删除知识库产出 ───────────────────────────────────────────
if $PURGE; then
    echo ""
    echo "[purge] 删除知识库产出..."
    _remove "${PROJECT_DIR}/${PROJECT_NAME}-knowledge"
    _remove "${PROJECT_DIR}/old-readme"
fi

# ── 完成 ──────────────────────────────────────────────────────────────────────
echo ""
echo "✅ 卸载完成（删除了 ${REMOVED} 个文件/目录）"

if ! $PURGE; then
    OUTPUT_DIR="${PROJECT_NAME}-knowledge"
    if [[ -d "${PROJECT_DIR}/${OUTPUT_DIR}" ]]; then
        echo ""
        echo "提示：知识库产出目录 ${OUTPUT_DIR}/ 已保留。"
        echo "      如需删除，执行：rm -rf ${OUTPUT_DIR}/"
        echo "      或重新运行：bash /path/to/ai-knowledge/uninstall.sh --purge"
    fi
    if [[ -d "${PROJECT_DIR}/old-readme" ]]; then
        echo "提示：旧文档目录 old-readme/ 已保留。"
        echo "      如需删除，执行：rm -rf old-readme/"
    fi
fi
