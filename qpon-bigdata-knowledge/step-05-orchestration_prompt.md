# 0. 核心接力策略（最高执行优先级）

Step05: map orchestration via DAG deps + ExternalTaskSensor + DELETE+INSERT/MERGE lifecycles; produce 05_Business_Orchestration.md AND 05_module_manifest.json; dags/ only

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

# Step 05: 业务编排全量测绘

[Role] 业务链路考古学家 + DDD 分层审计师。
你有两个并行任务：
1. 从 app 和 service 模块的代码中还原本服务的核心业务编排链路，
   追踪每条链路的完整调用链。
2. 审计 DDD 分层是否被穿透——app 层是否下沉了业务逻辑，
   service 层是否直接操作了 DAO，基础设施层是否侵入了领域层。

[Context]
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。
已完成步骤（具体数字由 001 根据前序产出动态注入）：
- Step 0: 旧文档声称（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已完成，子模块结构已确认
- Step 02: 对外契约 — 已完成，Dubbo 接口入口已明确
- Step 03: 下游依赖 — 已完成，外部服务调用点已记录
- Step 04: 数据模型 — 已完成，Mapper 操作全景已记录

本步骤是知识库中体量最大的一步。核心目标：
让 AI 在未来定位问题或交付需求时，能沿着业务链路精确找到代码位置。

已知关键线索（由 001 根据前序步骤动态注入）：
> [!SUCCESS] Step04 done
> WRITE_TARGET: qpon-bigdata-knowledge/04_Data_Model_and_Lifecycle.md
> WRITE_RESULT: UPDATED
> WRITE_BYTES: 30260
> WRITE_SHA256: f84f1b388aded2f86b2b29f140298eeca1cc25f343af0763ae2b233d158eee2b
> NO_CHANGE_REASON: N/A

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件，建立先验认知：
1. qpon-bigdata-knowledge/02_External_Contracts.md — §1 Dubbo 接口清单（这是链路入口）
2. qpon-bigdata-knowledge/03_Downstream_Dependencies.md — §2 实际调用点追踪
3. qpon-bigdata-knowledge/04_Data_Model_and_Lifecycle.md — §3 查询模式矩阵
如有旧文档：qpon-bigdata-knowledge/Legacy_qpon-bigdata_Claims.md — §4 业务链路声称


[Task: 业务编排全量测绘]

### 扫描范围

**区域 A：应用层入口（app 模块）**
- qpon-bigdata-app/src/main/java/**/rpc/ — 全部 RPC 实现类
- 逐文件读取至 EOF

**区域 B：业务编排层（service 模块 core/）**
- qpon-bigdata-service/src/main/java/**/core/ — 全部子包
- 重点扫描：DomainService、BizService、Executor、Handler、Checker、Strategy 等关键类

**区域 C：基础设施层（service 模块 infrastructure/）**
- qpon-bigdata-service/src/main/java/**/infrastructure/ 下的：
  - repository/ — 仓储实现
  - component/ — 组件
  - configuration/ — 配置
- 不需要重新扫描 infrastructure/service/（已在 Step 03 完成）

**区域 D：通用层（service 模块 common/）**
- qpon-bigdata-service/src/main/java/**/common/ — 工具类、通用 DTO、扩展

### 提取任务

#### 1. RPC 入口 → 业务方法映射表
对 app 模块每个 RPC 实现类，提取：
a) 类名 + 实现的 Dubbo 接口
b) 每个方法的调用第一层：该方法调用了 service 层的哪个类的哪个方法
c) 是否有 app 层直接包含业务逻辑（⚠️ DDD 分层穿透）

格式：
| RPC 实现类 | 接口方法 | 调用的 Service 类.方法 | 分层评估 |

#### 2. 核心业务链路深度还原
根据 Step 02 发现的接口，追踪核心业务链路（由 001 根据 Step 02 产出动态注入链路清单）。

**链路输出格式（精简规则）**：
```
[app] 入口类.方法()
  → [core] 关键决策类.方法() — 决策说明（一句话）
  → ... （中间层若无决策点，用省略号合并）
  → [infrastructure/RPC/MQ] 终端操作类.方法() — 操作说明
```

**精简原则**：
- 只保留三层：入口 → 关键决策点 → 终端操作
- 中间的纯转发层（只做参数转换、无分支判断的）用「→ ... →」省略
- 关键决策点：有 if/switch/策略分发/校验链的调用，必须显式列出
- 终端操作：DB 写入 / RPC 调用 / MQ 发送，必须显式列出
- 每条链路不超过 15 行

