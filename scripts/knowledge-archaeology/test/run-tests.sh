#!/bin/bash
set -uo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1: Mock 编排测试
#
# 每个测试场景映射一个需求（见方案文档 §1 和 §3.7）：
#   R1  — 步骤严格串行，顺序不可错
#   R2  — 每步结果回传 001，不能丢失
#   R3  — 模块循环遍历 manifest 中全部模块，不多不少
#   R4  — 模块后缀按 manifest 顺序递增 a/b/c...
#   R5  — 前置条件缺失：协议→拒绝启动；旧文档→交互选择；manifest→模块阶段失败
#   R6  — 单步失败时流水线熔断
#   R7  — 传入 legacy 路径 → 文件被复制到 old-readme/，跳过交互
#   R8  — 传入的 legacy 路径不存在时报错退出
#   R9  — 传入空目录（存在但无 .md/.txt）→ NO_DOCS 模式
#   R10 — 传入 0 字节文件 → 跳过并 WARN，汇总后 NO_DOCS
#   R11 — 多路径同名文件 → old-readme/ 中均存在且不互相覆盖
#   R12 — 扩展名过滤 → 仅 .md/.txt 被复制，非法扩展名汇总 WARN
#   R13 — 混合输入（目录+单文件）→ 均被收集到 old-readme/
#   R16 — 每步执行前 prompt 被归档到 OUTPUT_DIR
#   R17 — NO_DOCS 模式：placeholder 文件内容正确 + step-0 被跳过
#
# 用法：在项目根目录执行
#   bash scripts/knowledge-archaeology/test/run-tests.sh
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PIPELINE="$PROJECT_ROOT/scripts/knowledge-archaeology/run-archaeology.sh"
MOCK_CURSOR="$SCRIPT_DIR/mock-cursor.sh"
FIXTURES="$SCRIPT_DIR/fixtures"

PASS_COUNT=0
FAIL_COUNT=0

# ─── 测试基础设施 ─────────────────────────────────────────────────────────────

PROTOCOL_SOURCE_FILE="$PROJECT_ROOT/scripts/knowledge-archaeology/collaboration-protocol.md"

setup_sandbox() {
    local sandbox
    sandbox=$(mktemp -d)

    mkdir -p "$sandbox/.cursor/rules"
    mkdir -p "$sandbox/old-readme"
    mkdir -p "$sandbox/scripts/knowledge-archaeology/prompts"

    # 协议源文件（流水线自带）
    cp "$PROTOCOL_SOURCE_FILE" "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md" 2>/dev/null || \
        echo "mock protocol" > "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md"
    # 目标协议（与源一致，确保 preflight 不产生 WARN）
    cp "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md" \
       "$sandbox/.cursor/rules/collaboration-protocol.mdc"

    cp "$PROJECT_ROOT/scripts/knowledge-archaeology/prompts/"*.md \
       "$sandbox/scripts/knowledge-archaeology/prompts/" 2>/dev/null || true

    cp "$PIPELINE" "$sandbox/scripts/knowledge-archaeology/run-archaeology.sh"
    chmod +x "$sandbox/scripts/knowledge-archaeology/run-archaeology.sh"

    echo "$sandbox"
}

# 无 old-readme 的 sandbox（用于 legacy 路径测试）
setup_sandbox_no_old_readme() {
    local sandbox
    sandbox=$(mktemp -d)

    mkdir -p "$sandbox/.cursor/rules"
    mkdir -p "$sandbox/scripts/knowledge-archaeology/prompts"

    cp "$PROTOCOL_SOURCE_FILE" "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md" 2>/dev/null || \
        echo "mock protocol" > "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md"
    cp "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md" \
       "$sandbox/.cursor/rules/collaboration-protocol.mdc"

    cp "$PROJECT_ROOT/scripts/knowledge-archaeology/prompts/"*.md \
       "$sandbox/scripts/knowledge-archaeology/prompts/" 2>/dev/null || true

    cp "$PIPELINE" "$sandbox/scripts/knowledge-archaeology/run-archaeology.sh"
    chmod +x "$sandbox/scripts/knowledge-archaeology/run-archaeology.sh"

    echo "$sandbox"
}

teardown_sandbox() {
    rm -rf "$1"
}

