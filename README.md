# 知识库考古流水线——架构全景文档（开源）

> **⚠️ 平台声明：当前版本仅支持 macOS。**
> Windows 的 Shell 环境差异太大，适配成本过高，我比较忙，也比较懒。
> 原理是通用的——如果你在 Windows 或 Linux 上，完全可以参考本文档自行适配。欢迎 PR。

---

## 目录

1. [项目是什么，解决什么问题](#一项目是什么解决什么问题)
2. [快速开始](#二快速开始)
3. [流水线全景：贪吃蛇架构](#三流水线全景贪吃蛇架构)
4. [产出物说明](#四产出物说明)
5. [关键设计决策](#五关键设计决策)
6. [仓库文件说明](#六仓库文件说明)
7. [实现方案 A：Gemini CLI 原生版](#七实现方案-agemini-cli-原生版)
8. [实现方案 B：bash + Cursor Agent CLI 版](#八实现方案-bbash--cursor-agent-cli-版)
9. [设计亮点与取舍](#九设计亮点与取舍)
10. [参与贡献](#十参与贡献)

> 本项目源于实践：[让 AI 真正理解你的代码：从静态文档到活知识库的实践](./让AI真正理解你的代码：从静态文档到活知识库的实践.md) 是本工具的理论背景与方法论原文，建议在使用前阅读。

---

## 一、项目是什么，解决什么问题

### 背景

接手一个陌生代码库时，AI 编程助手（Cursor、Gemini CLI 等）的实际能力取决于它能「看到」多少有效上下文。现实中的困境：

- 代码量大时，AI 每次只能看到有限的上下文窗口，容易产生幻觉
- 旧项目有过时文档、隐含的架构约定、未记录的技术债，AI 无法自动感知
- 工程师接手新项目、排查线上问题、评估需求影响时，都需要反复回答同一批问题：模块边界在哪？接口契约是什么？数据怎么流转？

### 这个项目做什么

**知识库考古流水线**是一个自动化工具，针对任意代码仓库，通过一条串行的 AI 分析流水线，同时产出两类文件：

1. **知识库文档**（Markdown）：将代码库中隐含的架构约定、接口契约、业务决策点等提炼为结构化文档
2. **AI 行为规则**（`.mdc` / `.gemini/rules/`）：强制 AI 在每次代码变更时同步更新知识库，形成「代码变 → 知识库变」的闭环

这两类产出共同构成一个**活的知识库体系**——知识库不是一次性生成后静置的文档，而是通过规则文件强制与代码库保持同步，不随迭代过期。

核心价值：

- **AI 接手即用**：规则文件注入 Cursor / Gemini CLI 后，AI 在回答任何问题前已具备项目全局视野，并按场景路由到对应知识文件
- **人类也能看**：每个知识库文档都是可读的 Markdown，工程师可以直接阅读
- **自我维护**：双写协议规则确保每次功能开发同步维护知识库，避免文档腐烂
- **覆盖三类核心场景**：排障定位、需求交付影响评估、日常运维

### 核心挑战与解法

| 挑战 | 解法 | 详见 |
|------|------|------|
| 单次 AI 分析容易幻觉、遗漏 | 流水线串行执行，每步聚焦一个维度，前序产出作为后续步骤的交叉验证线索 | §3.1 贪吃蛇架构 |
| 不同项目模块数量、边界不同 | Step 05 的 AI 自决模块清单（`05_module_manifest.json`）驱动后续动态循环，无需人工配置 | §5.1 Step 05 双产出 |
| AI 在长会话中容易身份漂移、取巧 | 每个执行步骤使用独立的全新 AI 会话，token 预算重置，无历史污染 | §5.4 物理隔离；§7.2（Gemini 版）；§8.2（bash 版） |
| 无法感知 AI 是否真正完成任务 | 每步强制输出 `[!SUCCESS]` 闭环验证块，未出现则流水线硬中断 | §5.5 质量门禁 |
| 旧文档与代码事实可能矛盾 | Step 0 单独提取旧文档声称，后续步骤逐一交叉验证，显式标注「声称」vs「代码事实」 | §4 产出物说明 |


---

## 二、快速开始

> **前置条件**：必须先在目标项目根目录执行 `install.sh` 完成安装，详见 `USAGE.md`。

### 方式 A：Gemini CLI（推荐）

```bash
cd /path/to/your-project
gemini --yolo   # 或缩写 gemini -y
```

在对话框输入（支持多种旧文档模式）：

```
# 无旧文档
运行考古流水线 旧文档=无

# 使用项目内 old-readme/ 目录
运行考古流水线 旧文档=有

# 指定一个或多个路径（目录或文件，空格分隔）
运行考古流水线 旧文档="docs/old-wiki docs/spec.md README.md"
```

### 方式 B：bash 脚本

```bash
cd /path/to/your-project

# 无旧文档
bash /path/to/ai-knowledge/scripts/knowledge-archaeology/run-archaeology.sh 签到中心

# 指定一个或多个旧文档路径（位置参数 2+）
bash /path/to/ai-knowledge/scripts/knowledge-archaeology/run-archaeology.sh 签到中心 docs/old-wiki docs/spec.md README.md
```

流水线运行完成后，在项目根目录生成 `{项目名}-knowledge/` 知识库目录。

**旧文档路径收集规则**（Legacy 路径指定时自动执行）：

- **目录**：遍历直接子文件，按 `<目录前缀>__<文件名>` 命名复制到 `old-readme/`（如 `docs-legacy__design.md`），保留层级上下文，避免重名覆盖
- **单文件**：保留原文件名；重名时追加 `_2`、`_3` 后缀
- **跳过**：0 字节文件、非 `.md`/`.txt` 扩展名（输出 WARN）
- **路径不存在** → 报错退出；**收集后有效文件为 0** → 自动切换 NO_DOCS 模式

---

## 三、流水线全景：贪吃蛇架构

### 3.1 为什么叫「贪吃蛇」

每一步分析的产出，都作为下一步的输入（先验知识注入）。流水线像贪吃蛇一样，边走边把已发现的事实串联进来，越到后面的步骤，视野越完整、交叉验证越充分。

**术语说明**：流水线产出 **11 类知识文件**（Step 0 ~ Final + Audit），指挥官执行 **15 个操作节点**（初始化 3 步 + 主链 8 步 + 模块循环 N 步 + 收官 2 步）。两者描述同一流水线，前者是产出维度，后者是操作维度。

```
[协作元协议] — 贯穿所有步骤的 AI 行为约束层
      ‖
Step 0   旧文档声称提取
      ↓  声称清单 → 后续步骤的交叉验证 checklist
Step 01  模块骨架与技术栈
      ↓  模块边界、技术债 Red Flags
Step 02  对外契约
      ↓  接口清单、DTO 定义
Step 03  下游依赖
      ↓  幽灵依赖、超时配置
Step 04  数据模型与生命周期
      ↓  表结构、分库分表策略
Step 05  业务编排                          ← 关键节点
      ↓  核心链路 + 05_module_manifest.json（驱动后续动态循环）
Step 06  异步机制与补偿
      ↓  Job、MQ、分布式锁、补偿流程
Step 07  配置与可观测性
      ↓  配置项、缓存、错误码
Step 08a 模块深潜（模块一）               ← 动态循环，N 由 Step 05 自决
Step 08b 模块深潜（模块二）
  ...    （最多 26 个模块，a-z 后缀）
Final    00_Master_Catalog 组装 + 规则文件生成
Audit    Rules 合规性审计与补丁
```

### 3.2 三层架构

理解三层架构，先看人工模式是怎么跑的——自动化方案是它的直接复现。

**人工模式的操作循环**（每步重复约 9 次）：

```
人类打开 001 会话
  → 把上一步的执行摘要粘贴进去
  → 询问「下一步怎么做？」
  → 001 生成下一步 prompt
  → 人类手动新开会话，粘贴 prompt 执行
  → 执行完成，人类回到 001 汇报结果
  → 循环 ~9 次
```

人工模式中人类扮演三个角色：

| 人工角色 | 自动化替代 |
|---------|----------|
| **指挥官**：记住全局目标，决定每步重点 | 001 指挥官 AI（唯一持续会话） |
| **胶水层**：在 001 和执行会话之间手动传递 prompt 和结果 | 编排层（bash 脚本 / SKILL 状态机） |
| **质检员**：识别产出质量问题并实时纠偏 | `[!SUCCESS]` 门禁（硬中断） |

**三层架构图**：

```
  prompts/ 模板库（已固化的结构框架）
          │
          │ 读对应模板
          ▼
  ┌─────────────────────────────────────────────┐ ◄─── 每步结果摘要（循环输入）
  │         001 指挥官 AI（持续会话）             │
  │  模板框架 + 前序发现 → 动态生成 prompt        │
  │  → 写入 next-prompt.md                      │
  └──────────────────┬──────────────────────────┘
                     │ next-prompt.md（文件传递，防转义污染）
                     ▼
  ┌─────────────────────────────────────────────┐
  │              编排层（调度器）                  │
  │  cat → 启动执行 Agent → stdin 传入 prompt    │
  │  → 提取 [!SUCCESS] 摘要 ────────────────────→ 回传 001（循环）
  └──────────────────┬──────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────┐
  │        执行 Agent（每步全新，物理隔离）        │
  │    读代码 → 分析 → 写知识库产出文件            │
  │    Token 预算独立，执行完即销毁               │
  └─────────────────────────────────────────────┘
```

**关键传递机制**：Prompt 通过文件（`next-prompt.md`）传递而非命令行拼接，彻底避免 shell 转义字符污染 Prompt 内容。摘要提取通过 `grep '[!SUCCESS]'` 精准定位，不读取完整日志（防止指挥官 context 膨胀）。

### 3.3 协作元协议

`collaboration-protocol.md` 是贯穿所有步骤的**元约束层**，每步 Prompt 开头强制挂载，作用：

- 防止 AI 附和用户期望（批判性独立性要求）
- 拦截 AI 取巧（禁止声称「已完成」而不输出内容）
- 防止身份漂移（执行 Agent 不得越权扮演指挥官）
- 技术壁垒透明化（遇到无法确认的事实必须明确标注）

流水线启动时自动将协议复制到 `.cursor/rules/` 和 `.gemini/rules/` 两端。若目标文件已存在且内容不同，输出 WARN 但不覆盖（避免覆盖用户本地定制）。

---

## 四、产出物说明

流水线完成后，在项目根目录生成 `{项目名}-knowledge/` 目录：

```
{项目名}-knowledge/
├── 00_Master_Catalog.md          # 全局索引 + 场景路由表（AI 的入口文件）
├── Legacy_{项目名}_Claims.md     # 旧文档声称清单（供后续步骤交叉验证）
├── 01_Module_Skeleton_and_Stack.md  # 模块依赖、技术栈、技术债 Red Flags
├── 02_External_Contracts.md      # 对外接口契约（Dubbo/REST/gRPC 等）
├── 03_Downstream_Dependencies.md # 下游依赖、幽灵依赖、超时配置
├── 04_Data_Model_and_Lifecycle.md # 数据模型、表结构、分库分表
├── 05_Business_Orchestration.md  # 核心业务链路、DDD 分层审计
├── 05_module_manifest.json       # 模块清单（机器接口，驱动 Step 08 循环）
├── 06_Async_Jobs_and_Compensation.md # 异步 Job、MQ、补偿机制、分布式锁
├── 07_Config_and_Observability.md # 配置项、缓存、错误码、监控
├── 08a_Module_{模块一}.md        # 模块深潜：业务决策点地图
├── 08b_Module_{模块二}.md
├── ... (08c ~ 08z，数量由 Step 05 决定)
├── Rules_Audit_Report.md         # 规则文件合规性审计报告
├── .logs/
│   ├── {timestamp}/              # 每次运行的完整日志
│   │   ├── pipeline.log          # 主流程日志
│   │   ├── step-01-skeleton.log  # 每步的 Agent 执行输出
│   │   ├── step-01-skeleton.heartbeat.log  # 心跳监控（sh 版）
│   │   └── ...
│   └── latest -> {timestamp}     # 软链，始终指向最新一轮
└── .tmp/
    └── next-prompt.md            # 指挥官写入、执行 Agent 读取的 Prompt 中转文件
```

### 产出清单与目标映射

| 步骤 | 产出文件 | 核心内容示例 | 支撑场景 |
|------|---------|------------|----------|
| 前置 | `.cursor/rules/collaboration-protocol.mdc`<br>`.gemini/rules/collaboration-protocol.md` | AI 行为约束（批判性独立性、拦截取巧） | 保证所有步骤的产出质量 |
| Step 0 | `Legacy_{项目名}_Claims.md` | 旧文档声称清单，用于交叉验证 | 为后续步骤提供验真 checklist |
| Step 01 | `01_Module_Skeleton_and_Stack.md` | 模块依赖、技术栈、Red Flags（技术债） | **排障**：定位架构腐化点；**需求**：理解模块边界 |
| Step 02 | `02_External_Contracts.md` | 对外接口、方法清单、DTO、契约耦合点 | **需求**：新增接口时避免破坏契约；**排障**：接口变更影响分析 |
| Step 03 | `03_Downstream_Dependencies.md` | 下游依赖、幽灵依赖、超时配置 | **排障**：下游调用失败定位；**运维**：超时配置调优 |
| Step 04 | `04_Data_Model_and_Lifecycle.md` | 实体、表结构、分库分表策略 | **排障**：数据异常定位；**需求**：新增表/字段；**运维**：分表规则 |
| Step 05 | `05_Business_Orchestration.md`<br>`05_module_manifest.json` | 核心链路、RPC 入口、DDD 分层审计；模块清单（驱动 Step 08 动态循环） | **排障**：业务流程定位；**需求**：新增业务功能的插入点 |
| Step 06 | `06_Async_Jobs_and_Compensation.md` | Job 清单、MQ、补偿流程、分布式锁点 | **排障**：异步任务失败定位；**运维**：Job 调度管理 |
| Step 07 | `07_Config_and_Observability.md` | 配置项、缓存点、错误码、监控切面 | **运维**：配置变更、缓存策略；**排障**：错误码定位 |
| Step 08 × N | `08{a-z}_Module_{名称}.md` | 业务决策点地图、特性章节（数量由 Step 05 决定） | **排障**：业务逻辑细节定位；**需求**：扩展点识别 |
| Final | `00_Master_Catalog.md` | 全局索引、场景路由表、接手必知清单 | **所有场景**：AI 的入口文件，按场景路由 |
| Final | `{项目名}.mdc`<br>`.gemini/rules/{项目名}.md` | 意图路由、防御性编码红线（10+ 条）、知识库双写协议 | **所有场景**：AI 行为规范 + 知识库保活机制 |
| Audit | `Rules_Audit_Report.md` | 规则文件合规性审计结果、补丁文本 | 确保规则文件质量（同时对 Cursor 和 Gemini CLI 两端规则文件做 9 项合规检查并双端打补丁） |

### 知识库的使用方式

生成完成后，将 `00_Master_Catalog.md` 加载为 AI 规则的入口，AI 在回答问题时会按场景路由到对应文件：

- **排障场景**：可观测性（07）→ 业务编排（05）→ 模块深潜（08x）→ 异步机制（06）
- **需求交付场景**：业务编排（05）→ 契约（02）→ 数据模型（04）→ 模块深潜（08x）
- **运维场景**：配置（07）→ 异步机制（06）→ 数据模型（04）

**知识库保活（双写协议）**：规则文件中内置的双写协议表要求 AI 在每次代码变更时判断是否需要同步更新对应的知识库文件，并输出变更 Diff。这是知识库「活」的机制核心。

---

## 五、关键设计决策

### 5.1 Step 05 双产出：静态流水线到动态流水线的转折点

Step 05 是流水线中唯一有「机器接口」产出的步骤，必须同时生成两个文件：

- `05_Business_Orchestration.md`：供人和 AI 阅读的知识文档
- `05_module_manifest.json`：供编排脚本读取的 JSON 机器接口

```json
[
  {"id": "signin",         "name": "签到模块",   "complexity": "high"},
  {"id": "multiple-order", "name": "多单任务模块", "complexity": "high"},
  {"id": "lottery",        "name": "抽奖模块",   "complexity": "medium"}
]
```

**为什么这是关键设计**：没有这个文件，Step 08 只能硬编码模块列表（静态流水线，每个新项目都需要人工配置）。有了它，编排脚本直接读取 JSON 循环，模块数量和边界完全由 AI 在 Step 05 中自决，同一套脚本可以无修改地适配任意项目。

### 5.2 Step 08 固定骨架 + 开放特性

每个项目的业务模块数量不同、边界不同，但知识库需要对所有模块回答同一批基础问题，同时又要聚焦各模块最关键的特性。解法是「固定骨架 + 开放特性」：

- **固定骨架（A~F 节）**：所有模块必须输出的基础章节——模块定位、核心类清单、主要入口方法、典型调用链、前序验证逻辑、衍生约束。保证可比性和可检索性。
- **开放特性（G~J 节）**：由执行 Agent 根据代码特点自行决定，不同模块完全不同。这是「让 AI 判断什么值得深挖」而非人工指定。

`{{module_core_classes}}` 占位符由指挥官在启动每个 Step 08 子进程前按以下 4 步提炼后注入，禁止空置或虚构：

1. `read_file` 读取 `05_Business_Orchestration.md`
2. 定位该模块 ID 对应的章节（搜索包含 `module_id` 或模块名的标题行及其下方内容）
3. 从该节中提炼核心类清单：提取所有以 `类名.方法名()` 或 `` `ClassName` `` 形式出现的类名，去重后拼接为多行文本
4. 将提炼结果替换占位符；若该模块在 05 文档中无对应章节，显式写入「未在 05_Business_Orchestration.md 中找到该模块的核心类描述」，不跳过、不虚构

### 5.3 001 指挥官的中心化编排

指挥官是整条流水线中**唯一持续运行的 AI 会话**，承担两个核心职责：

**职责一：结构保证**

指挥官不从零生成 Prompt，而是以固化的模板为框架，只调整「先验知识注入」和「任务」两个动态层。其余六层（角色定义、最高指令挂载、约束条件、审计闭环等）原样保留。这确保无论跑什么项目，执行 Agent 都不会遗漏质量要素。

**职责二：认知接力**

每步完成后，指挥官从日志中提取 `[!SUCCESS]` 摘要（≤25 行），注入到下一步的「先验知识注入」层。前序发现中的异常（如幽灵依赖、契约耦合点）会在后续步骤中成为专项核查线索，而不是被遗忘。

**指挥官 context 保护**：指挥官禁止直接读取完整执行日志（单步日志可达 2000+ 行，36 步累计将超出百万 token 上限）。所有摘要提取通过 `grep -A 20 '[!SUCCESS]'` 精准定位，每步注入不超过 25 行。

### 5.4 独立会话 / 物理隔离的执行者

每个执行 Agent 是一个全新的、无历史的 AI 会话。设计意图：

- **幻觉隔离**：多步累积上下文是 AI 产生幻觉和漂移的主要来源。全新会话彻底切断这条路径。
- **Token 预算独立**：每步的复杂度不同，独立预算避免前面步骤"烧完"后续步骤的可用 token。
- **纯净分析**：执行 Agent 只看当前步骤的 Prompt（含指挥官注入的前序摘要），不受无关历史干扰。

Prompt 通过文件（`next-prompt.md`）传递而非命令行参数拼接，避免 shell 转义字符污染 Prompt 内容。

### 5.5 质量门禁：[!SUCCESS] 闭环

质量门禁完全由 Prompt 驱动，不依赖外部校验脚本：

每个模板的「约束条件」层要求执行 Agent 在完成分析后，必须在响应末尾输出标准的 `[!SUCCESS]` 验证块：

```markdown
> [!SUCCESS] 步骤验证摘要
> - KEY_FINDINGS: [核心发现]
> - FILE_PRODUCED: [文件名]
> - NEXT_STEP_HINT: [给指挥官的建议]
```

编排层检测到日志中不含 `[!SUCCESS]` 块时，流水线**硬中断**，不允许用兜底摘要继续执行下一步。

**Stdout 强制指令机制**：指挥官在将每步 Prompt 写入 `next-prompt.md` 前，必须在末尾统一追加以下标准指令：

```
重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。
```

这确保 `[!SUCCESS]` 块同时出现在日志文件（被重定向）和 stdout，使 `grep` 提取可靠命中。没有这条指令，执行 Agent 可能只把验证块写入产出文件而不输出到 stdout，导致门禁误判为失败。

**为什么不允许跳过失败步骤**：认知接力链（每步摘要注入下一步）是知识库质量的核心约束。跳过某步会导致后续步骤收到过期摘要，形成静默断链——比显式失败更危险。


| 门禁检查项                     | 类型  | 写入位置                     |
| ------------------------- | --- | ------------------------ |
| EOF 完整性（`[!SUCCESS]` 块存在） | 硬性  | 每个模板的「约束条件」层             |
| 衍生约束存在                    | 硬性  | Step 06/07/08 模板的「输出要求」层 |
| 模块清单合法 JSON               | 硬性  | Step 05 模板的「输出要求」层       |
| 产出行数 ≤ 800                | 软性  | 每个模板的「约束条件」层             |


### 5.6 边界条件防护


| 风险点            | 防护机制                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------ |
| 无旧文档（全新项目）     | Step 0 探测到 `old-readme/` 为空时，输出含 `LEGACY_STATUS=NO_DOCS` 的 placeholder，后续步骤自动略去旧文档交叉验证层，全流程无人工介入 |
| Step 08 模块数不确定 | 编排层读取 `05_module_manifest.json` 动态循环，模块数由 AI 自决                                                  |
| 知识漂移           | Final assembly 阶段交叉验证各步产出的数量指标（模块数/接口数/依赖数）与前序步骤是否一致                                             |
| 流水线中断（设计中）     | 每步完成后写 checkpoint.json，重启时可从断点续跑；指挥官会话服务端持久化，resume 后上下文完整                                       |
| 非 Java 项目      | Gemini CLI 版：结构探测识别到非 Maven 项目后，在 Prompt 中注入语义推断说明，执行 Agent 将 Java 特有扫描节的分析意图映射到等价物，不触发熔断        |
| Prompt 转义污染    | Prompt 必须通过 `write_file`/文件写入后用管道传入，禁止拼接到 Shell 命令里                                              |
| 占位符残留          | 变量替换后下发前必须全量核查，禁止输出含 `{{...}}` 的 Prompt                                                          |


---

## 六、仓库文件说明

```
ai-knowledge/
├── install.sh                          # 安装脚本：将工具复制到目标项目
├── uninstall.sh                        # 卸载脚本
├── USAGE.md                            # 安装 + 使用完整说明
├── scripts/knowledge-archaeology/
│   ├── ARCHITECTURE.md                 # 本文档：流水线架构全景
│   ├── run-archaeology.sh              # bash + Cursor Agent CLI 版主编排脚本
│   ├── collaboration-protocol.md       # 协作元协议源文件
│   ├── prompts/                        # Prompt 模板库（11 个模板）
│   │   ├── README.md
│   │   ├── step-0-legacy.md            # 旧文档声称提取
│   │   ├── step-01-skeleton.md         # 模块骨架与技术栈
│   │   ├── step-02-contracts.md        # 对外契约
│   │   ├── step-03-downstream.md       # 下游依赖
│   │   ├── step-04-data-model.md       # 数据模型
│   │   ├── step-05-orchestration.md    # 业务编排（含 manifest 产出要求）
│   │   ├── step-06-async.md            # 异步机制与补偿
│   │   ├── step-07-config.md           # 配置与可观测性
│   │   ├── step-08-module-template.md  # 模块深潜模板（固定骨架 + 开放特性）
│   │   ├── step-final-assembly.md      # 总目录组装与规则生成
│   │   └── step-audit-rules.md         # Rules 合规性审计
│   └── test/                           # TDD 测试套件（R1~R15）
│       ├── run-tests.sh
│       ├── mock-cursor.sh
│       └── fixtures/
└── .gemini/skills/archaeology-commander/
    └── SKILL.md                        # Gemini CLI 版指挥官 SKILL（核心实现）
```

**Prompt 模板的统一结构（8 层骨架）**：

所有 11 个模板遵循统一的层次，保证结构不因项目而丢失：

```
角色定义      → 约束执行 Agent 的身份和视角
上下文        → 项目名、输出目录等变量注入
最高指令挂载  → 强制读取协作元协议（每步必有）
先验知识注入  → 前序步骤的 [!SUCCESS] 摘要（指挥官动态填入）
任务          → 本步骤的扫描范围和输出格式（步骤间差异最大的部分）
约束          → EOF 防截断、行数上限、敏感信息脱敏
审计闭环      → [!SUCCESS] 验证块格式要求
```

001 指挥官只调整「先验知识注入」和「任务」，其余五层原样保留。

---

## 七、实现方案 A：Gemini CLI 原生版

### 7.0 为什么选择 Gemini CLI？——因为穷，而且抠...

> 引用自官方仓库 [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

| 特性 | 说明 |
|------|------|
| 🎯 **免费额度** | 个人 Google 账号每分钟 60 次请求、每天 1000 次请求，零成本跑完整条流水线 |
| 🧠 **强力模型** | 接入 Gemini 3 系列，推理能力更强，支持 100 万 token 超长上下文窗口 |
| 🔧 **内置工具** | 原生支持 Google 搜索、文件读写、Shell 命令、网页抓取，无需额外配置 |
| 🔌 **可扩展** | 支持 MCP（模型上下文协议），可自定义集成外部工具 |
| 💻 **终端优先** | 专为命令行开发者设计，天然契合流水线自动化场景 |
| 🛡️ **开源** | Apache 2.0 协议，可自由使用、修改和分发 |

本流水线正是基于免费额度设计的——整条流水线（约 14 个步骤）在日常使用中完全在免费配额内跑完，**不产生任何 API 费用**。

### 7.1 方案概述

- **指挥官载体**：加载了 `archaeology-commander` SKILL 的 Gemini CLI 交互式会话
- **执行 Agent**：由指挥官通过 `run_shell_command` 孵化的 OS 级子进程
- **编排方式**：SKILL 内置完整的状态机逻辑，指挥官自主驱动整条流水线
- **平台要求**：macOS / Linux，需 Gemini CLI 0.33.2+、jq

### 7.2 执行 Agent 的物理隔离

```bash
# MODEL 为空时不加 --model，使用账号默认模型（避免不可用模型名导致 404）
if [ -z "${MODEL}" ]; then
  cat ${NEXT_PROMPT} | gemini -p '' --yolo > ${LOG_DIR}/{step_name}.log 2>&1
else
  cat ${NEXT_PROMPT} | gemini -p '' --yolo --model ${MODEL} > ${LOG_DIR}/{step_name}.log 2>&1
fi
```

关键参数：

- **`-p ''`**：headless 模式，无交互提示，Prompt 完全由 stdin 管道传入
- **`--yolo`**：`-p` 模式下 CLI 将 `nonInteractive=true` 注入 PolicyEngine。在此模式下，任何未被显式 ALLOW 的工具调用，`ASK_USER` 决策自动降级为 `DENY`，工具调用静默失败。`--yolo` 直接设置 `approvalMode=YOLO`，PolicyEngine 在 YOLO 分支遇到无匹配规则时直接返回 `ALLOW`，不经过 `applyNonInteractiveMode` 降级路径。因此 **`--yolo` 是必须的**，省略会导致所有文件读写操作静默失败，执行 Agent 无法产出任何文件。
- **无 `--resume`**：子进程调用严禁带 `-r`/`--resume`，每步从零开始，Token 预算完全重置，无历史污染
- **timeout**：`run_shell_command` 的 timeout 必须设为 **1800000ms（30 分钟）**，以适应大型项目深度分析。Gemini CLI 的 `inactivityTimeout` 默认 300 秒（非活跃超时，持续有输出不触发），但 `run_shell_command` 本身的超时需单独设置。

### 7.3 指挥官的续跑机制

指挥官本身是一个持久化的 Gemini 会话，中断后通过以下方式恢复：

```bash
gemini --resume latest        # 恢复最近一次会话
gemini --list-sessions        # 查看所有会话列表（获取数字序号）
gemini --resume 3             # 按数字序号恢复
```

注意：`--resume` 只接受 `latest` 或数字序号，**不接受 UUID 字符串**。

用户告知「从 step-04 继续」，指挥官直接从该步重新执行，上下文天然保留（对话历史在服务端持久化）。

### 7.4 非 Java 项目处理

流水线启动后，指挥官执行一次项目结构探测：

```bash
ls -d */ 2>/dev/null | sed 's|/||'      # 列出根目录子目录
find . -maxdepth 2 -name 'pom.xml' | sort  # 查找 Maven 结构
```

若检测到非 Java/Maven 项目（`ACTUAL_MODULE_PREFIX=NON_JAVA`），不做机械路径替换，而是在 Prompt 中插入语义推断说明，让执行 Agent 将 Java 特有扫描节的分析意图映射到项目实际存在的等价物（如 Shell 脚本、配置文件、JSON 契约等）。无等价物时明确标注 `N/A`，不跳过、不虚构。

### 7.5 可行性验证记录


| #   | 验证项                                           | 结论        | 说明                                                                 |
| --- | --------------------------------------------- | --------- | ------------------------------------------------------------------ |
| 1   | `gemini -p '' --yolo` 管道模式能否在非 TTY 环境下正常启动    | ✅         | 实测 `printf '%s' 'prompt' | gemini -p '' --yolo` 成功执行，EXIT_CODE:0   |
| 2   | `--yolo` 机制可靠性                                | ✅         | 源码验证：PolicyEngine 在 YOLO 模式下走独立分支，直接返回 ALLOW，不经过 nonInteractive 降级 |
| 3   | `read_file` 读取大日志文件是否截断                       | ⚠️ 截断     | `DEFAULT_MAX_LINES_TEXT_FILE=2000`，已改用 `grep` 精准提取规避               |
| 4   | `inactivityTimeout` 默认值                       | ✅ 300 秒   | 非活跃超时（持续有输出不触发），大型项目分析通常不会触发                                       |
| 5   | `.gemini/policies/` TOML 文件在 headless 模式下是否生效 | ❌ 不生效     | `disableWorkspacePolicies=true` 硬编码默认值，已弃用此方案                      |
| 6   | `ask_user` 工具可靠性                              | ❌ 有已知 bug | 对话框可能被自动 dismiss，当前版本不使用，参数收集改为硬编码默认值                              |


### 7.6 方案亮点与取舍

**亮点**：

- 指挥官是原生 Gemini 会话，无需外部状态管理，续跑机制天然支持
- 执行 Agent 物理级隔离（OS 进程），比 chat ID 隔离更彻底
- SKILL 本身即文档，部署只需复制一个文件
- 支持非 Java 项目的语义推断模式

**取舍**：

- 依赖 Gemini CLI，不适合只有 Cursor 的环境
- `ask_user` bug 导致参数收集无法交互式进行（待上游修复）
- 无心跳监控（执行过程对用户不透明，只能查日志）

### 7.7 防御性红线速查（Gemini CLI 版）

| 红线 | 规则 | 违反后果 |
|------|------|----------|
| **R-01 隔离红线** | 子进程调用绝对禁止携带 `--resume` 或 `-r` | Token 预算不重置，历史上下文污染后续分析 |
| **R-02 交互隔离红线** | 子进程调用必须包含 `-p ''` + `--yolo`，严禁启动 TUI，严禁省略 `--yolo` | 工具调用被 nonInteractive 模式静默 DENY，Agent 无法写文件 |
| **R-03 熔断红线** | 日志中不含 `[!SUCCESS]` 块时，指挥官必须立即 Panic 并告知用户日志路径，禁止用兜底摘要继续 | 认知接力链断裂，后续步骤在错误基础上继续，静默产出劣质知识库 |
| **R-04 变量红线** | 下发给子进程的 Prompt 禁止遗留任何未替换的 `{{...}}` 占位符 | 执行 Agent 扫描错误路径，产出与项目无关的内容 |
| **R-05 Resume 红线** | `--resume` 只传 `latest` 或通过 `--list-sessions` 确认的数字序号，禁止传 UUID 字符串 | CLI 报错，指挥官会话无法恢复 |

---

## 八、实现方案 B：bash + Cursor Agent CLI 版

### 8.1 方案概述

- **指挥官载体**：通过 `cursor agent create-chat` 创建的持久 Cursor 会话（chat ID）
- **执行 Agent**：通过 `cursor agent create-chat` + stdin 传入 Prompt 的 Cursor Agent
- **编排方式**：`run-archaeology.sh` bash 脚本驱动整条流水线
- **平台要求**：macOS（当前）/ Linux（脚本层面兼容，注释中已标注），需 Cursor CLI、jq

### 8.2 Cursor Agent CLI 核心能力

```bash
# 创建新会话，返回 chat ID
cursor agent create-chat

# 通过 stdin 传入 Prompt，非交互式执行
cat next-prompt.md | cursor agent --print --yolo --resume <chatId>
```

与 Gemini CLI 版的关键区别：Cursor Agent 通过 chat ID 隔离会话（而非 OS 进程），每步 `create-chat` 创建全新会话，不带历史。

### 8.3 指挥官初始化协议

bash 版指挥官通过以下流程初始化和工作：

**初始化**：脚本启动时调用 `cursor agent create-chat` 创建持久会话，获取 `COMMANDER_ID`。向其发送角色定义消息，内容包括：项目名、模板目录、产出目录，以及核心规则——「每次收到步骤结果后，读取对应模板，结合前序发现动态调整，将生成的 Prompt 写入 `next-prompt.md`，禁止输出到对话」。

**每步循环**：
1. 脚本删除旧的 `next-prompt.md`，向指挥官发送「上一步结果摘要 + 请生成下一步 Prompt」消息
2. 指挥官读取模板、注入前序摘要、写入 `next-prompt.md`
3. 脚本轮询等待文件出现（`--print` 模式同步阻塞，轮询作兜底，最多等 30 分钟）
4. 脚本 `cat next-prompt.md` 传入新的执行 Agent

**写文件可靠性**：指挥官生成的 Prompt 不走 stdout 解析，直接通过 `write_file` 工具写入文件，bash 脚本 `cat` 读取，100% 规避转义字符污染。已验证：`--print` 模式下 Agent 可正常执行工具调用（含文件写入）。

**降级方案**（未实现）：001 不可用或 token 耗尽时，bash 直接渲染模板 + 变量替换，跳过指挥官。模板本身含「读取前序产出」指令，执行 Agent 仍会自行适配，但失去指挥官的动态策略调整能力。

### 8.3 心跳监控机制

bash 版特有的进度可观测性设计。每个执行 Agent 启动后，脚本同时 fork 一个后台子进程：

- 每 **6 秒** tick 一次，读取 Cursor Agent 对应的 transcript 文件：
  `~/.cursor/projects/<project-path>/agent-transcripts/<agent-id>/<agent-id>.jsonl`
- 通过对比文件行数变化，判断 Agent 状态（`turn N` / `thinking` / `starting`）
- 最新一行 JSON 通过内嵌 python3 解析，提取 role 和摘要（≤80 字符）
- 进度写入 `logs/<timestamp>/<step>.heartbeat.log`，不打印到控制台
- Agent 完成后立即 kill，`trap EXIT` 兜底清理

这解决了 AI 长时间推理时控制台「假死」的问题，同时不影响流水线执行结果。

### 8.4 日志系统

三层日志结构：

| 日志文件 | 内容 | 写入方式 |
|---------|------|----------|
| `pipeline.log` | 主流程节点（步骤启动/完成/耗时） | `log()` 函数同时输出到终端和文件 |
| `<step>.log` | 每步 Agent 的完整输出 | `tee` 同时写文件和终端 |
| `<step>.heartbeat.log` | 心跳监控进度摘要 | 后台子进程写入 |

每次运行创建 `logs/<YYYY-MM-DD_HHMMSS>/` 子目录，`logs/latest` 软链始终指向最新一轮。

快捷监控命令：`tail -f {项目名}-knowledge/.logs/latest/pipeline.log`

### 8.5 可行性验证记录

| # | 验证项 | 结论 | 说明 |
|---|--------|------|------|
| 1 | `cursor agent create-chat` 返回 chat ID | ✅ | 实测返回 `c9f65486-bd00-4072-936c-2ecd2770535e` |
| 2 | `--print --resume <chatId>` 非交互式执行 | ✅ | stdin 传入 Prompt，成功执行并输出到 stdout |
| 3 | `--print` 模式下 Agent 可写文件 | ✅ | 实测向 Agent 发送写文件指令，文件成功生成 |
| 4 | 进程终止后 chat ID 会话可 resume | ✅ | Ctrl+C 后 resume，001 准确回忆项目名和已完成步骤 |
| 5 | 会话跨天持久性 | ✅ | 实测隔 3 天 resume 仍可用，上下文完整 |
| 6 | `STOP READING HERE` 对 Cursor rules 加载器无效 | ❌ | `.mdc` 文件全量注入 context，已从模板移除 |
| 7 | `--model` 在 `--resume` 模式下无效 | ❌ | resume 后模型固定为创建时的模型，`--model` 参数被忽略 |

### 8.6 方案亮点与取舍

**亮点**：
- 心跳监控提供实时进度可观测性
- 三层日志结构完整，事后分析友好
- 纯 bash 实现，无额外运行时依赖
- 适合已在使用 Cursor 的团队，零额外工具成本

**取舍**：
- 依赖 Cursor CLI，不适合只有 Gemini CLI 的环境
- chat ID 隔离（应用层）相比 OS 进程隔离（系统层）理论上不那么彻底
- `--model` 在 resume 模式下无效，指挥官模型在创建时固定
- 断点续跑尚未实现（checkpoint 机制已设计，待开发）
- macOS `sed -i ''` 语法与 Linux GNU sed 不兼容（当前限制 macOS，Linux 兼容性待验证）

---

## 九、设计亮点与取舍

### 9.1 项目整体亮点

**知识增量串联（认知接力）**

每步产出的 `[!SUCCESS]` 摘要注入到下一步的先验知识层，形成一条完整的发现链。后面的步骤不是在空白状态下分析，而是站在前序发现的肩膀上做交叉验证。这是这个流水线区别于「让 AI 一次性分析整个项目」的核心差异。

**执行层无状态 + 指挥层有状态**

执行 Agent 每步全新（无状态），保证分析纯净；指挥官持续运行（有状态），保证全局视野。这种分工让两个矛盾的需求（纯净 vs 连续）同时得到满足。

**模板驱动的可复现性**

11 个 Prompt 模板固化了人工模式下验证过的分析框架。新项目只需输入项目名，流水线输出的知识库结构与经过验证的项目完全对齐，无需重新设计 Prompt。

**AI 自决的动态拓扑**

Step 05 的 `05_module_manifest.json` 让流水线拓扑在运行时由 AI 决定。这是「静态脚本 + 动态知识」的结合：脚本逻辑不变，知识结构随项目特点自适应。

**双端知识库兼容**

产出的规则文件同时支持 Cursor（`.mdc` 格式）和 Gemini CLI（`.gemini/rules/` 格式），团队成员使用不同 AI 工具时均可加载同一套知识库。

### 9.2 已知局限

| 局限 | 影响 | 计划 |
|------|------|------|
| 断点续跑（bash 版）未实现 | 流水线中断需从头重跑 | checkpoint 机制已完整设计，待开发 |
| `ask_user` bug（Gemini 版） | 参数收集无法交互式进行 | 待 Gemini CLI 上游修复 |
| macOS 专有语法（bash 版） | Linux 上部分命令需调整 | 待验证并修复 GNU sed 兼容性 |
| `--model` resume 无效（bash 版） | 指挥官模型固定 | 已验证，文档标注 |
| 模块上限 26 个（a-z 后缀） | 超大项目可能不够 | 可扩展为 `08aa`/`08ab` 等双字母后缀 |

---

## 十、参与贡献

欢迎拥抱开源！本项目代码托管在内源平台，欢迎 Issue、PR：

```
http://code.oppoer.me/InnerSource/api/ai-knowledge.git
```


---

## 十一、待办：

- 常驻监控 Chat 守护进程（Monitor Daemon）
> plan/monitor-daemon.md。

- **`run-archaeology.sh` 改造为真正的 Skill 格式**
  当前 `archaeology-commander` SKILL.md 本质上是「伪 Skill」——调度逻辑（循环、变量替换、子进程孵化）依赖 AI 运行时理解，而非 Gemini CLI Skill 规范的结构化字段。
  改造方向：用 `resources` 声明 prompt 模板为可加载资源；用结构化 tool manifest 替代 `run_shell_command` 裸调用；引入 Skill 版本管理。
  **可行性：可行，中等工作量**。核心调度逻辑需重新用 Skill DSL 描述，不是简单改文件格式。

---
 
```

