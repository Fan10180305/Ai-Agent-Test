# Step 08: 业务模块深潜模板

[Role] 业务语义深度解读专家。
你的任务是为 考古执行器逻辑 模块生成业务语义深度解读文档——
不重复 Step 05 的调用链追踪，而是向下钻取业务决策点、扩展机制、失败模式。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。

核心前提：Step 05（05_Business_Orchestration.md）已经完成了：
- RPC 实现类的方法入口映射
- 核心链路的调用链追踪
- 非主线功能清单
- DDD 分层审计和设计模式识别

本步骤不重复 Step 05 的工作，而是以 05 为骨架，向下钻取业务语义。

【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Shell/Python 脚本、配置文件、JSON 契约、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 ai-knowledge-xxx/ 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在所触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

# 0. 核心接力策略（最高执行优先级）

> [!RELAY] 定向审计约束
- **物理事实 (Context)**: 心跳监控 (`_extract_transcript_hint`) 强依赖 `python3`；指挥官响应超时硬编 码为 1800s (L429)；脚本中存在多处 macOS 专有的 `sed -i ''` 写法 (L265)。
- **推演约束 (Constraint)**: 下一步（考古引擎模块 08b）需重点审计各 Prompt 模板中的「意图映射指令」是否能有效规避 NON_JAVA 环境下的路径扫描报错，并核实 `[!SUCCESS]` 摘要提取正则是否足够健壮。
- **物理锚点 (Anchors)**: run-archaeology.sh:L457 (python3), L265 (sed), L429 (timeout)。

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
1. ai-knowledge-knowledge/05_Business_Orchestration.md — 核心链路和调用链
2. ai-knowledge-knowledge/04_Data_Model_and_Lifecycle.md — 数据模型
3. ai-knowledge-knowledge/03_Downstream_Dependencies.md — 下游依赖

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/08b_Module_archaeology.md` ，将其作为「旧假说」参照：
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

[Task: 考古执行器逻辑 模块深度解读]

### 扫描范围

**核心组件清单**：
- run_step, .ai-knowledge/prompts/*.md, gemini CLI (execution logic)

**扫描目标**：
- 逐一读取 Prompt 模板至 EOF，理解其分析意图映射逻辑
- 重点关注：`[!SUCCESS]` 的提取格式要求、工具调用的 approving 机制

### 提取任务

#### A. 模块定位（固定骨架）
#### B. 核心类/组件清单（固定骨架）
#### C. 入口方法（固定骨架）
#### D. 调用链（固定骨架）
#### E. 前序步骤验证（固定骨架）
#### F. 衍生约束清单（固定骨架）
#### G-J. 业务特性章节（开放特性）

[Action]
在 ai-knowledge-knowledge/ 目录下生成 08b_Module_archaeology.md

[Constraint - 工业级底线]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/08b_Module_archaeology.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

## 结尾标准审计闭环

> [!SUCCESS] 考古执行器逻辑 模块深潜闭环验证
> - 扫描范围：run_step + 12 个分析模板
> - 提取结果：[X] 个分析意图映射、[Y] 条衍生约束、[Z] 个业务特性章节
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本模块深潜发现的关键事实]
> - **推演约束 (Constraint)**: [强制下一步重点关注的风险点]
> - **物理锚点 (Anchors)**: [对应文件路径及关键逻辑行号]
