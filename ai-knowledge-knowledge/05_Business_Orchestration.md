# 05 业务编排全量测绘 (Business Orchestration)

本项目是一个高度自动化的 AI 考古流水线，其核心业务逻辑并非由单一的 Service 类承载，而是通过 `run-archaeology.sh` 脚本驱动的一套 **认知接力 (Cognitive Relay)** 与 **模块深潜 (Module Deep-dive)** 机制实现。

## 1. 入口映射与职责分配 (Entrypoints)

| 入口/函数 | 核心职责 | 业务分层 | 审计结论 |
|---|---|---|---|
| `main()` | 协调串行主链 (Step 0~07) 与 动态模块循环 (Step 08) | **App/Orchestration** | 负责整体生命周期，符合编排层定义。 |
| `preflight()` | 环境检查、协议注入、旧文档 (Legacy) 物理收集 | **Infrastructure** | 存在部分业务逻辑（如 `_generate_no_docs_placeholder`）泄露。 |
| `init_commander()` | 初始化 001 会话，注入角色定义与项目元数据 | **Domain Service** | 实现“指挥官”这一核心领域实体的初始化。 |
| `ask_commander()` | 驱动认知接力，生成下一步 Prompt 并写入 `${NEXT_PROMPT}` | **Domain Service** | 核心状态机驱动，决定流水线的下一步走向。 |
| `run_step()` | 孵化短期 Agent 执行原子考古任务，并记录日志 | **Application Service** | 原子任务调度器。 |
| `start_heartbeat()` | 异步监控 Agent 进度，通过 Python3 解析 Transcript | **Infrastructure** | 典型的“观察者模式”实现。 |

## 2. 核心分析链路深度还原

### 链路 A：认知接力流水线 (Cognitive Relay Pipeline)
这是流水线的骨干，通过 **状态中转文件 (`.tmp/next-prompt.md`)** 实现跨会话的上下文传递：
1. **决策层 (`ask_commander`)**: 读取上一步的 `[!SUCCESS]` 摘要，结合对应的 `.md` 模板，由 001 指挥官 AI 合成新的 Prompt。
2. **物理交付**: 001 指挥官将会话结果使用 `Write` 工具写入物理文件。
3. **执行层 (`run_step`)**: Bash 脚本读取物理文件，将其作为输入启动一个新的、拥有独立 Token 预算的 Agent。
4. **存证**: 将生成的 Prompt 备份为 `${step}_prompt.md` 以供审计。

### 链路 B：模块动态循环 (Dynamic Module Deep-dive)
流水线在完成基础架构分析后，会自动进入递归深潜阶段：
1. **清单加载**: 解析 `05_module_manifest.json` 获取待分析模块 ID。
2. **后缀路由**: 使用 `SUFFIXES` (a, b, c...) 为每个模块分配唯一标识，防止覆盖。
3. **动态注入**: 将 `05_Business_Orchestration.md` 中提取的核心类/逻辑点动态注入到模块分析 Prompt 中。
4. **并行串行化**: 虽是模块分析，但为保证指挥官认知的连续性，模块间采用串行接力方式执行。

### 链路 C：旧文档 (Legacy) 交叉验证流
1. **扫描**: `_collect_from_dir` 对用户指定的多个路径进行深度探测。
2. **标准化**: 统一重命名并收集到 `old-readme/`。
3. **熔断处理**: 若无文档，自动生成 `Legacy_Claims.md` 的 Placeholder，并通知指挥官后续步骤无需进行交叉验证。

## 3. 分层审计汇总 (DDD Audit)

- **Commander 与 Archaeology 的边界**: 
    - **清晰点**: 001 指挥官不处理具体代码（除非读取 `manifest`），只负责“想”；执行 Agent 负责“做”。
    - **模糊点**: `run-archaeology.sh` 中硬编码了大量的 Prompt 路径和变量名，若模板结构发生剧烈变化，脚本将失效。
- **模板与逻辑的耦合**: 模板中存在对 `output_dir` 等物理路径的硬引用，这被视为 **领域逻辑泄露到配置模板**。
- **异步隔离**: `start_heartbeat` 使用了独立的 Python 进程，有效避免了对 Bash 主进程阻塞。

## 4. 设计模式识别

- **管道-过滤器模式 (Pipe-Filter)**: 步骤间的接力通过文件流实现，每一步都是对前一步发现的进一步加工。
- **观察者模式 (Observer)**: 心跳监控子进程持续观察 `transcript.jsonl` 的变化。
- **策略模式 (Strategy)**: 在 `collect_legacy_sources` 中，根据输入是目录还是文件选择不同的收集算法。

## 5. 衍生约束清单

| 约束编号 | 约束内容（一句话，可执行） | 物理锚点 | 严重级别 |
|---|---|---|---|
| CON-05-01 | `05_module_manifest.json` 必须由 Step 05 产出且为合法 JSON | `run-archaeology.sh:L637` | 🔴 核心硬依赖 |
| CON-05-02 | 禁止修改 `.tmp/next-prompt.md` 之外的任何中转文件 | `ask_commander()` | 🟡 最佳实践 |
| CON-05-03 | Step 08 循环必须严格遵循 `SUFFIXES` 的分配顺序 | `run-archaeology.sh:L672` | 🔴 强制 |
| CON-05-04 | 所有 Shell 执行必须声明 `set -euo pipefail` 以防静默失败 | `run-archaeology.sh:L2` | 🔴 强制 |

---

> [!SUCCESS] 业务编排全量测绘闭环验证
> - 扫描范围：run-archaeology.sh + install.sh + 脚本主链逻辑
> - 核心链路：[3] 条主链链路完整还原（认知接力、模块循环、Legacy收集）
> - 05_module_manifest.json：已验证，包含 [3] 个模块 (commander, archaeology, infrastructure)
> - 旧文档差异：✅ 已基于代码事实对旧假说中的执行引擎细节进行了修正
> - EOF 状态：已确认遍历至脚本最后一行 (L774)，无静默截断
