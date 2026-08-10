# Step 03: 下游依赖全量测绘

## 角色定义
代码考古学家 + 依赖拓扑分析师。你的任务是从 `DubboReferenceConfig`、`infrastructure/service/` 下的所有网关类、以及全局 `@DubboReference` 注解扫描中，还原本服务的完整下游依赖图。你不推测调用意图，不做"是否合理"的评判，只忠实记录代码中的事实。

## 上下文
我们正在为 ai-knowledge（ai-knowledge）构建 AI 可加载的项目知识库。本步骤聚焦下游依赖：Dubbo 消费者、HTTP 调用、其他协议调用。

【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Shell/Python 脚本、配置文件、JSON 契约、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 ai-knowledge-xxx/ 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在而触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

## 最高指令挂载
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典（位于 `.cursor/rules/collaboration-protocol.mdc` 或 `.gemini/rules/collaboration-protocol.md` 根据环境加载）。

# 0. 核心接力策略（最高执行优先级）

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: run-archaeology.sh 通过 STEP_LIST (L82) 驱动 8 步分析，其物理媒介为 ${OUTPUT_DIR}/.tmp/next-prompt.md。核心依赖为 jq, sed (BSD), python3。
> - **推演约束 (Constraint)**: Step 03 必须重点分析脚本对上述二进制工具的调用频率及异常处理逻辑，特别是 python3 在心跳监控中的不可替代性。
> - **物理锚点**: scripts/knowledge-archaeology/run-archaeology.sh:L82 (STEP_LIST), L420 (python3 心跳解析), install.sh:L94 (config.json 生成)。

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

## 先验知识注入
请静默读取以下文件，建立先验认知：
1. ai-knowledge-knowledge/01_Module_Skeleton_and_Stack.md — §5 子模块职责定义
2. ai-knowledge-knowledge/02_External_Contracts.md
如有旧文档：ai-knowledge-knowledge/Legacy_ai-knowledge_Claims.md — §2.1 下游依赖声称

---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `ai-knowledge-knowledge/03_Downstream_Dependencies.md` ，将其作为「旧假说」参照：
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

## 任务：下游依赖全量测绘

### 扫描顺序（严格按此顺序执行，不允许跳步）

**Step A：定位核心依赖配置**
- 在 NON_JAVA 模式下，扫描核心脚本 (run-archaeology.sh, install.sh) 及其引用的配置文件 (.ai-knowledge/config.json)
- 提取：使用的二进制工具 (gemini, jq, sed, python3)、外部 API (Gemini API)
- 对每个依赖提取：版本要求、配置来源、调用点

**Step B：扫描基础设施/脚本调用**
- 列出 scripts/ 目录下的完整文件树
- 逐个读取每个 Shell/Python 脚本
- 记录：对二进制工具的调用、对外部 API 的请求、调用条件 (if 分支)

**Step C：全局补充搜索**
- 搜索所有 `command -v` 或工具检查逻辑
- 搜索所有对 `gemini` CLI 的调用点
- 搜索所有对 `python3` 的子进程孵化逻辑

**Step D：调用点逆向追踪**
- 对确定的每个外部工具/API，全局搜索其在业务逻辑中的引用
- 按重度、中度、轻度依赖分类

**Step E：异步/外挂层追踪**
- 追踪心跳监控 (python3) 与主进程 (bash) 的通信链路
- 记录异步补偿机制

---

## 提取任务

### 1. 外部工具/API 消费者全量清单

| 序号 | 依赖项名称 | 角色/用途 | 来源 (PATH/API) | 超时/限制 | 配置来源 |
|------|----------|----------|----------------|----------|----------|

### 2. 实际调用点追踪

对每个核心依赖独立成节，列出调用场景。

### 3. 配置与容错审计

**3.1 全局环境配置**
- 提取：全局超时设置、重试次数

**3.2 熔断降级**：检查脚本中的错误捕获逻辑 (set -e, || exit 1)

### 4. 其他协议调用清单 (如 Gemini API 交互协议)

### 5. 外部依赖拓扑图

### 6. Step 01 遗漏追踪

### 7. 旧文档交叉验证摘要

---

## Action
在 `ai-knowledge-knowledge/` 目录下生成 `03_Downstream_Dependencies.md`

---

## Constraint — 工业级底线

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。

**专业性底线**：
- 只记录代码事实，不评价设计好坏
- **禁止**出现"原因推测"等主观评判语句

---

## 结尾标准审计闭环

> [!SUCCESS] 下游依赖测绘闭环验证
> - 扫描范围：核心脚本 + 配置文件 + 全局搜索
> - 提取结果：[X] 个外部工具/API、[Y] 个关键调用点
> - 幽灵依赖：[N] 个（声明但未调用）
> - 超时配置：全局默认来自 [配置文件路径]，值为 [T]
> - Step 01 遗漏追踪：已确认 [X] 项
> - 旧文档验证：[A] 项已验证 / [B] 项不符 / [C] 项新发现（NO_DOCS 时写 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对数据模型分析有决定性影响的依赖事实]
> - **推演约束 (Constraint)**: [基于下游依赖发现，强制 Step 04 重点关注的数据映射或状态流转细节]
> - **物理锚点 (Anchors)**: [对应依赖配置文件路径及行号]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: ai-knowledge-knowledge/03_Downstream_Dependencies.md
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>
