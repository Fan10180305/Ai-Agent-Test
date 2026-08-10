# 06 异步机制与补偿全量测绘 (Async Jobs and Compensation)

本模块描述了 `ai-knowledge` 流水线的异步执行架构、心跳监控机制以及在 NON_JAVA 环境下的失败补偿策略。

## 1. 异步/后台任务全量清单 (Async Jobs)

项目中唯一的持续异步逻辑是基于 Shell 子进程的心跳监控机制，用于实时追踪执行 Agent 的进度。

| 任务名称 | 触发方式 | 执行逻辑摘要 | 物理锚点 | 风险标注 |
| :--- | :--- | :--- | :--- | :--- |
| **Heartbeat Monitor** | `run_step()` 调用 `start_heartbeat()` | 孵化后台 subshell (`(...) &`)，每 6s 循环一次。 | `run-archaeology.sh:L479` | **僵尸进程风险**：若 `kill` 失败，子进程可能残留。 |
| **Transcript Hint Parser** | 心跳循环调用 `_extract_transcript_hint()` | 调用 `python3 -c` 解析 `tail -1` 得到的 JSONL 轨迹。 | `run-archaeology.sh:L454` | **静默失败**：若 `python3` 缺失，进度摘要将为空。 |
| **Commander Polling** | `ask_commander()` | 阻塞式 `while` 循环，每 3s 检查一次 `${NEXT_PROMPT}`。 | `run-archaeology.sh:L431` | **超时风险**：硬编码 30min 超时，超时则脚本熔断。 |

## 2. 进程通信与状态同步 (Inter-process Communication)

流水线采用**无锁、基于文件系统的信号传递**模式。

| 通信媒介 | 数据格式 | 流向 | 核心用途 |
| :--- | :--- | :--- | :--- |
| **Next-Prompt File** | Markdown | Commander → Executor Agent | 跨进程传递分析指令（认知接力）。 |
| **Agent Transcript** | JSONL | Cursor Agent → Heartbeat | 暴露实时 Turn 数及 AI 思考摘要（Hint）。 |
| **Success Block** | Markdown | Executor Agent → Commander | 包含 `[!SUCCESS]` 的审计块，作为状态闭环证据。 |
| **Latest Agent ID** | Plain Text | `run_step()` → `.logs/latest-agent-id` | 供外部工具（如 `cursor resume`）快速定位。 |

## 3. 补偿与重试机制深度解析 (Retry & Compensation)

本项目在脚本层面遵循 **"Fail-Fast"** 原则，不进行盲目重试；重试逻辑上浮至指挥官决策层。

### 3.1 脚本层硬熔断 (Hard Circuit Breaker)
- **实现方式**：`set -euo pipefail` 结合显式退出码检查。
- **重试逻辑**：**N/A (无)**。脚本在 `run_step` 失败后立即执行 `exit 1`。
- **补偿行为**：调用 `stop_heartbeat` 清理后台进程，并输出错误日志路径。

### 3.2 指挥官层软重试 (Soft Retry - 逻辑层)
- **物理锚点**：`SKILL.md §三 Step 5`
- **逻辑**：当检测到子进程退出码非 0 时，等待 10s 后触发第二次 `run_shell_command`。
- **限制**：仅限一次重试，连续两次失败则宣告考古任务中断。

### 3.3 信号处理与清理规约 (Signal Handling)
- **清理锁**：使用 `trap 'stop_heartbeat' EXIT` 确保主脚本无论因成功、失败还是 Ctrl+C 退出，都会强制杀掉心跳监控子进程。
- **锚点**：`run-archaeology.sh:L529`。

## 4. 并发保护与原子性 (Concurrency & Atomicity)

| 保护对象 | 实现机制 | 审计结论 |
| :--- | :--- | :--- |
| **中转指令文件** | 覆盖写 (`cat >`) | **弱保护**：不支持多实例在同一项目下并发运行，会发生覆盖竞争。 |
| **心跳日志写入** | 追加写 (`>>`) | **安全**：支持多行并发追加，不影响解析。 |
| **Transcript 读取** | `tail -1` | **非原子读**：在高频写入下可能读到截断的 JSON，通过 Python `try...except` 容错。 |

## 5. 异步机制风险矩阵 (Risk Matrix)

| 环节 | 风险描述 | 影响范围 | 补偿方案 |
| :--- | :--- | :--- | :--- |
| **心跳监控** | `python3` 依赖未在 `preflight` 强制检查 | 进度不可见 | `_extract_transcript_hint` 采用 `|| true` 降级。 |
| **子进程僵尸** | `kill` 信号被屏蔽 | 资源泄露 | 暂无，依赖 OS 级进程清理。 |
| **无断点续跑** | 中途失败需从 Step 0 或 Step 1 重跑 | Token 损耗 | 🔴 **高风险**：当前代码完全缺失断点恢复逻辑。 |
| **消息丢失** | `next-prompt.md` 在写入完成前被读取 | 指挥官指令截断 | 🟡 **中风险**：依靠 `sleep 3` 轮询间隔做简单规避。 |

## 6. 衍生约束清单 (Constraints)

- **CON-06-01 (标准清理)**：所有新增的后台进程必须注册到 `trap` 或 `stop_heartbeat` 中，严禁产生孤儿进程。
- **CON-06-02 (幂等写入)**：所有知识库 `.md` 的写入必须是覆盖写模式（由于缺失断点续跑），防止多次运行产生重复内容。
- **CON-06-03 (心跳只读)**：心跳监控脚本严禁对被监控的 `*.jsonl` 执行写操作。
- **CON-06-04 (超时对齐)**：子进程 `timeout` 必须统一锁定为 1,800s (30min)，防止大型任务因心跳误判而被杀。

---

> [!SUCCESS] 异步机制测绘闭环验证
> - 扫描范围：`run-archaeology.sh` + `SKILL.md` + 信号处理逻辑
> - 提取结果：1 个异步监控进程、1 组 `trap` 信号锁、1 项 30min 硬超时门禁
> - 补偿机制：脚本层“零重试/硬熔断” + 指挥官层“单次软重试”
> - 演进对比：
>   - 事实修正：[修正了脚本层无重试的物理事实]
>   - 章节补充：[补充了 trap 进程清理锁]
>   - 删除章节：[删除了未实现的 Monitor Daemon 功能描述]
> - 旧文档差异：❌不符 2 条 (脚本重试声称、Daemon 已实现声称) / ✅其余已验证
> - EOF 状态：已确认遍历至 `run-archaeology.sh` 最后一行 (L742)，异步逻辑提取完整。

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 流水线通过 `trap EXIT` 实现了基础的后台进程生命周期管控，但缺乏项目级的分布式锁。
> - **推演约束 (Constraint)**: Step 07 必须审计 `config.json` 中的环境变量，特别是关于 Python 路径和 CLI 超时的配置，因为这直接决定了异步心跳的可用性。
> - **物理锚点 (Anchors)**: `run-archaeology.sh:L529` (trap), `L457` (python3 parse)