# 在 sandbox 中运行流水线（子 shell 中执行，不污染当前环境）
# 参数：sandbox, manifest_fixture, [legacy_path1] [legacy_path2] ...
# 返回值 = 流水线 exit code；stdout = 流水线输出
run_pipeline() {
    local sandbox=$1
    local manifest_fixture=${2:-""}
    shift 2 2>/dev/null || true
    local legacy_args=("$@")

    (
        export CURSOR_CMD="$MOCK_CURSOR"
        export MOCK_STATE_DIR="${sandbox}/.mock-state"
        export MOCK_NEXT_PROMPT="${sandbox}/scripts/knowledge-archaeology/next-prompt.md"

        if [[ -n "$manifest_fixture" ]]; then
            local output_dir="$sandbox/docs/ai-knowledge/$(basename "$sandbox")"
            mkdir -p "$output_dir"
            cp "$manifest_fixture" "$output_dir/05_module_manifest.json"
        fi

        cd "$sandbox"
        if (( ${#legacy_args[@]} > 0 )); then
            bash scripts/knowledge-archaeology/run-archaeology.sh "测试项目" "${legacy_args[@]}" 2>&1
        else
            bash scripts/knowledge-archaeology/run-archaeology.sh "测试项目" 2>&1
        fi
    )
}

get_call_log() {
    cat "$1/.mock-state/call-log.txt" 2>/dev/null || echo ""
}

# ─── 断言工具 ─────────────────────────────────────────────────────────────────

assert_contains() {
    local desc=$1 haystack=$2 needle=$3
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc"
        echo "    expected to contain: $needle"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_line_order() {
    local desc=$1 log=$2 first=$3 second=$4
    local pos_first pos_second
    pos_first=$(echo "$log" | grep -nF "$first" | head -1 | cut -d: -f1)
    pos_second=$(echo "$log" | grep -nF "$second" | head -1 | cut -d: -f1)

    if [[ -z "$pos_first" || -z "$pos_second" ]]; then
        echo "  FAIL: $desc (pattern not found)"
        [[ -z "$pos_first" ]] && echo "    missing: $first"
        [[ -z "$pos_second" ]] && echo "    missing: $second"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    elif (( pos_first < pos_second )); then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (wrong order: L${pos_first} vs L${pos_second})"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_count() {
    local desc=$1 log=$2 pattern=$3 expected=$4
    local actual
    actual=$(echo "$log" | grep -cF "$pattern" || true)
    if (( actual == expected )); then
        echo "  PASS: $desc (count=${actual})"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (expected ${expected}, got ${actual})"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_exit_nonzero() {
    local desc=$1 exit_code=$2
    if (( exit_code != 0 )); then
        echo "  PASS: $desc (exit=${exit_code})"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (expected nonzero, got 0)"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_exit_zero() {
    local desc=$1 exit_code=$2
    if (( exit_code == 0 )); then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (expected 0, got ${exit_code})"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_file_exists() {
    local desc=$1 filepath=$2
    if [[ -f "$filepath" ]]; then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (file not found: $filepath)"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_file_not_exists() {
    local desc=$1 filepath=$2
    if [[ ! -f "$filepath" ]]; then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (file should not exist: $filepath)"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_file_count() {
    local desc=$1 dir=$2 expected=$3
    local actual=0
    if [[ -d "$dir" ]]; then
        actual=$(find "$dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
    fi
    if (( actual == expected )); then
        echo "  PASS: $desc (count=${actual})"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (expected ${expected} files, got ${actual})"
        if [[ -d "$dir" ]]; then
            echo "    actual files: $(ls -1 "$dir" 2>/dev/null | tr '\n' ' ')"
        fi
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

assert_file_content_contains() {
    local desc=$1 filepath=$2 needle=$3
    if [[ -f "$filepath" ]] && grep -qF "$needle" "$filepath"; then
        echo "  PASS: $desc"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: $desc (content not found in $filepath)"
        echo "    expected to contain: $needle"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
}

# ─── 测试场景 ─────────────────────────────────────────────────────────────────

test_R1_step_order() {
    echo ""
    echo "=== R1: 步骤严格串行，顺序不可错 ==="

    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null
    local log
    log=$(get_call_log "$sandbox")

    assert_line_order "001 init 先于所有 executor" "$log" \
        "COMMANDER_INIT" "EXECUTOR_RUN"

    assert_line_order "step-0 先于 step-01" "$log" \
        "template=step-0-legacy.md" "template=step-01-skeleton.md"

    assert_line_order "step-01 先于 step-02" "$log" \
        "template=step-01-skeleton.md" "template=step-02-contracts.md"

    assert_line_order "step-02 先于 step-03" "$log" \
        "template=step-02-contracts.md" "template=step-03-downstream.md"

    assert_line_order "step-03 先于 step-04" "$log" \
        "template=step-03-downstream.md" "template=step-04-data-model.md"

    assert_line_order "step-04 先于 step-05" "$log" \
        "template=step-04-data-model.md" "template=step-05-orchestration.md"

    assert_line_order "step-05 先于 step-06" "$log" \
        "template=step-05-orchestration.md" "template=step-06-async.md"

    assert_line_order "step-06 先于 step-07" "$log" \
        "template=step-06-async.md" "template=step-07-config.md"

    assert_line_order "step-07 先于 step-08 模块深潜" "$log" \
        "template=step-07-config.md" "template=step-08-module-template.md"

    assert_line_order "step-08 先于 final assembly" "$log" \
        "template=step-08-module-template.md" "template=step-final-assembly.md"

    assert_line_order "final 先于 audit" "$log" \
        "template=step-final-assembly.md" "template=step-audit-rules.md"

    teardown_sandbox "$sandbox"
}

test_R2_results_forwarded() {
    echo ""
    echo "=== R2: 每步结果回传 001 ==="

    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null
    local log
    log=$(get_call_log "$sandbox")

    # 001 应收到: 初始请求(1) + step-0~06 结果(7) + step-07 结果(1,在模块阶段) + 模块结果(1) + final 请求(1) + audit 请求(1) = 12
    assert_count "001 收到正确次数的 prompt 请求" "$log" "COMMANDER_ASK" 12

    # 每个 executor 执行对应一个 EXECUTOR_RUN
    # 8(主链) + 2(模块) + 1(final) + 1(audit) = 12
    assert_count "executor 总执行次数正确" "$log" "EXECUTOR_RUN" 12

    teardown_sandbox "$sandbox"
}

test_R3_module_iteration() {
    echo ""
    echo "=== R3: 模块循环遍历全部模块 ==="

    # --- 1 module ---
    echo "  [1 module]"
    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-1-module.json" > /dev/null
    local log
    log=$(get_call_log "$sandbox")
    assert_contains "solo 模块被执行" "$log" "module_id=solo"
    assert_count "总 executor 次数 = 8+1+1+1 = 11" "$log" "EXECUTOR_RUN" 11
    teardown_sandbox "$sandbox"

    # --- 2 modules ---
    echo "  [2 modules]"
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null
    log=$(get_call_log "$sandbox")
    assert_contains "alpha 被执行" "$log" "module_id=alpha"
    assert_contains "beta 被执行" "$log" "module_id=beta"
    assert_count "总 executor 次数 = 8+2+1+1 = 12" "$log" "EXECUTOR_RUN" 12
    teardown_sandbox "$sandbox"

    # --- 3 modules ---
    echo "  [3 modules]"
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-3-modules.json" > /dev/null
    log=$(get_call_log "$sandbox")
    assert_contains "signin 被执行" "$log" "module_id=signin"
    assert_contains "multiple-order 被执行" "$log" "module_id=multiple-order"
    assert_contains "channel-exchange 被执行" "$log" "module_id=channel-exchange"
    assert_count "总 executor 次数 = 8+3+1+1 = 13" "$log" "EXECUTOR_RUN" 13
    teardown_sandbox "$sandbox"
}

test_R4_module_suffix() {
    echo ""
    echo "=== R4: 模块后缀按 manifest 顺序递增 ==="

    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-3-modules.json" > /dev/null
    local log
    log=$(get_call_log "$sandbox")

    assert_contains "signin → a" "$log" "module_id=signin, module_name=签到模块, module_suffix=a"
    assert_contains "multiple-order → b" "$log" "module_id=multiple-order, module_name=多单任务模块, module_suffix=b"
    assert_contains "channel-exchange → c" "$log" "module_id=channel-exchange, module_name=渠道兑换模块, module_suffix=c"

    # 顺序也要对：a 先于 b 先于 c
    assert_line_order "suffix=a 先于 suffix=b" "$log" "module_suffix=a" "module_suffix=b"
    assert_line_order "suffix=b 先于 suffix=c" "$log" "module_suffix=b" "module_suffix=c"

    teardown_sandbox "$sandbox"
}

test_R5_missing_prerequisites() {
    echo ""
    echo "=== R5: 前置条件缺失 ==="

    # --- R5a: 缺少协议源文件 → preflight 拒绝启动 ---
    local sandbox
    sandbox=$(setup_sandbox)
    rm -f "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md"
    rm -f "$sandbox/.cursor/rules/collaboration-protocol.mdc"
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null 2>&1
    assert_exit_nonzero "R5a: 缺少协议源文件时拒绝启动" $?
    teardown_sandbox "$sandbox"

    # --- R5b: 无旧文档目录 + 用户选 2（退出准备）→ exit 0 ---
    sandbox=$(setup_sandbox)
    rm -rf "$sandbox/old-readme"
    echo "2" | run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null 2>&1
    assert_exit_zero "R5b: 无旧文档 + 用户选 2 → 正常退出" $?
    teardown_sandbox "$sandbox"

    # --- R5c: 无旧文档目录 + 用户选 1（默认 NO_DOCS）→ 流水线继续 ---
    sandbox=$(setup_sandbox)
    rm -rf "$sandbox/old-readme"
    echo "1" | run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null 2>&1
    assert_exit_zero "R5c: 无旧文档 + 用户选 1 → NO_DOCS 模式，流水线完成" $?
    teardown_sandbox "$sandbox"

    # --- R5d: 无旧文档目录 + stdin EOF（默认选 1）→ NO_DOCS 模式，流水线继续 ---
    sandbox=$(setup_sandbox)
    rm -rf "$sandbox/old-readme"
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" < /dev/null > /dev/null 2>&1
    assert_exit_zero "R5d: 无旧文档 + EOF → 默认 NO_DOCS 模式，流水线完成" $?
    teardown_sandbox "$sandbox"

    # --- R5e: 缺少 manifest → 模块循环阶段失败（主链已完成） ---
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "" > /dev/null 2>&1
    assert_exit_nonzero "R5e: 缺少 manifest 时模块阶段失败" $?
    teardown_sandbox "$sandbox"

    # --- R5f: 非法 JSON manifest → 模块循环阶段失败 ---
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-invalid.json" > /dev/null 2>&1
    assert_exit_nonzero "R5f: 非法 JSON manifest 时模块阶段失败" $?
    teardown_sandbox "$sandbox"
}

test_R6_executor_failure() {
    echo ""
    echo "=== R6: 单步失败时流水线熔断 ==="

    local sandbox
    sandbox=$(setup_sandbox)

    # 创建一个在第 2 次 executor 调用时失败的 mock
    # UUID 必须只包含 hex 字符（0-9a-f），否则 pipeline 的 grep 匹配不到
    local fail_mock="$sandbox/fail-cursor.sh"
    cat > "$fail_mock" <<'FAILEOF'
#!/bin/bash
set -uo pipefail
STATE="${MOCK_STATE_DIR:-.mock-state}"
PROMPT="${MOCK_NEXT_PROMPT:-next-prompt.md}"
mkdir -p "$STATE"

subcmd="${1:-}"; shift || true
case "$subcmd" in
    agent)
        action="${1:-}"
        if [[ "$action" == "create-chat" ]]; then
            c=$(cat "$STATE/counter" 2>/dev/null || echo 0)
            echo $(( c + 1 )) > "$STATE/counter"
            printf "00000000-0000-0000-dead-%012d" "$c"
            exit 0
        fi
        chat_id=""
        for a in "$@"; do [[ "${p:-}" == "--resume" ]] && chat_id="$a"; p="$a"; done
        stdin=$(cat)
        commander=$(cat "$STATE/commander-id" 2>/dev/null || echo "")
        if echo "$stdin" | grep -q "指挥官 AI"; then
            echo "$chat_id" > "$STATE/commander-id"
            echo "就绪"
            exit 0
        fi
        if [[ "$chat_id" == "$commander" ]]; then
            echo "# mock" > "$PROMPT"
            exit 0
        fi
        ec=$(cat "$STATE/exec-count" 2>/dev/null || echo 0)
        ec=$(( ec + 1 ))
        echo "$ec" > "$STATE/exec-count"
        if (( ec >= 2 )); then
            echo "SIMULATED FAILURE" >&2
            exit 1
        fi
        echo "> [!SUCCESS] mock pass"
        ;;
esac
FAILEOF
    chmod +x "$fail_mock"

    (
        export CURSOR_CMD="$fail_mock"
        export MOCK_STATE_DIR="${sandbox}/.mock-state"
        export MOCK_NEXT_PROMPT="${sandbox}/scripts/knowledge-archaeology/next-prompt.md"

        local output_dir="$sandbox/docs/ai-knowledge/$(basename "$sandbox")"
        mkdir -p "$output_dir"
        cp "$FIXTURES/manifest-2-modules.json" "$output_dir/05_module_manifest.json"

        cd "$sandbox"
        bash scripts/knowledge-archaeology/run-archaeology.sh "测试项目" 2>&1
    ) > /dev/null 2>&1
    assert_exit_nonzero "executor 失败后流水线停止" $?

    local exec_count
    exec_count=$(cat "$sandbox/.mock-state/exec-count" 2>/dev/null || echo "0")

    # 应该执行了至少 1 个 executor（第 1 次成功），但少于 8 个（第 2 次就失败了）
    if (( exec_count >= 1 && exec_count < 8 )); then
        echo "  PASS: 执行了 ${exec_count} 个 executor 后熔断（第 2 次失败触发）"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: exec_count=${exec_count}（预期 1~7，即第 2 次失败时停止）"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    teardown_sandbox "$sandbox"
}

test_happy_path_exit_code() {
    echo ""
    echo "=== 完整 happy path 退出码 ==="

    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null
    assert_exit_zero "完整流水线正常退出" $?
    teardown_sandbox "$sandbox"
}

test_R7_legacy_copied_to_old_readme() {
    echo ""
    echo "=== R7: 传入 legacy 路径 → 文件复制到 old-readme/ ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/docs/legacy"
    echo "# design doc" > "$sandbox/docs/legacy/design.md"
    echo "notes here" > "$sandbox/docs/legacy/notes.txt"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "docs/legacy" 2>&1) || true

    # 核心断言：文件被复制到 old-readme/
    assert_file_count "old-readme/ 中有 2 个文件" "$sandbox/old-readme" 2

    # old-readme/ 中的文件内容正确
    local found_design=false found_notes=false
    for f in "$sandbox/old-readme/"*; do
        [[ -f "$f" ]] || continue
        if grep -qF "# design doc" "$f" 2>/dev/null; then found_design=true; fi
        if grep -qF "notes here" "$f" 2>/dev/null; then found_notes=true; fi
    done
    if $found_design; then
        echo "  PASS: design.md 内容已复制"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: design.md 内容未找到"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
    if $found_notes; then
        echo "  PASS: notes.txt 内容已复制"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: notes.txt 内容未找到"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    # 不应触发交互（输出中不含"请选择"）
    if echo "$out" | grep -qF "请选择"; then
        echo "  FAIL: 不应触发交互式选择"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    else
        echo "  PASS: 跳过了交互式选择"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    fi

    teardown_sandbox "$sandbox"
}

test_R8_legacy_path_not_exist() {
    echo ""
    echo "=== R8: 传入的 legacy 路径不存在时报错退出 ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)

    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "nonexistent/path" > /dev/null 2>&1
    assert_exit_nonzero "路径不存在时拒绝启动" $?

    teardown_sandbox "$sandbox"
}

test_R9_empty_dir_no_docs() {
    echo ""
    echo "=== R9: 空目录 → NO_DOCS 模式 ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/empty-legacy"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "empty-legacy" 2>&1) || true

    assert_contains "输出含 NO_DOCS 标识" "$out" "NO_DOCS"
    assert_contains "输出含跳过 step-0 提示" "$out" "跳过"

    # old-readme/ 应被创建但为空
    assert_file_count "old-readme/ 中 0 个文件" "$sandbox/old-readme" 0

    teardown_sandbox "$sandbox"
}

test_R10_empty_file_warn() {
    echo ""
    echo "=== R10: 0 字节文件 → 跳过并 WARN ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/docs"
    touch "$sandbox/docs/empty.md"  # 0 字节

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "docs/empty.md" 2>&1) || true

    assert_contains "日志含 WARN（空文件）" "$out" "WARN"
    # 0 字节文件不应被复制
    assert_file_count "old-readme/ 中 0 个文件" "$sandbox/old-readme" 0
    # 汇总后有效文件=0 → NO_DOCS
    assert_contains "进入 NO_DOCS 模式" "$out" "NO_DOCS"

    teardown_sandbox "$sandbox"
}

test_R11_name_conflict() {
    echo ""
    echo "=== R11: 多路径同名文件 → 不互相覆盖 ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/dir-a" "$sandbox/dir-b"
    echo "content from A" > "$sandbox/dir-a/foo.md"
    echo "content from B" > "$sandbox/dir-b/foo.md"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "dir-a" "dir-b" 2>&1) || true

    # old-readme/ 中应有 2 个文件（不是 1 个被覆盖）
    assert_file_count "old-readme/ 中有 2 个文件（未被覆盖）" "$sandbox/old-readme" 2

    # 两份内容都应存在
    local found_a=false found_b=false
    for f in "$sandbox/old-readme/"*; do
        [[ -f "$f" ]] || continue
        if grep -qF "content from A" "$f" 2>/dev/null; then found_a=true; fi
        if grep -qF "content from B" "$f" 2>/dev/null; then found_b=true; fi
    done
    if $found_a; then
        echo "  PASS: dir-a/foo.md 内容保留"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: dir-a/foo.md 内容丢失"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
    if $found_b; then
        echo "  PASS: dir-b/foo.md 内容保留"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: dir-b/foo.md 内容丢失"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    teardown_sandbox "$sandbox"
}

test_R12_extension_filter() {
    echo ""
    echo "=== R12: 扩展名过滤 → 仅 .md/.txt，非法扩展名汇总 WARN ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/mixed"
    echo "# valid markdown" > "$sandbox/mixed/readme.md"
    echo "valid text" > "$sandbox/mixed/notes.txt"
    echo "public class Foo {}" > "$sandbox/mixed/Foo.java"
    echo "<xml/>" > "$sandbox/mixed/config.xml"
    echo "prop=val" > "$sandbox/mixed/app.properties"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "mixed" 2>&1) || true

    # old-readme/ 只有 .md 和 .txt
    assert_file_count "old-readme/ 中只有 2 个文件" "$sandbox/old-readme" 2

    # 日志中含跳过非法扩展名的 WARN
    assert_contains "日志含非法扩展名 WARN" "$out" "WARN"

    # .java/.xml/.properties 不应出现在 old-readme/
    local has_illegal=false
    for f in "$sandbox/old-readme/"*; do
        [[ -f "$f" ]] || continue
        case "$f" in
            *.java|*.xml|*.properties) has_illegal=true ;;
        esac
        if grep -qF "public class Foo" "$f" 2>/dev/null; then has_illegal=true; fi
    done
    if ! $has_illegal; then
        echo "  PASS: 非 .md/.txt 文件未被复制"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: 非 .md/.txt 文件被错误复制到 old-readme/"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    teardown_sandbox "$sandbox"
}

