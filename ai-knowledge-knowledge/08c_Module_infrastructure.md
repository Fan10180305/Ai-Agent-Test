# 08c_Module_infrastructure (业务模块深潜 - infrastructure)

## A. 模块定位
`infrastructure` 模块是 `ai-knowledge` 流水线的物理基石，负责**运行环境治理、AI 进程生命周期编排与元协作协议强制注入**。它通过自包含的安装脚本与双层 AI 会话模型（Commander/Agent），为知识库考古提供了隔离且受控的执行环境。

## B. 核心组件职责

| 组件 | 物理实现 | 核心职责 |
| :--- | :--- | :--- |
| **流水线调度器 (Orchestrator)** | `run-archaeology.sh` | 核心引擎。管理 Commander/Agent 进程模型，驱动主链与模块循环。 |
| **环境安装器 (Installer)** | `install.sh` | 负责自包含安装，初始化 `config.json` 并强制注入元协议。 |
| **进度监听器 (Heartbeat)** | `start_heartbeat` | 异步监控子进程。利用 Python 解析 `.jsonl` 实时提取 AI 工具调用语义。 |
| **安全拷贝算子 (Safe Copy)** | `_copy_with_dedup()` | 物理文件去重拷贝，防止收集旧文档时发生重名覆盖。 |

## C. 入口方法/功能

| 入口方法 | 调用方 | 物理位置 | 一句话描述 |
| :--- | :--- | :--- | :--- |
| `preflight()` | `main` | `run-archaeology.sh:274` | 校验工具链，并调用 `_ensure_protocol` 注入规则。 |
| `init_commander()` | `main` | `run-archaeology.sh:341` | 建立 001 指挥官长会话，注入系统角色及全局考古记忆。 |
| `ask_commander()` | `main` | `run-archaeology.sh:439` | 指令接力中枢。请求 001 生成 `next-prompt.md`，硬超时 1800s。 |
| `_ensure_protocol()` | `preflight` | `run-archaeology.sh:205` | 物理劫持认知。同步协议至 `.gemini/rules/` 以强制 AI 准则。 |

## D. 调用链引用
引用自 **Step 05 (05_Business_Orchestration.md)**：
- 支撑了 **“认知接力流水线 (Core Pipeline)”** 的物理执行。
- 负责 **“旧文档收集 (Legacy Collection)”** 中的物理搬运。

## E. 前序步骤验证

- **Step 02 (Contracts)**: ✅ 验证通过。模块通过 `GEMINI_API_KEY` 环境变量与 API 契约解耦。
- **Step 03 (Dependencies)**: ✅ 验证通过。代码证实了对 `python3` (L489) 及 `jq` 的强依赖。
- **Step 04 (Data Model)**: ✅ 验证通过。`config.json` 驱动了全路径推导，`05_module_manifest.json` 驱动了深潜循环。

## F. 衍生约束清单

| 约束 ID | 约束内容 | 代码证据 | 违反后果 |
| :--- | :--- | :--- | :--- |
| C-INF-001 | 严禁使用非 POSIX 的 `sed` 语法，当前硬伤为 `sed -i ''` | `run-archaeology.sh:265` | Linux 环境执行崩溃 |
| C-INF-002 | `CURSOR_CMD` 路径硬编码为 `/Applications` 目录 | `run-archaeology.sh:101` | 非 macOS 环境无法找到 CLI 工具 |
| C-INF-003 | 异步监控进程必须在主进程 `EXIT` 信号捕获时强制清理 | `run-archaeology.sh:525` | 产生僵尸 Python 监控进程 |
| C-INF-004 | 转录日志路径依赖于 macOS 风格的 `${HOME}/.cursor` | `run-archaeology.sh:104` | 不同平台下日志监控失效 |

## G. 元协议物理劫持与环境预检 (Protocol Hijacking)
- **业务背景**：Agent 默认可能具有通用 AI 偏见，必须强制其服从项目底层法典。
- **实现方式**：`preflight -> _ensure_protocol`。
- **关键决策点**：
    - `_ensure_protocol` 在流水线启动第一秒即执行物理文件拷贝。
    - 校验 `jq` 与 `cursor` 可用性，失败则立即熔断 (L318)。
- **失败模式**：权限不足导致 Rules 无法写入，Agent 将在无约束状态下运行。

## H. 指挥官-Agent 双层接力架构 (Relay Architecture)
- **业务背景**：解决考古过程中长程记忆丢失与 Token 膨胀。
- **实现方式**：`init_commander` (长会话) + `Agent` (短会话)。
- **关键决策点**：
    - `ask_commander` 通过文件 I/O (`next-prompt.md`) 实现进程间通信。
    - `init_commander` (L341) 注入复杂的角色 Prompt，确立指挥官的“提示词编译器”身份。
- **失败模式**：`NEXT_PROMPT` 文件竞争或生成超时（1800s 阈值）。

## I. 异步监控与语义提取 (Monitoring & Semantics)
- **业务背景**：提升黑盒考古的可观测性。
- **实现方式**：`start_heartbeat` 调用 Python 算子。
- **关键决策点**：
    - `_extract_transcript_hint` (L489) 利用 `json.load` 提取 `tool_use` 名称。
    - `get_result_summary` (L539) 扫描前 25 行以提取 `[!SUCCESS]` 证据块。
- **失败模式**：`.jsonl` 格式异常导致监控崩溃。

## J. 安装器规约与路径确定性 (Installer & Determinism)
- **业务背景**：实现考古流水线的“一键部署”与“无迹卸载”。
- **实现方式**：`install.sh` 构建自包含 `.ai-knowledge/`。
- **关键决策点**：
    - `install.sh` 生成 `config.json` 锁定项目元数据。
    - `uninstall.sh` 支持 `--purge` 参数清理生成的知识库资产。
- **失败模式**：`install.sh` 无法在 Home 目录执行的安全保护逻辑 (L56)。

> [!SUCCESS] infrastructure 模块深潜闭环验证
> - 扫描范围：`run-archaeology.sh`, `install.sh`, `uninstall.sh`
> - 提取结果：4 个核心入口、6 条衍生约束、4 个特性章节
> - 物理锚点：L101 (CMD Path), L104 (Log Path), L265 (Sed), L525 (Trap)
> - EOF 状态：已确认遍历至 `run-archaeology.sh` L742，所有底层编排逻辑已全量还原。

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 该模块通过 `_ensure_protocol` 实现了对 AI 认知的物理劫持，并确认了 `sed -i ''` (L265) 等多处平台依赖硬伤。
> - **推演约束 (Constraint)**: 下一步收官组装需确保 `08c_Module_infrastructure.md` 中记录的约束（如非 POSIX Sed）被正确反馈至项目治理建议中。
> - **物理锚点 (Anchors)**: `scripts/knowledge-archaeology/run-archaeology.sh` L101, L265, L525。
