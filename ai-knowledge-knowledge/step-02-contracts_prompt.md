# Step 02: 对外契约全量审计

[Role] API 契约审计师。
你的任务是从 client 模块的 Java 源码中提取本服务对外暴露的全部 Dubbo 接口契约——
接口名、方法签名、入参/出参 DTO、枚举、常量。
这些是本服务对外的"承诺"，改动即为 breaking change，必须逐个登记在案。
你不分析实现逻辑，不读 app/service/dao 模块代码。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。
Step 0 已完成旧文档声称提取（NO_DOCS 时先验层留空）。
Step 01 已完成项目骨架测绘（01_Module_Skeleton_and_Stack.md），确认了子模块结构。
本步骤聚焦 ai-knowledge-client 模块，提取对外契约的完整事实。

已知关键线索（由 001 根据 Step 01 产出动态注入）：
> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 本项目为非 Java 项目，核心能力由 Bash 脚本和 AI Prompts 驱动。对外契约（Step 02）不表现为 RPC 接口，而表现为：1) install.sh 的参数接口；2) run-archaeology.sh 的位置参数；3) 产出的 Markdown/JSON 结构约定。
> - **推演约束 (Constraint)**: Step 02 必须跳过 Java RpcService/Controller 扫描，重点审计 run-archaeology.sh 的输入参数校验逻辑、config.json 的 Schema 约定，以及 05_module_manifest.json 的数据契约。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L82 (STEP_LIST), install.sh:L67 (config.json 生成), ARCHITECTURE.md:§5.1 (manifest 契约说明)。

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
> - **物理事实 (Context)**: 本项目为非 Java 项目，核心能力由 Bash 脚本和 AI Prompts 驱动。对外契约（Step 02）不表现为 RPC 接口，而表现为：1) install.sh 的参数接口；2) run-archaeology.sh 的位置参数；3) 产出的 Markdown/JSON 结构约定。
> - **推演约束 (Constraint)**: Step 02 必须跳过 Java RpcService/Controller 扫描，重点审计 run-archaeology.sh 的输入参数校验逻辑、config.json 的 Schema 约定，以及 05_module_manifest.json 的数据契约。
> - **物理锚点 (Anchors)**: run-archaeology.sh:L82 (STEP_LIST), install.sh:L67 (config.json 生成), ARCHITECTURE.md:§5.1 (manifest 契约说明)。

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
1. ai-knowledge-knowledge/01_Module_Skeleton_and_Stack.md — §5 子模块职责定义
如有旧文档：ai-knowledge-knowledge/Legacy_ai-knowledge_Claims.md — §2 对外接口声称

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/02_External_Contracts.md` ，将其作为「旧假说」参照：
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

[Task: 对外契约全量提取]

请集中算力扫描 ai-knowledge-client 模块的全部 Java 源码，执行以下提取：

### 扫描范围（严格限定）
ai-knowledge-client/src/main/java/ 下所有 .java 文件，逐文件读取至 EOF。

### 提取任务

#### 1. Dubbo 接口清单
- 扫描所有 api/ 目录下的接口定义文件（interface）
- 对每个接口提取：
  a) 接口全限定类名
  b) 所属子包
  c) 全部方法签名（方法名 + 入参类型 + 返回类型）
  d) 方法数量
- 按子包分组呈现

格式：
| 接口名 | 子包 | 方法签名 | 入参 | 返回类型 |

#### 2. DTO/请求/响应对象清单
扫描必须全量（dto/、req/、resp/ 等目录下每个 .java 逐文件读取至 EOF），但**输出按以下规则提炼**：

**字段输出规则**：
- 字段数 ≤ 5 个：全部列出（字段名 + 类型）
- 字段数 6~15 个：只列出前 5 个核心字段 + 「共 N 个字段」
- 字段数 > 15 个：只列出主键/ID 类字段 + 状态类字段 + 「共 N 个字段」

**嵌套 DTO 规则**：
- 作为字段类型出现的其他 DTO 类，只写类名，不展开其字段（在该 DTO 自己的条目中展开）
- 集合类型写 `List<XxxDTO>`，不展开泛型内容

**对每个 DTO 提取**：
a) 类名 + 全限定包路径
b) 所属接口（被哪个 Dubbo 接口的哪个方法引用）
c) 字段列表（按上述规则提炼）
d) 继承基类（如有，写基类名，不展开基类字段）

在本节末尾输出一行汇总：「共 N 个 DTO，分布在 M 个子包中」。

#### 3. 枚举定义清单
- 扫描 enums/ 或散落在各子包中的枚举类
- 对每个枚举提取：
  a) 枚举类名 + 全限定包路径
  b) 全部枚举值（枚举名 + 含义注释，如有）
  c) 被哪些 DTO/接口引用（从类名可推断时注明）

#### 4. 常量定义清单
- 扫描 constant/ 目录
- 对每个常量类提取：
  a) 类名
  b) 全部常量定义（常量名 + 值 + 注释）
- 重点关注 DubboConstants（Dubbo 服务分组、版本等配置）

#### 5. 子包结构全景图
- 列出 client 模块的完整包结构树，标注每个子包的文件数量
- 如有旧文档，标注旧文档未覆盖的新子包（🆕）

#### 6. 接口依赖分析
- 检查 client 模块的 pom.xml，提取它依赖的外部 client JAR
- 如果接口方法的入参/出参引用了外部服务的类型，逐个列出
- 标记为 ⚠️ 契约耦合点

[Action]
在 ai-knowledge-knowledge/ 目录下生成 02_External_Contracts.md

[Constraint - 工业级底线]

**输出格式锁定**：使用以下标题结构
```
### 1. Dubbo 接口清单
### 2. DTO/请求/响应对象清单
### 3. 枚举定义清单
### 4. 常量定义清单
### 5. 子包结构全景图
### 6. 接口依赖与契约耦合分析
### 7. 旧文档交叉验证摘要（有旧文档时输出，NO_DOCS 时跳过）
```

**第 7 节格式（有旧文档时）**：
只列出差异条目：❌不符 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条接口，其余均已代码验证」。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 ai-knowledge-client/src/main/java/ 在工作区内不存在，必须立即停止并输出：`❌ 未在工作区找到 [路径]，无法完成审计。请确认 PROJECT_NAME 与目标项目一致。` 禁止推断替代路径，禁止访问工作区外目录。

**扫描完整性保证**：
- 扫描必须全量：client 模块下每个 .java 文件读取至 EOF
- 输出必须提炼：接口方法全列（不省略）；DTO 字段按上述规则提炼

**专业性底线**：
- 只记录代码事实，不评价接口设计好坏
- 方法签名直接用 Java 语法，不做自然语言转述
- DTO 字段按代码中的声明顺序列出，不重排

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/02_External_Contracts.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

约束：
1) WRITE_RESULT=UPDATED 时，WRITE_BYTES 与 WRITE_SHA256 必须基于写入后的真实文件；
2) WRITE_RESULT=NO_CHANGE 时，必须给出 NO_CHANGE_REASON，禁止留空；
3) 若无法确认以上字段的真实性，必须显式宣告失败，禁止输出伪造回执。

## 结尾标准审计闭环

```
> [!SUCCESS] 对外契约测绘闭环验证
> - 扫描范围：ai-knowledge-client/src/main/java/ 下全部 [N] 个 .java 文件
> - 提取结果：[X] 个 Dubbo 接口、[Y] 个方法、[Z] 个 DTO、[W] 个枚举、[V] 个常量类
> - 子包覆盖：[列出所有发现的子包名]
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余 [C] 条已验证（NO_DOCS 时标注 N/A）
> - EOF 状态：已确认遍历 [N] 个 .java 文件至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对下一步下游依赖分析有决定性影响的契约事实，如：核心接口方法、高频调用的 DTO 类型等]
> - **推演约束 (Constraint)**: [基于契约发现，强制 Step 03 重点追踪的具体调用点或依赖关系]
> - **物理锚点 (Anchors)**: [对应接口文件路径及方法行号]
```
