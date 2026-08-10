# Step 06: 异步机制与补偿全量测绘

[Role] 异步架构审计师。
你的任务是从代码中还原本服务的全部异步机制——
定时任务、MQ 生产/消费、补偿策略、重试逻辑。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。
已完成步骤：
- Step 01: 骨架测绘 — 已确认核心工具与三层执行模型
- Step 02: 对外契约 — 已确认脚本参数约定
- Step 03: 下游依赖 — 已确认对二进制工具的硬依赖
- Step 04: 数据模型 — 已确认 .tmp/next-prompt.md 状态中转
- Step 05: 业务编排 — 已确认脚本主链流水线逻辑

已知关键线索（由 001 根据前序步骤动态注入）：
> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 脚本中存在一个基于 Python3 的后台心跳监控进程 (start_heartbeat)，它通过轮询解析 transcript.jsonl 来实现 Agent 进度的实时可见性。这是流水线中唯一的持续异步逻辑。
> - **推演约束 (Constraint)**: Step 06 必须重点审计该心跳进程的生命周期管理与异常补偿逻辑（如：若 Python 脚本崩溃，是否会影响主 Bash 脚本的退出状态）。
> - **物理锚点**: run-archaeology.sh:L446 (start_heartbeat), L492 (stop_heartbeat)

【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Shell/Python 脚本、配置文件、JSON 契约、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 ai-knowledge-xxx/ 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在而触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

# 0. 核心接力策略（最高执行优先级）

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 脚本中存在一个基于 Python3 的后台心跳监控进程 (start_heartbeat)，它通过轮询解析 transcript.jsonl 来实现 Agent 进度的实时可见性。这是流水线中唯一的持续异步逻辑。
> - **推演约束 (Constraint)**: Step 06 必须重点审计该心跳进程的生命周期管理与异常补偿逻辑（如：若 Python 脚本崩溃，是否会影响主 Bash 脚本的退出状态）。
> - **物理锚点**: run-archaeology.sh:L446 (start_heartbeat), L492 (stop_heartbeat)

**[执行准则]**: 以上为上一步指挥官转交的"强制任务"。你必须优先响应并回显证据，否则将被判定为考古失败。

# 0.5 项目军规（项目级行为约束）

### 意图路由
- 全局入口：读取 ai-knowledge-knowledge/00_Master_Catalog.md。
- Skill 优先：流水线操作必须先通过 archaeology-commander Skill 入口。

### 强制红线
- 禁止静默失败：所有 Shell 脚本声明 set -euo pipefail。
- 严禁错误掩盖：禁止使用 2>/dev/null 且不检查 $?。
- 严禁 macOS 专有 Sed：禁止使用 sed -i ''。
- 路径锚定：所有路径必须基于项目根目录或 config.json 变量。
- 密钥保护：禁止硬编码 API Key。
- 异步心跳：执行器修改需确保心跳更新。

### 双写要求
- 修改调度器、脚本参数、CLI 依赖等需同步更新 01-08 知识库文件。

### 本轮相关约束
- 认知接力模式，非交互式原则。

**[执行准则]**: 项目军规对本步分析与写回具有高优先级约束，不得被普通先验信息覆盖。

[先验知识注入]
请静默读取以下文件，建立先验认知：
1. ai-knowledge-knowledge/05_Business_Orchestration.md
2. ai-knowledge-knowledge/04_Data_Model_and_Lifecycle.md
如有旧文档：ai-knowledge-knowledge/Legacy_ai-knowledge_Claims.md — §6 异步机制声称

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/06_Async_Jobs_and_Compensation.md` ，将其作为「旧假说」参照：
- 代码事实是唯一权威；旧假说仅作参照，不得凌驾于代码之上
- 旧假说与代码不符时，以代码事实修正对应内容
- 代码中存在但旧假说未记录的逻辑，补充进对应章节
- 若代码事实未变化：优先保持旧文档高价值结构与表达，禁止仅因风格变化进行大面积重写
- 若删除旧章节/旧表格：必须给出代码证据锚点，否则视为退化性写回

### 演进对比输出要求（可审计格式）

在 `[!SUCCESS]` 前 20 行内输出以下字段：
- `事实修正：[xx]`
- `章节保持：[xx]`
- `章节补充：[xx]`
- `章节重写：[xx]`
- `删除章节：[xx]`
- `结构调整原因：[一句话，如无则写 无]`
- `无意义重写判定：[是/否]`
- `最小证据：[若无意义重写判定=是，至少 1 条：被重写章节 + 变化类型 + 代码事实未变化说明；否则写 无]`
- `退化风险申报：[触发时填写 受影响资产 + 变化类型 + 代码证据锚点 + 是否接受本次写回；未触发写 无]`

在 `[!RELAY]` 的 Context 字段中，若演进发现对下一步有决定性影响的变化（如：旧假说中某服务已删除/新增关键调用），必须声明。无演进变化时按常规填写。
---

[Task: 异步机制全量测绘]

### 扫描范围 (NON_JAVA 适配)

**区域 A：后台进程与心跳 (start_heartbeat)**
- 分析 Python 脚本在子进程中的生命周期
- 分析 `trap` 信号捕捉与资源清理 (stop_heartbeat)

**区域 B：脚本内重试与补偿**
- 搜索 Shell 脚本中的 `while` / `for` 重试循环
- 搜索对失败退出码的补偿逻辑

**区域 C：并发控制与锁**
- 搜索 `.lock` 文件或基于目录的原子操作

### 提取任务

#### 1. 后台/异步进程清单 (映射 Job/MQ)

#### 2. 重试与补偿机制深度解析 (映射补偿流程)

#### 3. 信号处理与清理规约 (映射事务/降级)

#### 4. 异步机制风险矩阵 (并发冲突、孤儿进程、静默失败)

#### 5. 衍生约束清单 (关于后台进程与错误捕获的可执行约束)

[Action]
在 ai-knowledge-knowledge/ 目录下生成 06_Async_Jobs_and_Compensation.md

[Constraint - 工业级底线]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/06_Async_Jobs_and_Compensation.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

## 结尾标准审计闭环

> [!SUCCESS] 异步机制测绘闭环验证
> - 扫描范围：run-archaeology.sh + 信号处理 + 重试逻辑
> - 提取结果：[X] 个异步环节、[Y] 处补偿点
> - 衍生约束：[D] 条（🔴强制 / 🟡建议）
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余已验证
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对配置与可观测性分析有决定性影响的异步事实]
> - **推演约束 (Constraint)**: [基于异步机制发现，强制 Step 07 重点审计的配置项或监控盲区]
> - **物理锚点 (Anchors)**: [对应代码引用行号]
