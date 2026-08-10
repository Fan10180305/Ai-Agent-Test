# Step 05: 业务编排全量测绘

[Role] 业务链路考古学家 + DDD 分层审计师。
你有两个并行任务：
1. 从 app 和 service 模块的代码中还原本服务的核心业务编排链路，追踪每条链路的完整调用链。
2. 审计 DDD 分层是否被穿透。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。
已完成步骤：
- Step 0: 旧文档声称提取（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已确认核心工具与三层执行模型
- Step 02: 对外契约 — 已确认脚本参数与数据结构约定
- Step 03: 下游依赖 — 已确认对二进制工具的硬依赖
- Step 04: 数据模型 — 已确认 .tmp/next-prompt.md 状态中转与 JSONL 日志模型

已知关键线索（由 001 根据前序步骤动态注入）：
> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 流水线使用 .tmp/next-prompt.md 作为唯一的无锁状态中转文件，且强依赖 05_module_manifest.json 驱动模块深潜循环。
> - **推演约束 (Constraint)**: Step 05 必须重点审计 05_module_manifest.json 的生成逻辑，它是驱动后续 Step 08 循环的“虚拟数据库”，其格式合法性直接决定了流水线能否闭环。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L643 (manifest 读取), L426 (NextPrompt 覆盖写)

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
> - **物理事实 (Context)**: 流水线使用 .tmp/next-prompt.md 作为唯一的无锁状态中转文件，且强依赖 05_module_manifest.json 驱动模块深潜循环。
> - **推演约束 (Constraint)**: Step 05 必须重点审计 05_module_manifest.json 的生成逻辑，它是驱动后续 Step 08 循环的“虚拟数据库”，其格式合法性直接决定了流水线能否闭环。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L643 (manifest 读取), L426 (NextPrompt 覆盖写)

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
1. ai-knowledge-knowledge/01_Module_Skeleton_and_Stack.md
2. ai-knowledge-knowledge/02_External_Contracts.md
3. ai-knowledge-knowledge/03_Downstream_Dependencies.md
4. ai-knowledge-knowledge/04_Data_Model_and_Lifecycle.md
如有旧文档：ai-knowledge-knowledge/Legacy_ai-knowledge_Claims.md — §4 业务链路声称

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/05_Business_Orchestration.md` ，将其作为「旧假说」参照：
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

[Task: 业务编排全量测绘]

### 扫描范围 (NON_JAVA 适配)

**区域 A：脚本主链 (run-archaeology.sh)**
- 分析 `STEP_LIST` 循环逻辑
- 分析 `_extract_success_block` 与 `_extract_relay_hint` 的接力机制
- 分析模块深潜 (Step 08) 的动态循环实现

**区域 B：逻辑决策点**
- 审计 `PREFLIGHT` 阶段的各种探测逻辑 (POM 探测, Legacy 探测)
- 审计演进模式 (EVOLUTION_MODE) 的判断逻辑

**区域 C：基础设施层**
- 审计日志重定向与 Stdout 拦截机制
- 审计心跳子进程 (python3) 的生命周期管理

### 提取任务

#### 1. 脚本入口 → 步骤映射表 (映射 RPC 入口)

#### 2. 核心分析链路深度还原 (映射业务链路)
- 链路：指挥官启动 → 渲染 Prompt → 孵化 Agent → 拦截 Stdout → 接力下一步

#### 3. 分层审计汇总 (映射 DDD 分层)
- 审计 Commander 逻辑是否泄露到分析模板中
- 审计模板中是否硬编码了 Commander 的路径

#### 4. 设计模式识别 (如：管道过滤器模式, 观察者模式-心跳)

#### 5. 衍生约束清单 (关于子进程隔离与状态原子性的硬性规定)

### 输出要求

**文件一**：在 ai-knowledge-knowledge/ 下生成 05_Business_Orchestration.md

**文件二（脚本接口，必须产出）**：在 ai-knowledge-knowledge/ 下生成 05_module_manifest.json。

格式要求：
```json
[
  {"id": "<模块英文id>", "name": "<模块中文名>", "complexity": "<high|medium|low>"}
]
```
规则：
- 模块边界由你根据本项目物理结构（如：Commander, Archaeology, Infrastructure）自行决定。
- 此文件是自动化流水线驱动 Step 08 循环执行的唯一依据，格式必须是合法 JSON。

[Action]
在 ai-knowledge-knowledge/ 目录下生成 05_Business_Orchestration.md

[Constraint - 工业级底线]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/05_Business_Orchestration.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

## 结尾标准审计闭环

> [!SUCCESS] 业务编排全量测绘闭环验证
> - 扫描范围：run-archaeology.sh + install.sh + 脚本主链逻辑
> - 核心链路：[N] 条主链链路完整还原
> - 05_module_manifest.json：已生成，包含 [X] 个模块
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余已验证
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对异步机制分析有决定性影响的编排事实]
> - **推演约束 (Constraint)**: [基于编排发现，强制 Step 06 重点审计的异步路径或补偿逻辑]
> - **物理锚点 (Anchors)**: [对应业务链路中涉及异步操作的类名及方法行号]
