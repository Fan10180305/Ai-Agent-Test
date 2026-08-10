# Step Audit: Rules 合规性审计

[Role] 知识库质量审计师。
你的任务是对 .cursor/rules/ai-knowledge.mdc 以及 .gemini/rules/ai-knowledge.md 文件进行合规性审计，
确保其满足知识库构建的三大目的：意图路由、防御性编码红线、知识库双写。

[Context]
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。
Step Final 已经生成了 00_Master_Catalog.md 和 ai-knowledge.mdc。

本步骤是知识库的最终质量门禁，确保生成的规则文件能够真正约束 AI 的行为。

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
> - **物理事实 (Context)**: 确认了该模块通过 _ensure_protocol (L205) 实现了对 AI 认知的物理劫持，并记录了 sed -i '' (L265) 等多处严重的平台依赖性硬伤。
> - **推演约束 (Constraint)**: 下一步收官阶段需重点核实 00_Master_Catalog 是否正确链接了 08a/b/c 三个子模块的深潜报告，并确保 C-INF-001 等物理约束被同步至全局规则审计中。
> - **物理锚点 (Anchors)**: scripts/knowledge-archaeology/run-archaeology.sh L101 (CMD Path), L265 (Sed), L525 (Trap)。

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
请静默读取以下文件：
1. .cursor/rules/ai-knowledge.mdc — 待审计的 Cursor 规则文件
2. .gemini/rules/ai-knowledge.md — 待审计的 Antigravity 规则文件
3. ai-knowledge-knowledge/00_Master_Catalog.md — 总目录

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/Rules_Audit_Report.md` ，将其作为「旧假说」参照：
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

[Task: Rules 合规性审计]

### 审计清单 (NON_JAVA 适配)

对 ai-knowledge.mdc 文件执行以下审计：

#### 目的一：意图路由
- 检查场景分流是否包含本项目的核心脚本与 Prompt 开发场景

#### 目的二：防御性编码红线
- 检查是否包含：set -euo pipefail, 禁止 2>/dev/null, 路径锚定, API Key 保护, macOS Sed 禁止

#### 目的三：知识库双写
- 检查触发条件是否包含：修改调度器, 脚本参数, 模板变量, 核心架构变更

[Action]
1. 生成审计报告：ai-knowledge-knowledge/Rules_Audit_Report.md
2. 如有未通过项，自动应用补丁到两个规则文件中
3. 重新审计，直到 9/9 通过

[Constraint - 工业级底线]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/Rules_Audit_Report.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

## 结尾标准审计闭环

> [!SUCCESS] Rules 审计闭环验证
> - 审计范围：ai-knowledge.mdc 文件
> - 审计结果：[X]/9 通过
> - 补丁应用：[Y] 个补丁已应用
> - 最终状态：9/9 通过 ✅
> - EOF 状态：已确认遍历至最后一行，无静默截断
