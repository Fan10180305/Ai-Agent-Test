# Knowledge Archaeology Prompts

本目录包含用于构建 qpon-sign-in-center 知识库的所有 prompt 模板。

## 文件清单

| 文件名 | 步骤 | 描述 | 行数 | 状态 |
|--------|------|------|------|------|
| `step-0-legacy.md` | Step 0 | 旧文档声称提取 | 79 | ✅ 已创建 |
| `step-01-skeleton.md` | Step 01 | 模块骨架与技术栈审计 | 124 | ✅ 已创建 |
| `step-02-contracts.md` | Step 02 | 对外契约全量审计 | 130 | ✅ 已创建 |
| `step-03-downstream.md` | Step 03 | 下游依赖全量测绘 | 63 | ✅ 已创建 |
| `step-04-data-model.md` | Step 04 | 数据模型与生命周期全量测绘 | 178 | ✅ 已创建 |
| `step-05-orchestration.md` | Step 05 | 业务编排全量测绘 | 108 | ✅ 已创建 |
| `step-06-async.md` | Step 06 | 异步机制与补偿全量测绘 | 192 | ✅ 已创建 |
| `step-07-config.md` | Step 07 | 配置体系与可观测性全量测绘 | 192 | ✅ 已创建 |
| `step-08-module-template.md` | Step 08 | 业务模块深潜模板 | 137 | ✅ 已创建 |
| `step-final-assembly.md` | Final | 总目录组装与规则生成 | 222 | ✅ 已创建 |
| `step-audit-rules.md` | Audit | Rules 合规性审计 | 191 | ✅ 已创建 |

## 参数化说明

所有 prompt 模板使用以下变量进行参数化：

- `{{project_name}}` - 项目名称（如：qpon-sign-in-center）
- `{{project_display_name}}` - 项目显示名称（如：签到中心）
- `{{output_dir}}` - 输出目录（如：docs/ai-knowledge/qpon-sign-in-center/）
- `{{legacy_docs_dir}}` - 旧文档目录（如：old-readme/）

## 使用方法

1. 选择对应步骤的 prompt 文件
2. 替换模板中的变量为实际值
3. 在新的 Agent 会话中执行 prompt
4. 验证输出结果
5. 提交到知识库

## 提取进度

### ✅ 全部完成

所有 11 个 prompt 模板已成功提取并参数化：

- ✅ Step 0: 旧文档声称提取（79行）
- ✅ Step 01: 模块骨架与技术栈审计（124行）
- ✅ Step 02: 对外契约全量审计（130行）
- ✅ Step 03: 下游依赖全量测绘（63行）
- ✅ Step 04: 数据模型与生命周期全量测绘（178行）
- ✅ Step 05: 业务编排全量测绘（108行）
- ✅ Step 06: 异步机制与补偿全量测绘（192行）
- ✅ Step 07: 配置体系与可观测性全量测绘（192行）
- ✅ Step 08: 业务模块深潜模板（137行）
- ✅ Final: 总目录组装与规则生成（222行）
- ✅ Audit: Rules 合规性审计（191行）

**总计**: 1714 行（含 README）

## 提取命令

```bash
# 从知识库文件中提取 Step 01-07 的 prompts
for file in docs/ai-knowledge/qpon-sign-in-center/*.md; do
  echo "Processing: $file"
  # 提取 🛑 标记之后的内容
  sed -n '/🛑.*STOP READING HERE/,/<\/details>/p' "$file"
done

```

## 提取方法

本次提取使用了以下方法：

1. **Step 0-07**: 从知识库文件 `docs/ai-knowledge/qpon-sign-in-center/*.md` 的 `🛑 [AI Context Parser Directive: STOP READING HERE]` 标记之后提取
   - Step 0-03: 从 `<details>` 块中的代码块提取
   - Step 04: 从两个 `🛑` 标记之间提取
   - Step 05-07: 从 `🛑` 标记到文件末尾提取

2. **Step 08**: 基于已有的 08a-08e 知识库文件和总结文档，创建通用模板

3. **Final & Audit**: 基于总结文档和知识库构建的三大目的，创建完整 prompt

## 注意事项

1. **完整性**: 确保每个 prompt 都包含完整的 RCAC 结构（Role, Context, Action, Constraint）
2. **参数化**: 所有项目特定信息都应使用变量替换
3. **闭环验证**: 每个 prompt 末尾都应包含审计闭环验证块
4. **溯源**: 每个 prompt 末尾都应附上原始 prompt 内容（防注入隔离）

## 使用示例

在新项目中使用这些 prompt 模板：

```bash
# 1. 复制 prompt 模板到新项目
cp -r scripts/knowledge-archaeology/prompts /path/to/new-project/scripts/

# 2. 替换变量
cd /path/to/new-project/scripts/knowledge-archaeology/prompts
find . -name "*.md" -exec sed -i '' 's/{{project_name}}/your-project-name/g' {} \;
find . -name "*.md" -exec sed -i '' 's/{{project_display_name}}/Your Project Display Name/g' {} \;
find . -name "*.md" -exec sed -i '' 's|{{output_dir}}|docs/ai-knowledge/your-project/|g' {} \;
find . -name "*.md" -exec sed -i '' 's|{{legacy_docs_dir}}|old-readme/|g' {} \;

# 3. 在新的 Agent 会话中执行每个 step
# 复制 step-0-legacy.md 的内容，粘贴到 Agent 会话中执行
# 依次执行 step-01 到 step-audit
```

## 质量检查清单

对于每个提取的 prompt,确保：

- [ ] 包含角色定义（Role）
- [ ] 包含上下文说明（Context）
- [ ] 包含最高指令挂载（Collaboration Protocol）
- [ ] 包含先验知识注入（如适用）
- [ ] 包含任务描述（Task）
- [ ] 包含输出要求（Action）
- [ ] 包含约束条件（Constraint）
- [ ] 包含审计闭环（Success Block）
- [ ] 包含指令溯源（Prompt Embedding）
- [ ] 所有项目特定信息已参数化