test_R13_mixed_input() {
    echo ""
    echo "=== R13: 混合输入（目录+单文件）→ 均被收集 ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/docs/legacy"
    echo "# from dir" > "$sandbox/docs/legacy/guide.md"
    echo "# standalone file" > "$sandbox/CHANGELOG.md"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "docs/legacy" "CHANGELOG.md" 2>&1) || true

    # old-readme/ 中有 2 个文件（1 个来自目录，1 个来自单文件）
    assert_file_count "old-readme/ 中有 2 个文件" "$sandbox/old-readme" 2

    local found_dir=false found_file=false
    for f in "$sandbox/old-readme/"*; do
        [[ -f "$f" ]] || continue
        if grep -qF "# from dir" "$f" 2>/dev/null; then found_dir=true; fi
        if grep -qF "# standalone file" "$f" 2>/dev/null; then found_file=true; fi
    done
    if $found_dir; then
        echo "  PASS: 目录中的文件已收集"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: 目录中的文件未收集"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
    if $found_file; then
        echo "  PASS: 单文件已收集"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: 单文件未收集"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    teardown_sandbox "$sandbox"
}

test_R14_protocol_auto_copy() {
    echo ""
    echo "=== R14: 协议文件自动复制到 .cursor/rules/ ==="

    # R14a: 目标不存在 → 自动复制
    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/old-readme"
    # 删除目标，只留源
    rm -f "$sandbox/.cursor/rules/collaboration-protocol.mdc"

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    assert_file_exists "R14a: 协议被自动复制" \
        "$sandbox/.cursor/rules/collaboration-protocol.mdc"
    # 内容应与源一致
    if [[ -f "$sandbox/.cursor/rules/collaboration-protocol.mdc" ]] && \
       diff -q "$sandbox/scripts/knowledge-archaeology/collaboration-protocol.md" \
               "$sandbox/.cursor/rules/collaboration-protocol.mdc" >/dev/null 2>&1; then
        echo "  PASS: R14a: 内容与源文件一致"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R14a: 内容与源文件不一致"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
    assert_contains "R14a: 日志记录了自动复制" "$out" "自动复制"
    teardown_sandbox "$sandbox"

    # R14b: 目标已存在且内容相同 → 静默通过，无 WARN
    sandbox=$(setup_sandbox)
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    if echo "$out" | grep -qF "协议内容不一致"; then
        echo "  FAIL: R14b: 内容相同时不应 WARN"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    else
        echo "  PASS: R14b: 内容相同时无 WARN"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    fi
    teardown_sandbox "$sandbox"

    # R14c: 目标已存在但内容不同 → WARN，不覆盖
    sandbox=$(setup_sandbox)
    echo "modified content" > "$sandbox/.cursor/rules/collaboration-protocol.mdc"
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    assert_contains "R14c: 内容不同时输出 WARN" "$out" "WARN"
    # 原内容不应被覆盖
    assert_file_content_contains "R14c: 原内容未被覆盖" \
        "$sandbox/.cursor/rules/collaboration-protocol.mdc" "modified content"
    teardown_sandbox "$sandbox"

    # R14d: 验证 Antigravity (.gemini) 协议文件是否自动复制并注入 Frontmatter
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/old-readme"
    rm -rf "$sandbox/.gemini"

    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    assert_file_exists "R14d: Antigravity 协议被自动复制" \
        "$sandbox/.gemini/rules/collaboration-protocol.md"
    
    if head -n 5 "$sandbox/.gemini/rules/collaboration-protocol.md" 2>/dev/null | grep -q "trigger: always_on"; then
        echo "  PASS: R14d: Antigravity 协议包含正确的 trigger: always_on"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R14d: Antigravity 协议缺少 trigger: always_on"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi
    teardown_sandbox "$sandbox"

    # R14e: 验证目标已存在但内容不同时，不覆盖 Antigravity 协议并输出 WARN
    sandbox=$(setup_sandbox)
    mkdir -p "$sandbox/.gemini/rules"
    echo "modified gemini content" > "$sandbox/.gemini/rules/collaboration-protocol.md"
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    assert_contains "R14e: Antigravity 协议内容不同时输出 WARN" "$out" "WARN"
    assert_file_content_contains "R14e: Antigravity 原协议未被覆盖" \
        "$sandbox/.gemini/rules/collaboration-protocol.md" "modified gemini content"
    teardown_sandbox "$sandbox"
}

