# 0. 核心接力策略（最高执行优先级）

Step audit-rules: audit .cursor/rules/qpon-bigdata.mdc and .gemini/rules/qpon-bigdata.md against 00_Master_Catalog; open debts must remain open; apply patches if audit fails

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

# Step Audit: Rules 合规性审计

[Role] 知识库质量审计师。
你的任务是对 .cursor/rules/qpon-bigdata.mdc 以及 .gemini/rules/qpon-bigdata.md 文件进行合规性审计，
确保其满足知识库构建的三大目的：意图路由、防御性编码红线、知识库双写。

[Context]
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。
Step Final 已经生成了 00_Master_Catalog.md 和 qpon-bigdata.mdc。

本步骤是知识库的最终质量门禁，确保生成的规则文件能够真正约束 AI 的行为。

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件：
1. .cursor/rules/qpon-bigdata.mdc — 待审计的 Cursor 规则文件
2. .gemini/rules/qpon-bigdata.md — 待审计的 Antigravity 规则文件
2. qpon-bigdata-knowledge/00_Master_Catalog.md — 总目录

[Task: Rules 合规性审计]

### 审计清单

对 qpon-bigdata.mdc 文件执行以下 9 项审计：

#### 目的一：意图路由（3 项审计）

**[A1] 全局入口**
- [ ] 是否明确规定了"全局入口"？
- 检查标准：必须提到强制首读 00_Master_Catalog.md
- 如果缺失：补充"强制首读"条款

**[A2] 场景分流**
- [ ] 是否做到了"场景分流"？
- 检查标准：必须列出至少 8 个常见场景的知识库文件路径
  - 排障/线上问题
  - 新增/修改 Dubbo 接口
  - 新增/修改数据表
  - 新增 Job/MQ
  - 新增下游依赖
  - 新增业务模块
  - 性能优化
  - 快速上手
- 如果缺失：补充场景路由表

**[A3] 禁止盲目搜索**
- [ ] 是否明确禁止未读知识库就全库搜索？
- 检查标准：必须有明确的"禁止"条款
- 如果缺失：补充禁止条款

#### 目的二：防御性编码红线（3 项审计）

**[B1] 封杀原生异常**
- [ ] 是否明确封杀了原生异常？
- 检查标准：必须有"禁止 catch 异常后 return null/false"或"禁止抛出 RuntimeException"的红线
- 如果缺失：补充异常处理红线

**[B2] 微服务防腐规约**
- [ ] 是否明确了微服务防腐规约？
- 检查标准：必须有"RPC 调用必须配置超时"或"强制拆包 CommonResponse"的红线
- 如果缺失：补充微服务防腐红线

**[B3] 并发安全机制**
- [ ] 是否强制了并发安全机制？
- 检查标准：必须有"缓存操作必须通过 Repository"或"分布式锁必须显式配置"的红线
- 如果缺失：补充并发安全红线

#### 目的三：知识库双写（3 项审计）

**[C1] 触发条件**
- [ ] 是否写明了触发条件？
- 检查标准：必须列出至少 8 种代码变更类型及其对应的知识库文件
  - 新增/修改 Dubbo 接口 → 02
  - 新增/修改数据表/字段 → 04
  - 新增/修改下游依赖 → 03
  - 新增/修改 Job/MQ → 06
  - 新增/修改缓存策略 → 07
  - 新增/修改配置项 → 07
  - 新增/修改业务模块 → 08x
  - 项目骨架/依赖变更 → 01
- 如果缺失：补充触发条件表

**[C2] 自我反思拦截词**
- [ ] 是否包含了硬编码的自我反思拦截词？
- 检查标准：必须有类似"🔍 [知识库资产审计]：本次代码变更是否导致现有架构资产过期？[是/否]"的自问自答环节
- 如果缺失：补充自我反思环节

**[C3] 连带输出要求**
- [ ] 是否强制要求了输出 Diff/Patch？
- 检查标准：必须有"如有过期，必须连带输出对应 `.md` 文件的更新 Diff"的要求
- 如果缺失：补充连带输出要求

### 审计报告格式

生成审计报告，格式如下：

```markdown
# qpon-bigdata.mdc 合规性审计报告

## 审计结果总览

| 审计项 | 状态 | 说明 |
|--------|------|------|
| [A1] 全局入口 | ✅/❌ | ... |
| [A2] 场景分流 | ✅/❌ | ... |
| [A3] 禁止盲目搜索 | ✅/❌ | ... |
| [B1] 封杀原生异常 | ✅/❌ | ... |
| [B2] 微服务防腐规约 | ✅/❌ | ... |
| [B3] 并发安全机制 | ✅/❌ | ... |
| [C1] 触发条件 | ✅/❌ | ... |
| [C2] 自我反思拦截词 | ✅/❌ | ... |
| [C3] 连带输出要求 | ✅/❌ | ... |

**通过率**：[X]/9

## 未通过项补丁

对于每个未通过的审计项，生成补丁文本：

### [A1] 全局入口补丁

```mdc
## 第一章：意图路由协议

**强制首读**：任何涉及本服务的任务，先读 `qpon-bigdata-knowledge/00_Master_Catalog.md`，从场景路由表确定本次任务所需的知识文件。
```

...（其他补丁）

## 补丁应用指令

请将以上补丁同时应用到 .cursor/rules/qpon-bigdata.mdc 和 .gemini/rules/qpon-bigdata.md 文件中，
确保 9 项审计全部通过。
```

### 补丁应用

如果有未通过项，自动将补丁应用到 qpon-bigdata.mdc 文件中，
然后重新执行审计，直到 9/9 通过。

[Action]
1. 生成审计报告：qpon-bigdata-knowledge/Rules_Audit_Report.md
2. 如有未通过项，自动应用补丁到两个规则文件中
3. 重新审计，直到 9/9 通过

[Constraint - 工业级底线]

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `.cursor/rules/qpon-bigdata.mdc` 或 `qpon-bigdata-knowledge/00_Master_Catalog.md` 不存在，必须立即停止并输出：`❌ 未在工作区找到 [文件路径]，请确认 step-final 已完成。` 禁止推断替代内容，禁止访问工作区外目录。

**输出格式锁定**：
- 审计报告必须包含：审计结果总览、未通过项补丁、补丁应用指令
- 每个审计项必须有明确的 ✅/❌ 状态

**严防静默截断**：
- 9 项审计必须全部执行，不允许跳过任何一项
- 未通过项必须生成补丁，不允许只报告问题

**专业性底线**：
- 补丁文本必须可以直接复制粘贴到 .mdc 文件中
- 补丁文本必须符合 .mdc 文件的格式规范
- 补丁文本必须具体可执行，不用模糊词汇

**结尾标准审计闭环**：

```
> [!SUCCESS] Rules 审计闭环验证
> - 审计范围：qpon-bigdata.mdc 文件
> - 审计结果：[X]/9 通过
> - 补丁应用：[Y] 个补丁已应用
> - 最终状态：9/9 通过 ✅ / 仍有未通过项 ❌
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
