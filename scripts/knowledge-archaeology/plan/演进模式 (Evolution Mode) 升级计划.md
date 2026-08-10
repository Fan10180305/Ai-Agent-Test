# 知识库考古流水线：演进模式 (Evolution Mode) 升级计划

## 1. 背景与核心动机

### 1.1 现状痛点

当前流水线是单次线性扫描，面临两个真实问题：

- **随机性盲点**：大模型是概率机，单次运行可能遗漏深层嵌套的业务逻辑（如隐秘的 MQ Topic、复杂的 if 分支）
- **冷启动浪费**：代码发生变更后，流水线必须从零重跑，已有知识库完全被抛弃，没有被利用

### 1.2 目标

将「再次运行」从「推倒重来」变为「在旧假说上做审计」——Agent 在扫描代码时，同时持有上一轮的知识库作为参照，用代码事实直接覆写旧内容，让每次运行都能在上一轮的基础上提升精度。

---

## 2. 关键架构决策

| 决策点 | 采选方案 | 理由 |
|:---|:---|:---|
| **知识存储** | MD 文件直接覆写，不在正文打标 | 多轮标注（`[!UPDATED]`/`[!NEW_DISCOVERY]`）会堆积，分不清哪轮产出，制造噪声；知识库反映当前代码事实，不是 changelog |
| **变化传递通道** | 走现有 `[!SUCCESS]` 和 `[!RELAY]`，不新建机制 | `[!SUCCESS]` 已有「旧文档验证」行，天然可承载演进对比结论；`[!RELAY]` 的 Context 字段本来就是「对下一步有决定性影响的事实」，演进发现的变化写进去即可；指挥官 grep 这两块，后续步骤自动感知 |
| **旧 MD 注入方式** | Agent 按需 `read_file` 读取 `{{old_knowledge_path}}`，路径由指挥官注入 | 不引入不存在的「摘要索引」基础设施；指挥官只做路径锁定，读取由 Agent 自主执行 |
| **跨步骤关联** | 依赖已有的「先验知识注入」节（该节已要求读取前几步产出 MD）| 先验知识注入节本来就在读其他步骤产出，无需额外机制；跨步骤关联通过 Agent 对多份 MD 的综合阅读自然发生 |
| **审计准则** | 以代码事实为准，不符就直接改 | 代码是权威，旧 MD 是参照，发现不符直接修改 MD 正文；不需要话术 |
| **与 RELAY 的关系** | Evolution Context 作为先验知识注入节的子节，RELAY 保持最高优先级不变 | 两者解决不同维度：RELAY 传递「上一步的强制指令」，Evolution Context 传递「上一轮的存量假说路径」；不合并，不干扰 |

---

## 3. 架构设计

### 3.1 指挥官层（SKILL.md）

**§一 变量初始化**——新增：

```
EVOLUTION_MODE   = false（初始值，Preflight 阶段更新）
```

**§二 Preflight**——新增存量探测（在现有检查项末尾追加）：

```bash
# 8. 演进模式探测
EVOLUTION_MODE=false
if [ "$(find ${OUTPUT_DIR} -maxdepth 1 -name '*.md' 2>/dev/null | wc -l)" -gt 0 ]; then
  EVOLUTION_MODE=true
  echo "ℹ️ 探测到存量知识库，演进模式已启用"
fi
```

**§三 Step 1 变量替换**——新增一条：

```
- `{{evolution_mode_context}}` → EVOLUTION_MODE=true 时注入演进节全文（含 {{old_knowledge_path}} 已展开的路径）；EVOLUTION_MODE=false 时替换为空字符串，整段不出现
```

> 注：`{{old_knowledge_path}}` 不作为独立变量替换，而是在指挥官生成 `{{evolution_mode_context}}` 内容时直接展开为实际路径，不暴露给模板层。

**`{{old_knowledge_path}}` 路径映射表**：

| 步骤 | 对应旧 MD 路径 |
|:--|:--|
| step-0-legacy | `${OUTPUT_DIR}/Legacy_${PROJECT_NAME}_Claims.md` |
| step-01-skeleton | `${OUTPUT_DIR}/01_Module_Skeleton_and_Stack.md` |
| step-02-contracts | `${OUTPUT_DIR}/02_External_Contracts.md` |
| step-03-downstream | `${OUTPUT_DIR}/03_Downstream_Dependencies.md` |
| step-04-data-model | `${OUTPUT_DIR}/04_Data_Model_and_Lifecycle.md` |
| step-05-orchestration | `${OUTPUT_DIR}/05_Business_Orchestration.md` |
| step-06-async | `${OUTPUT_DIR}/06_Async_Jobs_and_Compensation.md` |
| step-07-config | `${OUTPUT_DIR}/07_Config_and_Observability.md` |
| step-08（各模块） | `${OUTPUT_DIR}/08${suffix}_Module_${module_name}.md` |
| step-final-assembly | `${OUTPUT_DIR}/00_Master_Catalog.md` |
| step-audit-rules | 不适用（跳过） |

文件不存在时，不生成当前步骤的旧 MD 路径，`{{evolution_mode_context}}` 整段不注入。

### 3.2 模板层

**改动**：在 10 个模板（step-0 到 step-08 + step-final-assembly）的 `[先验知识注入]` 节末尾追加 `{{evolution_mode_context}}` 占位符。step-audit-rules 不适用，跳过。

`{{evolution_mode_context}}` 由指挥官根据 `EVOLUTION_MODE` 动态生成内容注入：

