# 00_Master_Catalog (知识库总目录与导航索引)

## 1. 项目概览 (Project Overview)
`ai-knowledge` 是一个基于 AI 驱动的自动化知识考古流水线。其核心使命是通过“认知接力”模式，将陌生的代码仓库（当前识别为：NON_JAVA 类型）转化为 AI 可加载、人类可读且结构严密的知识库。本项目通过 001 指挥官（长会话）与执行 Agent（短会话）的双层架构，解决了 AI 编程助手上下文有限、无法感知项目旧约定等痛点。

---

## 2. 知识库导航索引 (Knowledge Map)

| 知识文件 | 核心内容摘要 | 维护模块 |
| :--- | :--- | :--- |
| [01_Module_Skeleton_and_Stack.md](./01_Module_Skeleton_and_Stack.md) | 项目物理骨架（Bash/CLI）、技术栈及 macOS 专有架构红线。 | Infrastructure |
| [02_External_Contracts.md](./02_External_Contracts.md) | 脚本入口、`config.json` 契约及 001 指挥官交互协议。 | Infrastructure |
| [03_Downstream_Dependencies.md](./03_Downstream_Dependencies.md) | 强依赖：Gemini/Cursor CLI、jq 及心跳监控专用的 Python3。 | Infrastructure |
| [04_Data_Model_and_Lifecycle.md](./04_Data_Model_and_Lifecycle.md) | 配置实体、接力 DTO (`next-prompt.md`) 及 `jsonl` 运行轨迹模型。 | Commander |
| [05_Business_Orchestration.md](./05_Business_Orchestration.md) | 认知接力主链、模块深潜循环及旧文档 (Legacy) 交叉验证流。 | Commander |
| [06_Async_Jobs_and_Compensation.md](./06_Async_Jobs_and_Compensation.md) | 异步心跳监控、进程清理锁 (`trap EXIT`) 及软重试机制。 | Infrastructure |
| [07_Config_and_Observability.md](./07_Config_and_Observability.md) | 环境变量、三层日志架构及 1800s 硬超时门禁规则。 | Infrastructure |
| [08a_Module_commander.md](./08a_Module_commander.md) | **深潜报告**：指挥官调度决策、Context 裁剪与 NON_JAVA 语义映射。 | Commander |
| [08b_Module_archaeology.md](./08b_Module_archaeology.md) | **深潜报告**：考古引擎模板规约、`[!SUCCESS]` 审计闭环与演进审计。 | Archaeology |
| [08c_Module_infrastructure.md](./08c_Module_infrastructure.md) | **深潜报告**：物理环境劫持、路径硬编码风险及安装器自包含规约。 | Infrastructure |
| [Legacy_ai-knowledge_Claims.md](./Legacy_ai-knowledge_Claims.md) | 原始 README 声称与代码事实的交叉验证清单（当前为 NO_DOCS 模式）。 | Archaeology |

---

## 3. 场景路由表 (Scenario Routing)

| 场景需求 | 推荐阅读路径 |
| :--- | :--- |
| **排障**：心跳监控不显示进度或 AI 陷入死循环 | [06_Async](06_Async_Jobs_and_Compensation.md) -> [08c_Infra](08c_Module_infrastructure.md) §I |
| **适配**：在 Linux/CI 环境下运行工具（处理 Sed 报错） | [01_Skeleton](01_Module_Skeleton_and_Stack.md) §3 -> [08c_Infra](08c_Module_infrastructure.md) §F |
| **扩展**：调整 AI 的考古深度或增加新的分析切片 | [05_Orchestration](05_Business_Orchestration.md) -> [08b_Arch](08b_Module_archaeology.md) §H |
| **开发**：修改指挥官生成 Prompt 的逻辑或变量替换 | [08a_Commander](08a_Module_commander.md) -> [04_Data_Model](04_Data_Model_and_Lifecycle.md) |
| **部署**：在新项目根目录快速初始化考古工具链 | [02_Contracts](02_External_Contracts.md) -> [08c_Infra](08c_Module_infrastructure.md) §J |
| **观测**：想了解 AI 每一步具体调用了哪些 shell 工具 | [07_Config](07_Config_and_Observability.md) §4.1 -> [08c_Infra](08c_Module_infrastructure.md) §I |

---

## 4. 关键发现与风险红线 (Red Flags)

### 🔴 核心风险 (Hard Red Flags)
- **Linux 兼容性断层**：`run-archaeology.sh` 大量使用 `sed -i ''` (L265)，仅兼容 macOS。在 Linux 环境下流水线将直接崩溃 (Source: 08c_Infra §F)。
- **物理路径硬编码**：`CURSOR_CMD` 指向 `/Applications`，日志监控依赖 `${HOME}/.cursor`。跨平台迁移需重构路径推导 (Source: 08c_Infra §F)。
- **幽灵依赖 (Python3)**：心跳进度监控强依赖 `python3` 命令解析 JSONL，但 `preflight` 中缺失此项预检 (Source: 03_Downstream §7)。

### 🟡 隐形债 (Tech Debt)
- **虚假断点续跑声称**：旧文档提及的 `checkpoint.json` 在代码中完全缺失，目前失败必须重头运行 (Source: 08a_Commander §G)。
- **Token 膨胀隐患**：指挥官 (001) 使用长会话，随着分析步骤增加，上下文累积可能导致响应变慢或超出限制 (Source: 08a_Commander §G)。
- **无锁竞争风险**：`.tmp/next-prompt.md` 采用覆盖写模式，不支持在同一项目下并发运行多个流水线实例 (Source: 06_Async §4)。

---
> [!SUCCESS] 总目录组装闭环验证
> - 输入范围：Step 0-08 全部产出文件
> - 提取结果：[11] 个知识库文件、[6] 个场景路由、[6] 条核心红线
> - 产出文件：00_Master_Catalog.md
> - EOF 状态：已确认遍历至最后一行，无静默截断
