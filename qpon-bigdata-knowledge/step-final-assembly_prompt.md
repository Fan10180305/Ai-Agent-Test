# 0. 核心接力策略（最高执行优先级）

Step08 test-dags: drill decision/failure modes; do not redo Step05; dags/ only; next test-dags/final: Unpause+webhook; etl_alter first; distinguish swallow-green vs ES raise-red; forbid side clocks as ADS day; device_active SLA=tag+rpt-d+analyst-serving; alarm_h hour-Skip still o

**[执行准则]**: 以上为上一步指挥官转交的"强制任务"。你必须优先响应并回显证据，否则将被判定为考古失败。

# 0.5 项目军规（项目级行为约束）

意图路由：先读知识库入口再改代码；Skill 优先调度流水线。
强制红线：禁止 macOS 专有 sed；路径锚定；Shell set -euo pipefail。
双写要求：改调度逻辑须同步更新知识库。
本轮相关约束：扫描权威范围为 dags/；产出写入 qpon-bigdata-knowledge/；NON_JAVA 语义映射。

**[执行准则]**: 项目军规对本步分析与写回具有高优先级约束，不得被普通先验信息覆盖。

【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Airflow DAG、Python 算子、SQL/BigQuery、配置文件、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 `<project>-xxx/` 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在而触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

【扫描边界硬约束】本次知识库的代码事实权威范围严格限定为工作区内的 `dags/` 目录（含子目录）。
禁止以仓库其他目录（如 scripts/、ai-knowledge-knowledge/）作为业务事实来源；仅可读取协作协议与产出目录。

# Step Final: 总目录组装与规则生成

[Role] 知识库架构师 + AI 行为约束设计师。
你的任务是：
1. 生成 00_Master_Catalog.md — 全局导航索引
2. 生成 .cursor/rules/qpon-bigdata.mdc — AI 开发军规

[Context]
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。
已完成步骤：
- Step 0: 旧文档声称提取
- Step 01-07: 技术维度横向切片（骨架/契约/依赖/数据/编排/异步/配置）
- Step 08a-08e: 业务模块纵向切片（签到/多单/渠道/抽奖/其他）

本步骤是知识库的收官步骤，将所有产出组装成可导航的知识体系，
并提炼出 AI 开发时必须遵守的行为约束。

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件，建立全局认知：
1. qpon-bigdata-knowledge/Legacy_qpon-bigdata_Claims.md — 旧文档声称
2. qpon-bigdata-knowledge/01_Module_Skeleton_and_Stack.md — 骨架与技术栈
3. qpon-bigdata-knowledge/02_External_Contracts.md — 对外契约
4. qpon-bigdata-knowledge/03_Downstream_Dependencies.md — 下游依赖
5. qpon-bigdata-knowledge/04_Data_Model_and_Lifecycle.md — 数据模型
6. qpon-bigdata-knowledge/05_Business_Orchestration.md — 业务编排
7. qpon-bigdata-knowledge/06_Async_Jobs_and_Compensation.md — 异步与补偿
8. qpon-bigdata-knowledge/07_Config_and_Observability.md — 配置与可观测
9. qpon-bigdata-knowledge/08a~08e_Module_*.md — 业务模块深潜


[Task: 总目录组装与规则生成]

### 任务 A：生成 00_Master_Catalog.md

#### A1. 项目概览
一句话定义本服务的核心职责和业务定位。

#### A2. 知识库文件导航
列出所有知识库文件，每个文件用一句话说明其内容和用途。

格式：
```
## 知识库文件清单

### 技术维度（横向切片）
- **01_Module_Skeleton_and_Stack.md** — 模块骨架与技术栈
  - 用途：了解项目结构、依赖关系、技术选型
  - 适用场景：新人上手、技术栈升级、依赖冲突排查
  
- **02_External_Contracts.md** — 对外契约
  - 用途：了解本服务对外暴露的 Dubbo 接口和 DTO
  - 适用场景：新增/修改接口、契约变更评估、下游集成

...（其他文件）

### 业务维度（纵向切片）
- **08a_Module_SignIn.md** — 签到模块
  - 用途：深度理解签到业务逻辑、校验链、缓存策略
  - 适用场景：签到相关需求开发、签到问题排查

...（其他模块）
```

#### A3. 场景路由表
为常见开发场景提供知识库文件的阅读路径。

