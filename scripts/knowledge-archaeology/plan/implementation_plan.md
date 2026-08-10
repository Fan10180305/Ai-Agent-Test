# 认知接力强化实施计划 (Completed)

## 1. 核心目标

在保持现有模板和指挥官逻辑基本不动的前提下，引入 `[!RELAY]` 动态指令通道作为步间认知接力的补充机制。

- **Java 项目零降级**：模板正文完全不动，经实战验证的高精度指令集保持原样
- **非 Java 项目增强**：step-01 的 RELAY 向后传递技术栈特异性发现，弥补静态模板在未知技术栈上的覆盖盲区
- **改动面极小**：SKILL.md 约 30 行新增 + 9 个模板各加 4 行

## 2. 设计决策记录

### 为什么不做 A+B 分层模板重构

原方案（`[!RELAY]` 独立协议 + 模板 A 层/B 层分层重构）被否决，原因：

- 具体指令比抽象意图更利于 AI 发挥——Java 模板的高精度正是其核心价值，重构会降级
- 模板重构工作量大（11 个模板全量），但对 Java 项目无收益
- 非 Java 项目的 B 层变体质量无法保证——写得不够精确就等于把「请自行映射」换了个说法

### 为什么不引入 PROJECT_TYPE 变量

- 真正了解技术栈细节的是 step-01 执行 Agent，不是指挥官的 `ls` 命令
- 保持 Java / NON_JAVA 二分已足够，更细的分类由 step-01 RELAY 动态传递

### 为什么不泛化先验知识注入中的 § 章节号

- § 引用在 Java 项目上精度高、经过实践验证
- 非 Java 项目上 AI 已经在自动处理指向虚空的引用——泛化在 Java 上是降级，在非 Java 上收益极小

## 3. 落地计划与完成情况

### Phase 1: 指挥官改造（SKILL.md）

- [x] **[MODIFY]** §一 变量初始化：新增 `RELAY_STRATEGY` 变量，默认值「无先验接力偏好，请按标准考古规范执行。」
- [x] **[MODIFY]** §三 Step 1：新增 `{{RELAY_STRATEGY}}` 变量替换规则；在「先验知识注入」之前插入接力策略块
- [x] **[MODIFY]** §三 Step 6：新增 `[!RELAY]` grep 提取逻辑，找到则更新 RELAY_STRATEGY，未找到则重置为默认值并记录 WARN（不熔断）
- [x] **[MODIFY]** NON_JAVA 处理段：对 step-01 追加 RELAY 输出要求，要求输出技术栈清单和后续步骤扫描路径建议

### Phase 2: 模板微调（9 个模板）

- [x] `step-0-legacy.md`：追加 `[!RELAY]` 格式定义
- [x] `step-01-skeleton.md`：追加 `[!RELAY]` 格式定义
- [x] `step-02-contracts.md`：追加 `[!RELAY]` 格式定义
- [x] `step-03-downstream.md`：追加 `[!RELAY]` 格式定义
- [x] `step-04-data-model.md`：追加 `[!RELAY]` 格式定义
- [x] `step-05-orchestration.md`：追加 `[!RELAY]` 格式定义
- [x] `step-06-async.md`：追加 `[!RELAY]` 格式定义
- [x] `step-07-config.md`：追加 `[!RELAY]` 格式定义
- [x] `step-08-module-template.md`：追加 `[!RELAY]` 格式定义
- （step-final-assembly.md / step-audit-rules.md 为终点步骤，不追加）

### Phase 3: Bug 修复

- [x] step-01-skeleton.md 先验知识注入节：`Legacy_SignInCenter_Claims.md` 已为 `Legacy_{{project_name}}_Claims.md`，无需变更

## 4. [!RELAY] 格式规范（所有模板统一）

```markdown
> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对下一步有决定性影响的关键事实]
> - **推演约束 (Constraint)**: [基于事实，强制下一步重点分析的具体内容]
> - **物理锚点 (Anchors)**: [对应的文件路径或行号]
```

## 5. 降级策略

- `[!SUCCESS]` 缺失 → **硬熔断**（流水线停止，不可接受静默失败）
- `[!RELAY]` 缺失 → **软降级**（RELAY_STRATEGY 重置为默认值 + pipeline.log 记录 WARN，不熔断）

原因：RELAY 是补充通道，不是主通道。缺失不代表考古失败，但必须留痕。

## 6. 遗留与后续扩展

> [!NOTE]
> **关于非 Java 项目的深度适配**
> 当前方案通过 step-01 RELAY 向后传递技术栈信息，是「低成本垫脚石」级别的改进。
> 若实际跑前端/测试项目后发现产出质量仍不达标，下一步考虑在 SKILL.md 中为特定
> 技术栈（frontend/python 等）编写精确的适配指令映射表——只改 SKILL.md 一个文件，模板不动。