**`EVOLUTION_MODE=false` 时**：替换为空字符串，不注入任何内容。模板行为与当前完全一致。

**`EVOLUTION_MODE=true` 时**，指挥官生成以下**完整文本**注入（其中 `<旧MD路径>` 由指挥官查映射表展开为实际路径，如 `${OUTPUT_DIR}/03_Downstream_Dependencies.md`；若文件不存在则整段不注入）：

```
---
## 演进模式

本次为再次运行，存在上一轮产出的旧知识库。

请 read_file 读取 `<旧MD路径>` ，将其作为「旧假说」参照：
- 扫描代码时以代码事实为准，旧假说与代码不符则直接覆写对应内容
- 旧假说中已有的内容若代码验证无误，保持不动（避免无意义重写）
- 代码中存在但旧假说未记录的逻辑，直接补充进对应章节

旧假说是参照，不是权威。代码是唯一权威。

### 演进对比输出要求

1. 在你的 [!SUCCESS] 块末尾追加一行演进对比（无论模板中是否已有「旧文档验证」行）：
   `- 演进对比：覆写了 [X] 处 / 补充了 [Y] 处 / 与旧假说完全一致（无变化）`

2. 在你的 [!RELAY] 的 Context 字段中，若演进中发现对下一步有决定性影响的变化
   （如：旧假说中某服务已从代码删除 / 新增了某服务的调用），必须在 Context 中声明。
   无演进变化时 [!RELAY] 按常规填写代码事实，无需特殊处理。
---
```

> 以上是 Agent 实际看到的 Prompt 文本。`<旧MD路径>` 是唯一需要指挥官在注入前替换的位置，不暴露给模板层。

### 3.3 与 RELAY 的 Prompt 层次关系

```
[Role]
[Context]
[最高指令挂载]
─────────────────────────────────────────
# 0. 核心接力策略（RELAY，最高优先级）   ← 已落地
─────────────────────────────────────────
[先验知识注入]
  原有：读前步产出 MD（步间横向接力）
  新增：{{evolution_mode_context}}       ← 本次新增（指挥官内部展开路径后注入）
         └─ 含 old_knowledge_path（已由指挥官解析为实际路径，非独立模板变量）
─────────────────────────────────────────
[Task]
```

---

## 4. 改动范围

| 改动对象 | 改动内容 | 改动量 |
|:--|:--|:--|
| SKILL.md §一 | 新增 `EVOLUTION_MODE` 变量 | 1 行 |
| SKILL.md §二 Preflight | 新增存量 MD 探测 | 约 6 行 |
| SKILL.md §三 Step 1 | 新增 1 个变量替换规则（`{{evolution_mode_context}}`，内部展开路径）+ `{{old_knowledge_path}}` 映射表（指挥官内部查表用） | 约 15 行 |
| 10 个模板（step-0 ~ step-08 + step-final-assembly） | 先验知识注入节末尾追加 `{{evolution_mode_context}}` | 每个 +1 行 |

**不改的**：模板正文、任务描述、`[!SUCCESS]` 和 `[!RELAY]` 的格式定义（演进要求通过 `{{evolution_mode_context}}` 注入，不改格式声明本身）

---

## 5. 验证计划

**验证 1（覆写能力）**：
- 执行全量考古，产生基准 MD
- 手动修改一处代码（如更改一个外部服务的超时配置）
- 再次运行，检查对应 MD 章节的内容是否已更新为新值
- 成功标准：MD 内容与当前代码事实一致，无旧值残留

**验证 2（保留正确内容——防止全量重写）**：
- 执行全量考古，产生基准 MD
- 不修改任何代码，直接再次运行（演进模式）
- 对比两轮 MD 的 diff：逐章节检查是否出现了「内容正确但被改写为不同措辞」的情况
- 检查 `[!SUCCESS]` 中的演进对比行是否为「与旧假说完全一致（无变化）」
- 成功标准：两轮 MD 内容高度一致（允许措辞微调），不出现信息丢失或无意义重写

**验证 3（跨步骤关联）**：
- 在代码中新增一个外部服务调用
- 再次运行，检查 step-03 能否在扫描到新服务时，主动关联到 step-02 旧产出中是否缺少对应契约
- 成功标准：step-03 的 MD 中出现对该服务的记录，且 step-02 在下一轮运行时补充了对应契约

---

## 6. 待决策项

> [!NOTE]
> **EVOLUTION_MODE 启用的粒度**：当前设计是「OUTPUT_DIR 下有任何 MD 文件即启用」。是否需要更细的控制（如某些步骤强制不走演进模式）？暂定全量启用，实测后根据效果调整。

> [!NOTE]
> **与 RELAY 的验证策略**：用「首次全量运行 → 演进模式再次运行」两轮来同时验证 RELAY 和 Evolution Mode：
> - **第一轮**：RELAY 接力是否生效——观察各步骤的 `[!RELAY]` 输出是否被下一步实际采纳，扫描方向是否产生了定向变化
> - **第二轮**（演进模式）：n+1 增量能力——第二次运行是否在第一次产出基础上覆写了差异、补充了遗漏，而不是无意义的重复；同时验证「先验知识注入」和「演进节」是否与原有 Prompt 结构保持解耦，没有引入结构性干扰
> - **两轮对比**即是最终验证：若第二轮的 MD 产出与第一轮相比有可解释的增量，且 Prompt 结构未变形，则两个机制同时通过验收
