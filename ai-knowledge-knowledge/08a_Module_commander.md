# 08a_Module_commander (指挥官核心与调度编排深潜)

本模块定义了 `ai-knowledge` 考古流水线的“大脑”逻辑，涵盖了从环境预检到全量知识库产出的端到端编排机制。它通过“指挥官 (AI 会话)”与“调度器 (Bash 脚本)”的解耦协作，实现了高强度的认知接力分析。

---

## A. 模块定位
`commander` 模块是流水线的核心决策与编排层。其职责边界定义如下：
- **环境准入**：执行 OS 级工具链检查（jq, cursor, python3）及工作区协议同步（`_ensure_protocol`），并处理旧文档（Legacy）的标准化收集。
- **上下文编排**：负责各分析步骤之间的“认知接力 (Cognitive Relay)”，通过 `ask_commander` 驱动 001 会话生成下一步 Prompt，确保前序发现精准进入后续任务。
- **任务委派**：通过 `run_step` 孵化物理隔离的执行 Agent 子进程，并维护独立的 Token 预算。
- **生命周期管理**：控制串行主链（Step 0-07）与动态模块循环（Step 08）的交替执行，并提供实时心跳进度监控。

---

## B. 核心函数清单 (NON_JAVA 语义映射)

| 函数名 | 类型 | 职责 |
| :--- | :--- | :--- |
| `main` | Orchestrator | 顶层生命周期协调器，定义了 Step 0-08 及 Final Assembly 的执行顺序。 |
| `preflight` | Validator | 环境预检，确保协议文件挂载、CLI 可用，并处理无文档时的熔断降级。 |
| `init_commander` | Constructor | 初始化 001 指挥官会话，注入 Master 角色定义及变量替换协议。 |
| `ask_commander` | Dispatcher | 核心状态机驱动，向 001 发送指令并轮询等待 `next-prompt.md` 生成。 |
| `run_step` | Executor | 孵化短期 Agent 实例，记录完整转录（Transcript）并执行退出码检查。 |
| `start_heartbeat` | Monitor | 异步监控进程，利用 Python3 解析 `transcript.jsonl` 以提取实时动作摘要。 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
| :--- | :--- | :--- |
| `bash run-archaeology.sh` | 用户/CLI | 整个考古流程的唯一物理入口，接受项目名及 Legacy 路径参数。 |
| `ask_commander()` | 脚本内部逻辑 | 流水线的“逻辑中枢”，决定下一步 Prompt 的具体内容。 |
| `run_step()` | 脚本内部逻辑 | 流水线的“执行引擎”，启动具体的考古原子任务。 |

---

## D. 调用链
参照 `05_Business_Orchestration.md` §2.1，本模块驱动的核心链路如下：
1. **主链驱动**: `main` -> `init_commander` -> `ask_commander` -> `run_step` (循环 Step 0-07)。
2. **模块深潜**: `main` -> 解析 `05_module_manifest.json` -> 循环调用 `ask_commander` & `run_step` (Step 08-a/b/c...)。
3. **心跳闭环**: `run_step` -> `start_heartbeat` -> 监听 `agent-transcripts/` -> 输出实时进度。

---

## E. 前序步骤验证
- **Step 02 (对外契约)**：已验证 `run-archaeology.sh` 对 `cursor` CLI 和 `jq` 的强依赖。
- **Step 03 (下游依赖)**：已确认对 `python3` 的幽灵依赖风险（监控进度需用）。
- **Step 04 (数据模型)**：已验证 `next-prompt.md` 作为认知接力唯一物理载体的生命周期。
- **Step 05 (业务编排)**：已确认 `05_module_manifest.json` 是 Step 08 启动的硬性先置条件。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据（脚本行号） | 严重级别 |
| :--- | :--- | :--- | :--- |
| CON-08a-01 | **Python3 强依赖**：心跳监控必须在具有 Python3 环境的 OS 上运行。 | `L457 (_extract_transcript_hint)` | 🔴 核心 |
| CON-08a-02 | **超时硬编码**：001 响应超时限制在 1800s，长 Prompt 生成可能触发熔断。 | `L429 (max_wait=1800)` | 🟡 风险 |
| CON-08a-03 | **路径锚定约束**：脚本必须在项目根目录执行，否则 `PROMPT_DIR` 推导会失效。 | `L35-L55` | 🔴 强制 |
| CON-08a-04 | **变量污染防护**：每个 Agent 必须使用 `create-chat` 创建全新会话 ID 以隔离 Context。 | `L555 (executor_id)` | 🔴 强制 |
| CON-08a-05 | **Sed 平台差异**：禁止在脚本中使用 `sed -i ''`，否则 Linux 环境执行必败。 | `L265 (macOS 特有语法)` | 🔴 核心 |