test_R15_log_timestamp_dir() {
    echo ""
    echo "=== R15: 日志时间戳子目录 + latest 软链 ==="

    local sandbox
    sandbox=$(setup_sandbox)

    local out
    out=$(run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" 2>&1) || true

    local logs_base="$sandbox/scripts/knowledge-archaeology/logs"

    # R15a: latest 软链存在
    if [[ -L "$logs_base/latest" ]]; then
        echo "  PASS: R15a: latest 软链存在"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R15a: latest 软链不存在"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    # R15b: latest 指向的目录名含日期格式（YYYY-MM-DD_HHMMSS）
    local target
    target=$(readlink "$logs_base/latest" 2>/dev/null || echo "")
    if [[ "$target" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}$ ]]; then
        echo "  PASS: R15b: 目录名格式正确 ($target)"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R15b: 目录名格式不匹配 (got: $target)"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    # R15c: pipeline.log 在时间戳目录内
    assert_file_exists "R15c: pipeline.log 在时间戳目录内" \
        "$logs_base/$target/pipeline.log"

    teardown_sandbox "$sandbox"
}

test_R16_prompt_archived() {
    echo ""
    echo "=== R16: 每步执行前 prompt 被归档到 OUTPUT_DIR ==="

    local sandbox
    sandbox=$(setup_sandbox)
    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" > /dev/null

    local output_dir="$sandbox/docs/ai-knowledge/$(basename "$sandbox")"

    assert_file_exists "step-0-legacy prompt 归档" "$output_dir/step-0-legacy_prompt.md"
    assert_file_exists "step-01-skeleton prompt 归档" "$output_dir/step-01-skeleton_prompt.md"
    assert_file_exists "step-02-contracts prompt 归档" "$output_dir/step-02-contracts_prompt.md"
    assert_file_exists "step-03-downstream prompt 归档" "$output_dir/step-03-downstream_prompt.md"
    assert_file_exists "step-04-data-model prompt 归档" "$output_dir/step-04-data-model_prompt.md"
    assert_file_exists "step-05-orchestration prompt 归档" "$output_dir/step-05-orchestration_prompt.md"
    assert_file_exists "step-06-async prompt 归档" "$output_dir/step-06-async_prompt.md"
    assert_file_exists "step-07-config prompt 归档" "$output_dir/step-07-config_prompt.md"
    assert_file_exists "step-08-alpha prompt 归档" "$output_dir/step-08-alpha_prompt.md"
    assert_file_exists "step-08-beta prompt 归档" "$output_dir/step-08-beta_prompt.md"
    assert_file_exists "step-final-assembly prompt 归档" "$output_dir/step-final-assembly_prompt.md"
    assert_file_exists "step-rules-audit prompt 归档" "$output_dir/step-rules-audit_prompt.md"

    teardown_sandbox "$sandbox"
}

