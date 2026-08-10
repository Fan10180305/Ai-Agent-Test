#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# Knowledge Archaeology Pipeline — 知识库考古流水线
#
# 三层架构：001 指挥官 AI（持续会话） + bash 调度器（本脚本） + 执行 Agent（每步全新）
#
# 用法：
#   cd <项目根目录>
#   bash scripts/knowledge-archaeology/run-archaeology.sh <项目显示名> [legacy_path1] [legacy_path2] ...
#
# 示例：
#   bash scripts/knowledge-archaeology/run-archaeology.sh 签到中心
#   bash scripts/knowledge-archaeology/run-archaeology.sh 签到中心 docs/legacy/
#   bash scripts/knowledge-archaeology/run-archaeology.sh 签到中心 docs/legacy/ README.md
#
# 前置条件：
#   - scripts/knowledge-archaeology/collaboration-protocol.md 存在（自动复制到 .cursor/rules/）
#   - old-readme/ 目录，或通过 legacy 路径参数指定旧文档（自动收集到 old-readme/）
#   - cursor CLI 可用
#   - jq 可用
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 全局常量 ─────────────────────────────────────────────────────────────────

PROJECT_DISPLAY="${1:?用法: $0 <项目显示名> [legacy_path1] [legacy_path2] ...}"

# ── 工具根目录：从脚本自身路径推导 ──────────────────────────────────────────
_SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$_SCRIPT_PATH"
AI_KNOWLEDGE_HOME="$(cd "${_SCRIPT_PATH}/../.." && pwd)"

# ── 优先从 per-project config.json 读取，回退到运行时推导 ─────────────────
_CONFIG="$(pwd)/.ai-knowledge/config.json"
if [[ -f "$_CONFIG" ]] && command -v jq >/dev/null 2>&1; then
    PROJECT_NAME="$(jq -r '.project_name' "$_CONFIG")"
    OUTPUT_DIR="$(jq -r '.output_dir' "$_CONFIG")"
    PROMPT_DIR="$(jq -r '.prompt_dir' "$_CONFIG")"
    _CURSOR_FROM_CONFIG="$(jq -r '.cursor_cmd // empty' "$_CONFIG")"
else
    PROJECT_NAME=$(basename "$(pwd)")
    OUTPUT_DIR="${PROJECT_NAME}-knowledge"
    # 自动探测 Prompt 模板位置：优先使用 Skill 资源目录，回退到本地 .ai-knowledge 安装目录
    if [[ -d "${AI_KNOWLEDGE_HOME}/.gemini/skills/archaeology-commander/resources/prompts" ]]; then
        PROMPT_DIR="${AI_KNOWLEDGE_HOME}/.gemini/skills/archaeology-commander/resources/prompts"
    elif [[ -d "$(pwd)/.ai-knowledge/prompts" ]]; then
        PROMPT_DIR="$(pwd)/.ai-knowledge/prompts"
    else
        PROMPT_DIR="${AI_KNOWLEDGE_HOME}/prompts"
    fi
    _CURSOR_FROM_CONFIG=""
fi

LEGACY_DOCS_DIR="old-readme/"
NEXT_PROMPT="${OUTPUT_DIR}/.tmp/next-prompt.md"
PROTOCOL_SOURCE="${AI_KNOWLEDGE_HOME}/collaboration-protocol.md"
PROTOCOL_TARGET=".cursor/rules/collaboration-protocol.mdc"

RUN_TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
LOG_DIR="${OUTPUT_DIR}/.logs/${RUN_TIMESTAMP}"
LOCAL_LOG_DIR="${SCRIPT_DIR}/logs"

