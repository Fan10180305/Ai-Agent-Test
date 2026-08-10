# Step 04: 数据模型与生命周期全量测绘

[Role] 数据模型考古学家。
你的任务是从 dao 模块中还原本服务的完整数据模型——
实体定义、表结构、索引设计、分库分表策略、MyBatis 映射的 SQL 操作全景。
你不分析业务逻辑，不读 service/app 模块，只聚焦"数据长什么样、怎么存、怎么查"。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。
已完成步骤：
- Step 0: 旧文档声称提取（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已确认核心工具与三层执行模型
- Step 02: 对外契约 — 已确认脚本参数与 JSON/Markdown 结构约定
- Step 03: 下游依赖 — 已确认对 Gemini CLI, jq, Python3 的依赖，特别是 Python3 在心跳监控中的作用

已知关键线索（由 001 根据前序步骤动态注入）：
> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 心跳监控依赖 python3 解析 ~/.cursor/projects/.../agent-transcripts/ 下的 JSONL 文件。
> - **推演约束 (Constraint)**: Step 04 应重点关注此路径下的 JSONL 结构，将其作为执行 Agent 状态流转的“动态数据模型”。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L480 (TRANSCRIPT_BASE), L491 (_extract_transcript_hint)

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
> - **物理事实 (Context)**: 心跳监控依赖 python3 解析 ~/.cursor/projects/.../agent-transcripts/ 下的 JSONL 文件。
> - **推演约束 (Constraint)**: Step 04 应重点关注此路径下的 JSONL 结构，将其作为执行 Agent 状态流转的“动态数据模型”。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L480 (TRANSCRIPT_BASE), L491 (_extract_transcript_hint)

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
如有旧文档：ai-knowledge-knowledge/Legacy_ai-knowledge_Claims.md — §3 数据模型声称

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/04_Data_Model_and_Lifecycle.md` ，将其作为「旧假说」参照：
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

[Task: 数据模型全量测绘]

### 扫描范围（NON_JAVA 适配）

**区域 A：核心 Schema/契约（必扫）**
- .ai-knowledge/config.json
- 05_module_manifest.json (或生成该文件的脚本逻辑)
- 心跳监控涉及的 JSONL 结构 (由 run-archaeology.sh 推断)

**区域 B：数据操作/持久化（必扫）**
- 脚本中的 `write_file`, `cat >>`, `sed -i`, `jq` 操作
- 日志文件的滚动与清理逻辑

**区域 C：配置与基础设施（必扫）**
- 环境变量定义
- 产出目录结构约定

### 提取任务

#### 1. 核心模型决策摘要 (JSON/JSONL Schema)

#### 2. 表与实体映射总表 (映射为文件与数据结构总表)

#### 3. 查询/操作模式矩阵 (映射为脚本对数据的增删改查)

#### 4. 分片/并发配置解析 (映射为进程并发与文件锁)

#### 5. 数据源与连接配置 (映射为目录路径与 API 端点)

#### 6. 状态机还原 (脚本状态机：STARTUP, PREFLIGHT, EXECUTION, [!SUCCESS])

#### 7. 生命周期分析 (Prompt 到 知识文件 的转化生命周期)

[Action]
在 ai-knowledge-knowledge/ 目录下生成 04_Data_Model_and_Lifecycle.md

[Constraint - 工业级底线]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/04_Data_Model_and_Lifecycle.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

## 结尾标准审计闭环

> [!SUCCESS] 数据模型测绘闭环验证
> - 扫描范围：config.json + manifest.json + 核心脚本数据操作
> - 提取结果：[X] 个核心数据结构、[Y] 组状态机映射
> - 状态流转：从 [状态A] 到 [状态B]
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余已验证
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对业务编排分析有决定性影响的数据事实]
> - **推演约束 (Constraint)**: [基于数据模型发现，强制 Step 05 重点关注的业务流转或状态机逻辑]
> - **物理锚点 (Anchors)**: [对应文件路径及关键逻辑行号]