**必须标注的信息**：
- 分片表写入点（标注 ⚠️分片表写入）
- 外部 RPC 写操作调用点：retries=0 标注「RPC-外部服务名（retries=0）」；retries>0 标注「🔴RPC-外部服务名（retries=N，写操作重复风险）」
- 分布式锁保护点（标注锁 key 模式）
- 一个方法节点同时承担幂等校验和业务执行两种职责时，必须拆成两行分别标注，不允许合并为一行

#### 3. DDD 分层审计汇总
基于以上扫描，输出：
- app 层下沉清单：哪些方法直接包含了业务逻辑（应在 core 层的代码）
- infrastructure 侵入清单：哪些基础设施类直接依赖了 core 层接口
- 分层总体评估：core 层是否保持了领域纯净性

#### 4. 设计模式识别
识别代码中使用的设计模式，标注具体类名和使用场景：
- 策略模式（Strategy）
- 模板方法模式（Template Method）
- 责任链模式（Chain of Responsibility）
- 工厂模式（Factory）
- 其他模式

#### 5. 衍生约束清单
基于本步发现，提炼对后续开发的约束：
| 约束编号 | 约束内容（一句话，可执行） | 代码证据（类名.方法名） | 严重级别 |

约束提炼原则：只从代码事实中衍生；🔴 强制：违反会导致架构问题或线上事故；🟡 建议：增加维护成本。

### 输出要求

**文件一**：在 `qpon-bigdata-knowledge/` 下生成 `05_Business_Orchestration.md`，包含：
- RPC 入口映射表（完整）
- 核心业务链路（精简格式，每条 ≤ 15 行）
- DDD 分层审计汇总
- 设计模式识别
- 衍生约束清单

**文件二（脚本接口，必须产出）**：在 `qpon-bigdata-knowledge/` 下生成 `05_module_manifest.json`。

格式要求：
```json
[
  {"id": "<模块英文id>", "name": "<模块中文名>", "complexity": "<high|medium|low>"}
]
```

规则：
- 模块边界和数量由你根据 RPC 入口映射表和业务链路分析自行决定
- `id` 必须是合法的文件名片段（字母、数字、连字符）
- `complexity` 根据决策点数量判断：高（>15个）/ 中（5-15个）/ 低（<5个）
- 此文件是自动化流水线驱动 Step 08 循环执行的唯一依据，格式必须是合法 JSON

[Constraint - 工业级底线]

**输出格式锁定**：使用以下标题结构
```
### 1. RPC 入口映射表
### 2. 核心业务链路
### 3. DDD 分层审计汇总
### 4. 设计模式识别
### 5. 衍生约束清单
### 6. 旧文档交叉验证摘要（有旧文档时输出，NO_DOCS 时跳过）
```

**第 6 节格式（有旧文档时）**：
只列出差异条目：❌不符 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条链路，其余均已代码验证」。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `qpon-bigdata-app/` 或 `qpon-bigdata-service/` 在工作区内不存在，必须立即停止并输出：`❌ 未在工作区找到 [路径]，无法完成审计。请确认 PROJECT_NAME 与目标项目一致。` 禁止推断替代路径，禁止访问工作区外目录。

**扫描完整性保证**：
- 扫描必须全量：区域 A~D 每个文件逐一读取至 EOF
- 每条业务链路必须追踪到终端操作（DB 写入 / RPC 调用 / MQ 发送）为止
- 行数软上限：05_Business_Orchestration.md ≤ 500 行；超出则拆分为子文件

**专业性底线**：
- 调用链精确到 类名.方法名() 级别，不允许模糊描述
- 中间纯转发层用省略号合并，不展开
- 分层违规必须标注违规类名和具体违规行为
- 衍生约束必须有代码证据支撑，不允许凭空推断

**结尾标准审计闭环**：

> [!SUCCESS] 业务编排全量测绘闭环验证
> - 扫描范围：app/rpc/ [X] 个实现类 + service/core/ [Y] 个子包
> - RPC 入口映射：[X] 个实现类，[Y] 个方法
> - 核心链路：[N] 条链路完整还原至终端操作
> - DDD 分层违规：[X] 处 app 层下沉 / [Y] 处 infrastructure 侵入
> - 设计模式：识别 [X] 种模式的 [Y] 个具体应用
> - 衍生约束：[X] 条（🔴 [Y] 条强制 / 🟡 [Z] 条建议）
> - 05_module_manifest.json：已生成，包含 [X] 个模块
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余 [C] 条已验证（NO_DOCS 时标注 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对异步机制分析有决定性影响的编排事实，如：涉及 MQ/Job 的核心链路节点、补偿触发条件、高频失败场景等]
> - **推演约束 (Constraint)**: [基于编排发现，强制 Step 06 重点审计的异步路径或补偿逻辑]
> - **物理锚点 (Anchors)**: [对应业务链路中涉及异步操作的类名及方法行号]

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