---

## G. 认知接力 (Cognitive Relay) 深度解析
- **核心逻辑**：通过物理隔离的会话实现“大任务分解”。指挥官（001）充当架构师，通过提取上一步的 `[!SUCCESS]` 块（L585 处的摘要提取逻辑），动态拼装下一步的输入。
- **决策点**：
    - `L606-L650`：根据 Step ID 选择对应的 Prompt 模板。
    - `L410-L425`：通过 `Write` 工具将 Prompt 渲染结果落地为文件，实现“静默接力”。
- **失败模式**：
    - 若 Agent 未能按规约输出 `[!SUCCESS]` 标签，`get_result_summary` 会退化为提取日志最后 30 行，可能导致指挥官获取的上下文包含过多噪声。

---

## H. NON_JAVA 模式下的语义映射策略
- **实现机制**：在 `L542` (初始化消息) 中，指挥官被赋予了「语义深度解读专家」角色。当检测到非 Java 结构时，不再强行搜索 `pom.xml` 或 `src/main/java`，而是转向：
    - **文件树扫描**：识别脚本、配置、协议定义文件。
    - **意图映射**：将「RPC 契约」映射为「脚本参数/CLI 交互」，将「MyBatis/DB」映射为「JSON 文件/持久化 Log」。
- **熔断规避**：模板中的硬熔断指令（如找不到路径即停止）在 NON_JAVA 模式下通过 `SKILL.md` 的全局指令被软化为「映射分析」。

---

## I. 异步监控与心跳实现 (Observation)
- **技术栈**：Bash 后台进程 (`&`) + Python3 进程。
- **物理锚点**：`L457` (`_extract_transcript_hint`)。
- **逻辑细节**：利用 Python 解析 Cursor 的内部转录日志（`jsonl` 格式）。它能识别 Agent 是在 `thinking` 还是在 `tool_use`，并将最新的动作摘要实时推送至控制台。
- **关键隐患**：若 `python3` 缺失，`start_heartbeat` 会在后台静默报错，用户将无法感知 Agent 是否卡死。

---

> [!SUCCESS] 001指挥官核心 模块深潜闭环验证
> - 扫描范围：run-archaeology.sh, 00-07 知识库文件
> - 提取结果：6 个核心函数、5 条衍生约束、3 个业务特性章节 (G, H, I)
> - 全文行数：115 行（≤ 500 行）
> - 前序验证：Step 02 [CLI 依赖] / Step 03 [Python/Sed 风险] / Step 04 [状态中转]
> - EOF 状态：已确认遍历至 run-archaeology.sh L774，无静默截断

事实修正：[修正了指挥官超时的具体行号，确认了心跳监控对 Python3 的强依赖事实]
章节保持：[模块定位、调用链]
章节补充：[核心函数清单增加了 NON_JAVA 语义映射职责；衍生约束增加了行号证据]
章节重写：[重写了 G、H、I 章节，使其更贴合代码物理实现]
删除章节：[无]
结构调整原因：[为了对齐 Step 08 模板骨架，并深入挖掘 NON_JAVA 项目下的特定编排逻辑]
无意义重写判定：[否]
最小证据：[无]
退化风险申报：[无]

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 心跳监控 (`_extract_transcript_hint`) 强依赖 `python3`；指挥官超时硬编码在 `L429` 为 1800s。脚本存在大量 `sed -i ''` 的 macOS 专有写法。
> - **推演约束 (Constraint)**: 下一步（考古引擎模块 08b）在分析模板时，必须评估「意图映射指令」在各 Prompt 模板中的实际执行效果，核实是否有效规避了路径熔断。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L457 (python3), L265 (sed), L429 (timeout)。