格式：
```
## 场景路由表

| 场景 | 必读文件 | 可选文件 | 说明 |
|------|---------|---------|------|
| 排障/线上问题 | 07, 06, 03 | 05, 对应 08x | 先看配置和异步机制，再看依赖和业务链路 |
| 新增/修改 Dubbo 接口 | 02, 05 | 对应 08x | 先看契约规范，再看业务编排 |
| 新增/修改数据表 | 04, 05 | 对应 08x | 先看数据模型，再看业务编排 |
| 新增 Job/MQ | 06, 07 | 05 | 先看异步机制，再看配置 |
| 新增下游依赖 | 03, 05 | 01 | 先看依赖规范，再看业务编排 |
| 新增业务模块 | 05, 对应 08x | 02, 04, 06 | 先看业务编排，再看模块深潜 |
| 性能优化 | 07, 04, 03 | 05, 06 | 先看配置和缓存，再看数据模型和依赖 |
| 快速上手 | 00, 01, 05 | 08a-08e | 先看总目录和骨架，再看业务编排和模块深潜 |
```

#### A4. 关键发现汇总
从 Step 01-08 中提取的关键发现（Red Flags、幽灵依赖、设计模式等）。

### 任务 B：生成 .cursor/rules/qpon-bigdata.mdc

#### B1. 意图路由（对应目的一）
强制 AI 在动手写代码前，先读取相关知识库文件。

格式：
```mdc
## 第一章：意图路由协议

**强制首读**：任何涉及本服务的任务，先读 `qpon-bigdata-knowledge/00_Master_Catalog.md`，从场景路由表确定本次任务所需的知识文件。

**场景分流**（按场景路由表执行）：
- 排障 → 07 → 06 → 03 → 对应 08x
- 新增/改 Dubbo 接口 → 02 → 05 → 对应 08x
- 新增/改数据表 → 04 → 05 → 对应 08x
- 新增 Job/MQ → 06 → 07 → 05
- 新增下游依赖 → 03 → 05 → 01
- 新增业务模块 → 05 → 对应 08x → 02, 04, 06
- 性能优化 → 07 → 04 → 03
- 快速上手 → 00 → 01 → 05 → 08a-08e

**禁止**：未读取相关知识文件就直接全库搜索或修改代码。
```

#### B2. 防御性编码红线（对应目的二）
从 Step 01-08 的衍生约束中提炼出 AI 必须遵守的铁律。

格式：
```mdc
## 第二章：防御性编码红线

### 架构层红线
🔴 **[G-AR-01]** app 层只做委托转发，禁止编写业务逻辑。
来源：05 §4。违反后果：破坏分层，Domain Service 被架空。

🔴 **[G-AR-02]** client 模块禁止新增对内部服务 client JAR 的依赖。
来源：01 §3 RF-1。违反后果：传递性依赖污染所有消费方。

...（其他红线）

### RPC 与超时红线
🔴 **[G-RPC-01]** 新增 Dubbo 消费者必须显式配置 timeout 和 retries。
来源：03 §3。违反后果：默认超时不可控，链路雪崩。

...（其他红线）

### 异常处理红线
🔴 **[G-EX-01]** 禁止 catch 异常后 return null/false。
来源：07 §4.2。违反后果：故障静默传播，排障无迹可循。

...（其他红线）
```

#### B3. 知识库双写协议（对应目的三）
强制 AI 在修改代码时同步更新知识库文件。

格式：
```mdc
## 第三章：知识库双写协议

代码变更提交前，必须执行知识库资产审计：

| 代码变更类型 | 必须同步更新的知识文件 | 更新内容 |
|---|---|---|
| 新增/修改 Dubbo 接口 | 02_External_Contracts.md | 接口 + 方法签名 + DTO |
| 新增/修改数据表/字段 | 04_Data_Model_and_Lifecycle.md | 实体 + Mapper + 分表规则 |
| 新增/修改下游依赖 | 03_Downstream_Dependencies.md | 接口 + timeout + 调用点 |
| 新增/修改 Job/MQ | 06_Async_Jobs_and_Compensation.md | 清单 + 补偿策略 |
| 新增/修改缓存策略 | 07_Config_and_Observability.md | 缓存点全景表 |
| 新增/修改配置项 | 07_Config_and_Observability.md | 配置项清单 |
| 新增/修改业务模块 | 对应 08x 文件 | 决策点 + 扩展点 + 失败模式 |
| 项目骨架/依赖变更 | 01_Module_Skeleton_and_Stack.md | 模块依赖链 + Red Flags |

**自检清单**（每次提交前强制执行）：
> 🔍 本次变更是否导致以下知识资产过期？
> `[ ]` 02 接口契约 `[ ]` 03 依赖拓扑 `[ ]` 04 数据模型
> `[ ]` 06 异步机制 `[ ]` 07 配置/缓存 `[ ]` 08x 业务模块
> 如有过期，必须连带输出对应 `.md` 文件的更新 Diff。
```