test_R17_no_docs_comprehensive() {
    echo ""
    echo "=== R17: NO_DOCS 模式：placeholder 文件 + step-0 跳过 ==="

    local sandbox
    sandbox=$(setup_sandbox_no_old_readme)
    mkdir -p "$sandbox/empty-legacy"

    run_pipeline "$sandbox" "$FIXTURES/manifest-2-modules.json" "empty-legacy" > /dev/null

    local log
    log=$(get_call_log "$sandbox")
    local project_name
    project_name=$(basename "$sandbox")
    local output_dir="$sandbox/docs/ai-knowledge/${project_name}"
    local placeholder="${output_dir}/Legacy_${project_name}_Claims.md"

    # R17a: placeholder 文件存在
    assert_file_exists "R17a: placeholder 文件存在" "$placeholder"

    # R17b: placeholder 内容含 LEGACY_STATUS: NO_DOCS
    assert_file_content_contains "R17b: LEGACY_STATUS=NO_DOCS" "$placeholder" "LEGACY_STATUS: NO_DOCS"

    # R17c: placeholder 变量已替换（不应残留 {{project_name}}）
    if [[ -f "$placeholder" ]] && ! grep -qF '{{project_name}}' "$placeholder"; then
        echo "  PASS: R17c: 变量已替换（无 {{project_name}} 残留）"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R17c: 变量未替换（{{project_name}} 残留）"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    # R17d: step-0 未执行 — call log 中无 step-0-legacy 模板引用
    if ! echo "$log" | grep -qF "template=step-0-legacy.md"; then
        echo "  PASS: R17d: step-0 未执行（call log 中无 step-0-legacy 模板）"
        PASS_COUNT=$(( PASS_COUNT + 1 ))
    else
        echo "  FAIL: R17d: step-0 不应执行（call log 中出现了 step-0-legacy 模板）"
        FAIL_COUNT=$(( FAIL_COUNT + 1 ))
    fi

    # R17e: executor 总数 = 7(step-01~07) + 2(模块) + 1(final) + 1(audit) = 11
    assert_count "R17e: executor 总数 = 11（跳过 step-0）" "$log" "EXECUTOR_RUN" 11

    teardown_sandbox "$sandbox"
}

# ─── 运行所有测试 ─────────────────────────────────────────────────────────────

main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Layer 1: Mock 编排测试"
    echo "═══════════════════════════════════════════════════════════════"

    test_happy_path_exit_code
    test_R1_step_order
    test_R2_results_forwarded
    test_R3_module_iteration
    test_R4_module_suffix
    test_R5_missing_prerequisites
    test_R6_executor_failure
    test_R7_legacy_copied_to_old_readme
    test_R8_legacy_path_not_exist
    test_R9_empty_dir_no_docs
    test_R10_empty_file_warn
    test_R11_name_conflict
    test_R12_extension_filter
    test_R13_mixed_input
    test_R14_protocol_auto_copy
    test_R15_log_timestamp_dir
    test_R16_prompt_archived
    test_R17_no_docs_comprehensive

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    if (( FAIL_COUNT == 0 )); then
        echo "  ALL PASSED: ${PASS_COUNT} assertions"
    else
        echo "  RESULT: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
    fi
    echo "═══════════════════════════════════════════════════════════════"

    (( FAIL_COUNT == 0 ))
}

main