# 可选：用户指定的旧文档/知识库路径（位置参数 2+）
LEGACY_SOURCES=()
if (( $# >= 2 )); then
    for p in "${@:2}"; do
        [[ -n "$p" ]] && LEGACY_SOURCES+=("$p")
    done
fi

STEP_LIST=(
    step-0-legacy
    step-01-skeleton
    step-02-contracts
    step-03-downstream
    step-04-data-model
    step-05-orchestration
    step-06-async
    step-07-config
)

SUFFIXES=(a b c d e f g h i j k l m n o p q r s t u v w x y z)

CURSOR_CMD="${CURSOR_CMD:-${_CURSOR_FROM_CONFIG:-/Applications/Cursor.app/Contents/Resources/app/bin/cursor}}"
CURSOR_MODEL="${CURSOR_MODEL:-auto}"  # 示例：CURSOR_MODEL=opus-4.6-thinking bash run-archaeology.sh <项目显示名>
CURSOR_AGENT_FLAGS="--print --yolo --model ${CURSOR_MODEL}"
TRANSCRIPT_BASE="${HOME}/.cursor/projects/$(pwd | tr '/' '-' | sed 's/^-//')/agent-transcripts"

COMMANDER_ID=""
PIPELINE_START_TIME=""
SKIP_STEP0=false

# ─── 日志系统 ─────────────────────────────────────────────────────────────────

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

log()       { local msg="[$(timestamp)] $*"; echo "$msg" | tee -a "${LOG_DIR}/pipeline.log"; }
log_info()  { log "INFO  $*"; }
log_ok()    { log "  OK  $*"; }
log_error() { log "ERROR $*"; }
log_step()  { log " RUN  $*"; }

# ─── Legacy 文件收集 ─────────────────────────────────────────────────────────

# 将用户指定路径下的 .md/.txt 复制到 old-readme/，统一入口
# 返回收集到的有效文件数（通过全局 COLLECTED_COUNT）
COLLECTED_COUNT=0

collect_legacy_sources() {
    COLLECTED_COUNT=0
    mkdir -p "$LEGACY_DOCS_DIR"

    local total_skipped_ext=0
    local skipped_ext_summary=""

    for src in "${LEGACY_SOURCES[@]}"; do
        if [[ -d "$src" ]]; then
            _collect_from_dir "$src"
        elif [[ -f "$src" ]]; then
            _collect_single_file "$src"
        fi
    done

    if [[ -n "$skipped_ext_summary" ]]; then
        log_info "WARN  跳过 ${total_skipped_ext} 个非 .md/.txt 文件（${skipped_ext_summary}）"
    fi

    if (( COLLECTED_COUNT == 0 )); then
        log_info "WARN  所有路径中未找到有效的 .md/.txt 文件"
    else
        log_ok "收集了 ${COLLECTED_COUNT} 个文件到 ${LEGACY_DOCS_DIR}"
    fi
}

_collect_from_dir() {
    local dir=$1
    local dir_prefix
    dir_prefix=$(echo "$dir" | sed 's|/$||; s|/|-|g')
    local dir_skipped=0
    local dir_ext_map=""

    while IFS= read -r -d '' f; do
        local basename_f
        basename_f=$(basename "$f")
        local ext="${basename_f##*.}"
        ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

        if [[ "$ext" != "md" && "$ext" != "txt" ]]; then
            dir_skipped=$(( dir_skipped + 1 ))
            dir_ext_map="${dir_ext_map}.${ext} "
            continue
        fi

        if [[ ! -s "$f" ]]; then
            log_info "WARN  跳过空文件: $f"
            continue
        fi

        local target_name="${dir_prefix}__${basename_f}"
        _copy_with_dedup "$f" "$target_name"
    done < <(find "$dir" -maxdepth 1 -type f -not -type l -print0 2>/dev/null)

    if (( dir_skipped > 0 )); then
        local ext_counts
        ext_counts=$(echo "$dir_ext_map" | tr ' ' '\n' | sort | uniq -c | \
            awk '{printf "%s ×%s, ", $2, $1}' | sed 's/, $//')
        total_skipped_ext=$(( total_skipped_ext + dir_skipped ))
        skipped_ext_summary="${skipped_ext_summary}${dir}: ${ext_counts}; "
    fi
}

_collect_single_file() {
    local file=$1
    local basename_f
    basename_f=$(basename "$file")
    local ext="${basename_f##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    if [[ "$ext" != "md" && "$ext" != "txt" ]]; then
        log_info "WARN  跳过非 .md/.txt 文件: $file"
        total_skipped_ext=$(( total_skipped_ext + 1 ))
        skipped_ext_summary="${skipped_ext_summary}${file}; "
        return
    fi

    if [[ ! -s "$file" ]]; then
        log_info "WARN  跳过空文件: $file"
        return
    fi

    _copy_with_dedup "$file" "$basename_f"
}

_copy_with_dedup() {
    local src_file=$1
    local target_name=$2
    local dest="${LEGACY_DOCS_DIR}/${target_name}"

    if [[ -f "$dest" ]]; then
        local base="${target_name%.*}"
        local ext_part="${target_name##*.}"
        local n=2
        while [[ -f "${LEGACY_DOCS_DIR}/${base}_${n}.${ext_part}" ]]; do
            n=$(( n + 1 ))
        done
        dest="${LEGACY_DOCS_DIR}/${base}_${n}.${ext_part}"
    fi

    cp -- "$src_file" "$dest"
    COLLECTED_COUNT=$(( COLLECTED_COUNT + 1 ))
}

_ensure_protocol() {
    [[ -f "$PROTOCOL_SOURCE" ]] || {
        log_error "协议源文件 ${PROTOCOL_SOURCE} 不存在，流水线拒绝启动"
        exit 1
    }

    if [[ ! -f "$PROTOCOL_TARGET" ]]; then
        mkdir -p "$(dirname "$PROTOCOL_TARGET")"
        cp -- "$PROTOCOL_SOURCE" "$PROTOCOL_TARGET"
        log_ok "自动复制协议到 ${PROTOCOL_TARGET}（alwaysApply: true）"
    elif ! diff -q "$PROTOCOL_SOURCE" "$PROTOCOL_TARGET" >/dev/null 2>&1; then
        log_info "WARN  ${PROTOCOL_TARGET} 已存在但与 ${PROTOCOL_SOURCE} 协议内容不一致，保留现有文件"
    fi

    local PROTOCOL_TARGET_GEMINI=".gemini/rules/collaboration-protocol.md"
    if [[ ! -f "$PROTOCOL_TARGET_GEMINI" ]]; then
        mkdir -p "$(dirname "$PROTOCOL_TARGET_GEMINI")"
        cat << 'FRONTMATTER_EOF' > "$PROTOCOL_TARGET_GEMINI"
---
description: 知识库流水线底层协作法典
globs: **/*
trigger: always_on
---
FRONTMATTER_EOF
        cat "$PROTOCOL_SOURCE" >> "$PROTOCOL_TARGET_GEMINI"
        log_ok "自动复制协议到 ${PROTOCOL_TARGET_GEMINI}（trigger: always_on）"
    elif ! tail -n +6 "$PROTOCOL_TARGET_GEMINI" | diff -q "$PROTOCOL_SOURCE" - >/dev/null 2>&1; then
        log_info "WARN  ${PROTOCOL_TARGET_GEMINI} 已存在但与 ${PROTOCOL_SOURCE} 协议内容不一致，保留现有文件"
    fi
}

_generate_no_docs_placeholder() {
    mkdir -p "$LEGACY_DOCS_DIR"
    SKIP_STEP0=true
    cat > "${OUTPUT_DIR}/Legacy_${PROJECT_NAME}_Claims.md" <<'PLACEHOLDER_EOF'
# Legacy Claims: {{project_name}}

> [!WARNING] 无旧文档
> {{legacy_docs_dir}} 目录不存在或为空，本步骤跳过声称提取。
> 后续步骤的先验知识注入层将留空，直接基于代码事实构建知识库。

---

> [!SUCCESS] 旧文档情报萃取闭环验证
> - LEGACY_STATUS: NO_DOCS
> - 扫描范围：{{legacy_docs_dir}} 下实际存在 [0] 个文件
> - 提取结果：识别了 [0] 条涉及 {{project_name}} 的声称（LEGACY_COUNT=0）
> - 待确认项：[0] 条标记为【待确认】的声称
> - EOF 状态：N/A
PLACEHOLDER_EOF
    sed -i '' "s|{{project_name}}|${PROJECT_NAME}|g; s|{{legacy_docs_dir}}|${LEGACY_DOCS_DIR}|g" \
        "${OUTPUT_DIR}/Legacy_${PROJECT_NAME}_Claims.md"
    log_ok "无旧文档（NO_DOCS），已生成 placeholder 文件，跳过 step-0"
}

# ─── 前置检查 ─────────────────────────────────────────────────────────────────

preflight() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$LOCAL_LOG_DIR"
    ln -sfn "$RUN_TIMESTAMP" "${LOCAL_LOG_DIR}/latest"

    log_info "前置检查开始"

    _ensure_protocol

    mkdir -p "$OUTPUT_DIR"

    if (( ${#LEGACY_SOURCES[@]} > 0 )); then
        # 用户指定了 legacy 路径 → 校验存在性 → 收集到 old-readme/
        for src in "${LEGACY_SOURCES[@]}"; do
            if [[ ! -e "$src" ]]; then
                log_error "指定的 legacy 路径不存在: $src"
                exit 1
            fi
        done
        collect_legacy_sources
        if (( COLLECTED_COUNT == 0 )); then
            _generate_no_docs_placeholder
        fi
    elif [[ ! -d "$LEGACY_DOCS_DIR" ]]; then
        # 未指定路径，old-readme/ 也不存在 → 交互式确认
        log_info "旧文档目录 ${LEGACY_DOCS_DIR} 不存在"
        echo ""
        echo "  [1] 没有旧文档，跳过（step-0 以 NO_DOCS 模式运行）"
        echo "  [2] 旧文档在别处，我先准备好再跑（退出）"
        echo ""
        read -r -p "请选择 [1/2]（默认 1）: " choice || true
        choice="${choice:-1}"
        case "$choice" in
            1)  _generate_no_docs_placeholder ;;
            2)
                log_info "请将旧文档放入 ${LEGACY_DOCS_DIR} 后重新运行"
                exit 0
                ;;
            *)
                log_error "无效选择: ${choice}"
                exit 1
                ;;
        esac
    fi

    command -v "$CURSOR_CMD" >/dev/null 2>&1 || {
        log_error "${CURSOR_CMD} CLI 不可用"
        exit 1
    }

    command -v jq >/dev/null 2>&1 || {
        log_error "jq 不可用，请先安装：brew install jq"
        exit 1
    }

    [[ -d "$PROMPT_DIR" ]] || {
        log_error "Prompt 模板目录 ${PROMPT_DIR} 不存在"
        exit 1
    }

    log_ok "前置检查通过（元协议 ✓ | 旧文档目录 ✓ | cursor ✓ | jq ✓ | 模板 ✓）"
}

# ─── 001 指挥官 AI ────────────────────────────────────────────────────────────

init_commander() {
    log_step "初始化 001 指挥官 AI..."

    COMMANDER_ID=$("$CURSOR_CMD" agent create-chat 2>/dev/null | grep -oE '[a-f0-9-]{36}')
    [[ -n "$COMMANDER_ID" ]] || {
        log_error "001 会话创建失败"
        exit 1
    }
    log_info "指挥官会话 ID: ${COMMANDER_ID}"

    cat <<'INIT_ROLE_EOF' > "${LOG_DIR}/commander-init-msg.tmp"
你是知识库考古流水线的指挥官 AI（001）。

## 你的身份

你是唯一持续运行的会话，负责串联整条流水线的上下文。
每一步的执行由独立的 Agent 完成（token 预算独立），你的职责是：
1. 根据前序步骤的实际发现，动态调整下一步的 prompt
2. 保证每步 prompt 的结构完整性（RCAC 8 层骨架）
3. 将适配后的 prompt **写入文件**供 bash 调度器读取
INIT_ROLE_EOF

    # 追加项目特定信息（不能放在单引号 heredoc 内）
    cat <<INIT_PROJECT_EOF >> "${LOG_DIR}/commander-init-msg.tmp"

## 项目信息

- 项目名称：${PROJECT_NAME}
- 项目显示名：${PROJECT_DISPLAY}
- 模板目录：${PROMPT_DIR}/
- 产出目录：${OUTPUT_DIR}/
- 旧文档目录：${LEGACY_DOCS_DIR}

## 工作协议

每次你收到一条消息，它会包含：
1. 上一步的执行结果摘要
2. 下一步应该基于哪个模板文件生成 prompt

你必须：
1. 使用 Read 工具读取指定的 .md 模板文件
2. 将模板中的变量替换为实际值：
   - {{project_name}} → ${PROJECT_NAME}
   - {{project_display_name}} → ${PROJECT_DISPLAY}
   - {{output_dir}} → ${OUTPUT_DIR}/
   - {{legacy_docs_dir}} → ${LEGACY_DOCS_DIR}
3. 根据前序步骤的实际发现，动态调整 prompt 中的「先验知识注入」和「任务」部分
   - 在先验知识注入中增加前序步骤的关键发现作为交叉验证线索
   - 在任务部分补充需要特别关注的问题（如前序步骤发现的异常）
4. 调整后的完整 prompt 必须使用 Write 工具写入文件 ${NEXT_PROMPT}
5. 严禁把 prompt 输出到对话中，${NEXT_PROMPT} 是 bash 读取的唯一通道
6. 除了模板变量替换和动态调整外，模板的其余结构（角色定义、最高指令挂载、约束条件、审计闭环）必须原样保留

## 关于 Step 08（模块深潜）

当收到模块深潜请求时，消息中会包含模块信息（module_id, module_name, module_suffix）。
除了上述标准变量替换，还需要：
- 将 {{module_name}} 替换为消息中指定的模块中文名
- 将 {{module_suffix}} 替换为消息中指定的后缀字母
- 将 {{module_core_classes}} 替换为从 ${OUTPUT_DIR}/05_Business_Orchestration.md 中提取的该模块核心类清单

请确认你已理解上述全部规则，回复「就绪」。
INIT_PROJECT_EOF

    cat "${LOG_DIR}/commander-init-msg.tmp" \
        | "$CURSOR_CMD" agent $CURSOR_AGENT_FLAGS --resume "$COMMANDER_ID" \
        2>&1 | tee "${LOG_DIR}/commander-init.log"

    rm -f "${LOG_DIR}/commander-init-msg.tmp"
    log_ok "001 指挥官初始化完成"
}

# 向 001 发送消息，等待 next-prompt.md 生成
ask_commander() {
    local message=$1
    local msg_file="${LOG_DIR}/commander-msg.tmp"

    log_info "请求 001 生成下一步 prompt..."

    rm -f "$NEXT_PROMPT"
    printf '%s' "$message" > "$msg_file"

    start_heartbeat "001 生成 prompt" "$COMMANDER_ID"

    cat "$msg_file" \
        | "$CURSOR_CMD" agent $CURSOR_AGENT_FLAGS --resume "$COMMANDER_ID" \
        2>&1 | tee -a "${LOG_DIR}/commander.log"

    rm -f "$msg_file"

    stop_heartbeat

    # --print 模式同步阻塞，轮询兜底防边缘情况
    local max_wait=1800
    local elapsed=0
    while [[ ! -f "$NEXT_PROMPT" ]] && (( elapsed < max_wait )); do
        sleep 3
        elapsed=$((elapsed + 3))
        if (( elapsed % 60 == 0 )); then
            log_info "等待 001 生成 prompt... (${elapsed}s)"
        fi
    done

    [[ -f "$NEXT_PROMPT" ]] || {
        log_error "001 未在 ${max_wait}s 内生成 prompt"
        exit 1
    }

    local prompt_lines
    prompt_lines=$(wc -l < "$NEXT_PROMPT" | tr -d ' ')
    log_ok "001 已生成 prompt（${prompt_lines} 行）"
}

# ─── 心跳监控（基于 transcript 文件实时追踪 Agent 进度） ─────────────────────

HEARTBEAT_PID=""

# 从 transcript JSONL 最后一行提取摘要（纯监控，允许失败）
_extract_transcript_hint() {
    local transcript_file=$1
    [[ -f "$transcript_file" ]] || return 0
    tail -1 "$transcript_file" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    role = d.get('role', '?')
    content = d.get('message', {}).get('content', [])
    for item in content:
        if item.get('type') == 'text':
            text = item['text'].strip().replace('\n', ' ')[:80]
            print(f'{role}: {text}')
            break
    else:
        for item in content:
            if item.get('type') == 'tool_use':
                name = item.get('name', '?')
                print(f'{role}: [tool] {name}')
                break
except:
    pass
" 2>/dev/null || true
}

start_heartbeat() {
    local label=$1
    local agent_id=$2
    local heartbeat_log=${3:-""}
    local start_ts=$(date +%s)
    local prev_lines=0
    local transcript_file="${TRANSCRIPT_BASE}/${agent_id}/${agent_id}.jsonl"

    (
        while true; do
            sleep 6
            local now=$(date +%s)
            local elapsed=$(( now - start_ts ))
            local min=$(( elapsed / 60 ))
            local sec=$(( elapsed % 60 ))

            local cur_lines=0
            local hint=""
            if [[ -f "$transcript_file" ]]; then
                cur_lines=$(wc -l < "$transcript_file" 2>/dev/null | tr -d ' ')
                hint=$(_extract_transcript_hint "$transcript_file")
            fi

            local status=""
            if [[ "$cur_lines" -gt "$prev_lines" ]]; then
                status="turn ${cur_lines}"
                prev_lines=$cur_lines
            elif [[ "$cur_lines" -gt 0 ]]; then
                status="thinking"
            else
                status="starting"
            fi

            if [[ -n "$heartbeat_log" && -n "$hint" && "$cur_lines" -gt 0 ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')]   ⏳ [${label}] ${min}m$(printf '%02d' $sec)s | ${status} | ${hint}" \
                    >> "$heartbeat_log" 2>/dev/null || true
            fi
        done
    ) &
    HEARTBEAT_PID=$!
}

stop_heartbeat() {
    if [[ -n "$HEARTBEAT_PID" ]] && kill -0 "$HEARTBEAT_PID" 2>/dev/null; then
        kill "$HEARTBEAT_PID" 2>/dev/null
        wait "$HEARTBEAT_PID" 2>/dev/null || true
        HEARTBEAT_PID=""
    fi
}

trap 'stop_heartbeat' EXIT

# ─── 执行引擎 ─────────────────────────────────────────────────────────────────

get_result_summary() {
    local step_name=$1
    local log_file="${LOG_DIR}/${step_name}.log"

    if [[ ! -f "$log_file" ]]; then
        echo "（日志文件不存在）"
        return
    fi

    # 优先提取 [!SUCCESS] 闭环验证块
    local success_block
    success_block=$(grep -A 25 '\[!SUCCESS\]' "$log_file" 2>/dev/null | head -30 || true)

    if [[ -n "$success_block" ]]; then
        echo "$success_block"
    else
        # 兜底：取日志最后 30 行
        tail -30 "$log_file" 2>/dev/null || echo "（无法提取结果摘要）"
    fi
}

run_step() {
    local step_name=$1
    local log_file="${LOG_DIR}/${step_name}.log"

    cp "$NEXT_PROMPT" "${OUTPUT_DIR}/${step_name}_prompt.md" 2>/dev/null || true

    log_step "执行 ${step_name}..."

    local executor_id
    executor_id=$("$CURSOR_CMD" agent create-chat 2>/dev/null | grep -oE '[a-f0-9-]{36}')
    [[ -n "$executor_id" ]] || {
        log_error "${step_name}: 执行 Agent 创建失败"
        exit 1
    }
    log_info "${step_name} Agent: ${executor_id}"
    echo "$executor_id" > "${LOG_DIR}/latest-agent-id"

    start_heartbeat "$step_name" "$executor_id" "${LOG_DIR}/${step_name}.heartbeat.log"

    cat "$NEXT_PROMPT" \
        | "$CURSOR_CMD" agent $CURSOR_AGENT_FLAGS --resume "$executor_id" \
        2>&1 | tee "$log_file"
    local exit_code=${PIPESTATUS[1]:-$?}

    stop_heartbeat

    if [[ $exit_code -ne 0 ]]; then
        log_error "${step_name}: Agent 执行失败（exit code: ${exit_code}）"
        log_error "详见日志: ${log_file}"
        exit 1
    fi

    local log_lines
    log_lines=$(wc -l < "$log_file" | tr -d ' ')
    log_ok "${step_name} 执行完成（日志 ${log_lines} 行）"
}

# ─── 主流程 ───────────────────────────────────────────────────────────────────

main() {
    PIPELINE_START_TIME=$(date +%s)
    mkdir -p "$LOG_DIR"

    log "═══════════════════════════════════════════════════════════════"
    log "  知识库考古流水线启动"
    log "  项目：${PROJECT_NAME}（${PROJECT_DISPLAY}）"
    log "  时间：$(timestamp)"
    log "═══════════════════════════════════════════════════════════════"

    preflight
    init_commander

    # ── Step 0~07: 串行主链 ──────────────────────────────────────────────────

    local start_index=0

    if [[ "$SKIP_STEP0" == true ]]; then
        log_info "无旧文档，step-0 已跳过（placeholder 已生成）"
        start_index=1
        ask_commander "流水线启动，前置检查全部通过。
step-0（旧文档声称提取）已跳过——无旧文档可用（LEGACY_STATUS: NO_DOCS, LEGACY_COUNT=0）。
placeholder 文件已生成至 ${OUTPUT_DIR}/Legacy_${PROJECT_NAME}_Claims.md。
请基于 ${PROMPT_DIR}/step-01-skeleton.md 模板生成执行 prompt，写入 ${NEXT_PROMPT}。
注意：后续所有步骤的先验知识注入层中，旧文档交叉验证一律标注为 N/A。"
    else
        ask_commander "流水线启动，前置检查全部通过。
请基于 ${PROMPT_DIR}/step-0-legacy.md 模板生成第一步的执行 prompt，写入 ${NEXT_PROMPT}。"
    fi

    local step_count=${#STEP_LIST[@]}

    for (( i=start_index; i<step_count; i++ )); do
        local step="${STEP_LIST[$i]}"
        log "── [$(( i + 1 ))/${step_count}] ${step} ──"

        run_step "$step"

        # 最后一步（step-07）的结果由模块循环阶段发送
        if (( i + 1 < step_count )); then
            local next_step="${STEP_LIST[$(( i + 1 ))]}"
            ask_commander "${step} 执行完毕。结果摘要：
$(get_result_summary "$step")

请基于 ${PROMPT_DIR}/${next_step}.md 模板生成下一步的执行 prompt，写入 ${NEXT_PROMPT}。"
        fi
    done

    # ── Step 08: 动态模块循环 ────────────────────────────────────────────────

    local manifest="${OUTPUT_DIR}/05_module_manifest.json"
    [[ -f "$manifest" ]] || {
        log_error "缺少模块清单 ${manifest}，Step 05 可能未正确产出"
        exit 1
    }

    jq empty "$manifest" 2>/dev/null || {
        log_error "模块清单 ${manifest} 不是合法 JSON"
        exit 1
    }

    local module_count
    module_count=$(jq length "$manifest")
    log_info "模块清单包含 ${module_count} 个模块，开始深潜循环"

    # 读取所有模块 ID 和名称到数组
    local module_ids=()
    local module_names=()
    while IFS= read -r line; do
        module_ids+=("$line")
    done < <(jq -r '.[].id' "$manifest")
    while IFS= read -r line; do
        module_names+=("$line")
    done < <(jq -r '.[].name' "$manifest")

    local last_main_chain_summary
    last_main_chain_summary=$(get_result_summary "step-07-config")

    for (( i=0; i<module_count; i++ )); do
        local mid="${module_ids[$i]}"
        local mname="${module_names[$i]}"
        local msuffix="${SUFFIXES[$i]}"

        log "── [Step 08 - $(( i + 1 ))/${module_count}] ${mid}（${mname}）──"

        if (( i == 0 )); then
            # 第一个模块：发送 step-07 的结果 + 请求生成模块 prompt
            ask_commander "step-07-config 执行完毕。结果摘要：
${last_main_chain_summary}

串行主链（Step 0~07）全部完成，进入模块深潜阶段（共 ${module_count} 个模块）。
请基于 ${PROMPT_DIR}/step-08-module-template.md 模板，为第一个模块生成专属执行 prompt。
模块信息：module_id=${mid}, module_name=${mname}, module_suffix=${msuffix}
写入 ${NEXT_PROMPT}。"
        else
            # 后续模块：发送上一个模块的结果 + 请求生成下一个模块的 prompt
            local prev_mid="${module_ids[$(( i - 1 ))]}"
            ask_commander "step-08-${prev_mid} 执行完毕。结果摘要：
$(get_result_summary "step-08-${prev_mid}")

模块 ${prev_mid} 完成（${i}/${module_count}）。
请基于 ${PROMPT_DIR}/step-08-module-template.md 模板，为下一个模块生成专属执行 prompt。
模块信息：module_id=${mid}, module_name=${mname}, module_suffix=${msuffix}
写入 ${NEXT_PROMPT}。"
        fi

        run_step "step-08-${mid}"
    done

    # ── Final Assembly ───────────────────────────────────────────────────────

    log "── Final Assembly ──"

    local last_mid="${module_ids[$(( module_count - 1 ))]}"
    ask_commander "step-08-${last_mid} 执行完毕。结果摘要：
$(get_result_summary "step-08-${last_mid}")

全部 ${module_count} 个模块深潜已完成。
请基于 ${PROMPT_DIR}/step-final-assembly.md 模板生成收官组装的执行 prompt，写入 ${NEXT_PROMPT}。"

    run_step "step-final-assembly"

    # ── Rules Audit ──────────────────────────────────────────────────────────

    log "── Rules Audit ──"

    ask_commander "step-final-assembly 执行完毕。结果摘要：
$(get_result_summary "step-final-assembly")

请基于 ${PROMPT_DIR}/step-audit-rules.md 模板生成 Rules 审计的执行 prompt，写入 ${NEXT_PROMPT}。"

    run_step "step-rules-audit"

    # ── 完成 ─────────────────────────────────────────────────────────────────

    local elapsed_total=$(( $(date +%s) - PIPELINE_START_TIME ))
    local elapsed_min=$(( elapsed_total / 60 ))
    local elapsed_sec=$(( elapsed_total % 60 ))

    log "═══════════════════════════════════════════════════════════════"
    log "  流水线执行完成"
    log "  耗时：${elapsed_min}m ${elapsed_sec}s"
    log "  产出目录：${OUTPUT_DIR}/"
    log "  日志目录：${LOG_DIR}/"
    log "  指挥官会话：${COMMANDER_ID}"
    log "═══════════════════════════════════════════════════════════════"
}

main