#### B4. 项目特有约束
从 Step 08 的衍生约束中提炼出本项目特有的业务规则。

#### B5. 知识库盲区行为规范
当 AI 遇到知识库未覆盖的代码区域时的行为规范。

### 任务 C：生成 .gemini/rules/qpon-bigdata.md (Antigravity 兼容规则)

基于任务 B 整理出的所有协议和红线内容，生成一份完全相同的规则文件，但必须严格符合 Gemini CLI 的项目级规则标准。

**存放路径**：`.gemini/rules/qpon-bigdata.md`

**格式约束 (必须包含 Frontmatter)**：
文件顶部必须严格以 `---` 包围的 YAML Frontmatter 开头。

Gemini 端规则文件的 frontmatter **必须包含且只包含**以下三个字段：
```yaml
---
description: qpon-bigdata 核心意图路由与防御性编码军规
globs: **/*
trigger: always_on
---
```

**禁止**在 Gemini 端 frontmatter 中出现 `alwaysApply`、`priority` 等 Cursor 专有字段。

Cursor 端 `.mdc` 文件的 frontmatter **必须包含**以下字段：
```yaml
---
description: qpon-bigdata 核心意图路由与防御性编码军规
globs: **/*.md, **/*.sh, **/*.py, **/*.java
alwaysApply: false
---
```

**禁止**在 Cursor 端 frontmatter 中出现 `trigger`、`priority` 等 Gemini 专有字段。

规则正文内容两端保持一致，格式如下：
```md
---
description: qpon-bigdata 核心意图路由与防御性编码军规
globs: **/*
trigger: always_on
---
# qpon-bigdata 开发军规

（此处无缝粘贴任务 B 中生成的第一章到第五章的所有内容）
```

[Action]
1. 在 qpon-bigdata-knowledge/ 目录下生成 00_Master_Catalog.md
2. 在 .cursor/rules/ 目录下生成 qpon-bigdata.mdc
3. 在 .gemini/rules/ 目录下生成 qpon-bigdata.md

[Constraint - 工业级底线]

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `qpon-bigdata-knowledge/` 下的前序产出文件不存在，必须列出缺失文件并停止，输出：`❌ 未在工作区找到 [文件路径]，请确认前序步骤已完成。` 禁止推断替代内容，禁止访问工作区外目录。

**输出格式锁定**：
- 00_Master_Catalog.md 必须包含：项目概览、文件导航、场景路由表、关键发现汇总
- qpon-bigdata.mdc 必须包含：意图路由、防御性编码红线、知识库双写协议、项目特有约束、盲区行为规范

**严防静默截断**：
- 场景路由表必须覆盖至少 8 个常见场景
- 防御性编码红线必须至少包含 10 条红线
- 知识库双写协议必须覆盖至少 8 种代码变更类型

**专业性底线**：
- 红线内容具体可执行，不用模糊词汇
- 每条红线必须标注来源（哪个文件的哪个章节）
- 每条红线必须说明违反后果

**结尾标准审计闭环**：

```
> [!SUCCESS] 总目录组装闭环验证
> - 输入范围：Step 0-08 全部产出文件
> - 提取结果：[X] 个知识库文件、[Y] 个场景路由、[Z] 条防御红线、[W] 项双写触发条件
> - 产出文件：00_Master_Catalog.md + .cursor/rules/qpon-bigdata.mdc + .gemini/rules/qpon-bigdata.md
> - EOF 状态：已确认遍历至最后一行，无静默截断
```

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: <本步目标知识文件相对路径>
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

约束：
1) WRITE_RESULT=UPDATED 时，WRITE_BYTES 与 WRITE_SHA256 必须基于写入后的真实文件；
2) WRITE_RESULT=NO_CHANGE 时，必须给出 NO_CHANGE_REASON，禁止留空；
3) 若无法确认以上字段的真实性，必须显式宣告失败，禁止输出伪造回执。
