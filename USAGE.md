# 使用指南 (USAGE)

## 1. 环境要求

| 工具 | 说明 |
|------|------|
| macOS | 当前版本仅支持 macOS |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | 0.33.2+ |
| `jq` | JSON 解析，`brew install jq` |

---

## 2. 安装

```bash
# 第一步：clone 工具仓库（只需一次）
git clone <repo-url> /path/to/ai-knowledge

# 第二步：进入被分析的项目根目录，执行安装脚本
cd /path/to/your-project
bash /path/to/ai-knowledge/install.sh
```

脚本完成以下操作（全部安装到**当前项目目录**，不污染全局）：

- `.ai-knowledge/config.json` ← 项目配置（记录 tool_home、prompt_dir 等）
- `.ai-knowledge/USAGE.md` ← 使用说明
- `.ai-knowledge/uninstall.sh` ← 卸载脚本
- `.ai-knowledge/collaboration-protocol.md` ← 协作协议原文
- `.ai-knowledge/prompts/` ← 完整 prompt 模板（12 个）
- `.ai-knowledge/scripts/run-archaeology.sh` ← Bash 执行脚本
- `.gemini/skills/archaeology-commander/SKILL.md` ← Gemini 项目级 SKILL
- `.gemini/rules/collaboration-protocol.md` ← Gemini 协作协议
- `old-readme/` ← 旧文档目录

安装后重启 Gemini CLI，项目级 SKILL 即生效。

安装脚本末尾会自动验证所有文件是否存在，输出 `✅ 安装完成` 即表示成功。

手动验证：
```bash
ls .ai-knowledge/prompts/                       # 预期：12 个模板
ls .ai-knowledge/scripts/run-archaeology.sh     # 预期：执行脚本
ls .gemini/skills/archaeology-commander/SKILL.md
cat .ai-knowledge/config.json
```

---

## 3. 更新

工具仓库有新版本时：
```bash
cd /path/to/ai-knowledge
git pull

cd /path/to/your-project
bash /path/to/ai-knowledge/install.sh   # 覆盖安装，SKILL 和模板自动更新
```

---

## 4. 多项目使用

每个需要分析的项目都需要单独执行一次 `install.sh`。不同项目使用同一份工具仓库，互不干扰。

---

## 5. 卸载

```bash
# 使用项目内的卸载脚本（推荐）
bash .ai-knowledge/uninstall.sh          # 删工具文件，保留知识库产出
bash .ai-knowledge/uninstall.sh --purge  # 完整清除（含产出目录和 old-readme/）

# 或使用工具仓库的卸载脚本
bash /path/to/ai-knowledge/uninstall.sh
```

---

## 6. 快速开始

**前提**：已在目标项目根目录执行过 `bash /path/to/ai-knowledge/install.sh`。

进入被分析的项目根目录，选择以下任一方式启动：

### 方式一：Gemini CLI（推荐）

```bash
cd /path/to/your-project
gemini --yolo
```

在对话框输入：

```
运行考古流水线 旧文档=无
```

项目名称从 `.ai-knowledge/config.json` 自动读取，无需手动指定。

### 方式二：Bash 脚本（安装后直接使用）

```bash
cd /path/to/your-project
bash .ai-knowledge/scripts/run-archaeology.sh <项目显示名>
```

> [!TIP]
> 安装后 `run-archaeology.sh` 被复制到 `.ai-knowledge/scripts/`，无需再引用原始工具仓库路径。

---

## 7. 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `旧文档` | ✅ | `无` / `有` / 具体路径 |
| `项目名` | 可选 | 覆盖 config.json 中的 project_name，未提供时自动读取 |
| `工具目录` | 可选 | 覆盖工具根目录，未提供时自动从 config.json 读取 |

---

## 8. 变量解析优先级

| 变量 | 优先级 1 | 优先级 2 |
|------|---------|----------|
| PROJECT_NAME | `项目名=` 参数 | `.ai-knowledge/config.json` |
| OUTPUT_DIR | `.ai-knowledge/config.json` | `${PROJECT_NAME}-knowledge` |
| tool_home | `工具目录=` 参数 | `config.json.tool_home` |
| sh 脚本 | 脚本自身路径自推导 | — |

---

## 9. 旧文档三种模式

### 模式一：无旧文档

```
运行考古流水线 旧文档=无
```

直接跳过 step-0，从 step-01 开始分析代码结构。

### 模式二：使用 old-readme/ 目录

```
运行考古流水线 旧文档=有
```

前置检查时验证 `old-readme/` 存在且非空，不存在则终止并提示先准备旧文档。

### 模式三：指定路径

```
运行考古流水线 旧文档=docs/old-wiki
```

自动收集路径下的 `.md`/`.txt` 文件到 `old-readme/`，然后进行分析。

---

## 10. 产出说明

运行完成后，在当前项目根目录下生成：

```
{项目名}-knowledge/
├── 00_Master_Catalog.md
├── Legacy_{项目名}_Claims.md
├── 01_Module_Skeleton_and_Stack.md
├── 02_External_Contracts.md
├── 03_Downstream_Dependencies.md
├── 04_Data_Model_and_Lifecycle.md
├── 05_Business_Orchestration.md
├── 05_module_manifest.json
├── 06_Async_Jobs_and_Compensation.md
├── 07_Config_and_Observability.md
├── 08{a-z}_Module_*.md
├── Rules_Audit_Report.md
├── .logs/
└── .tmp/
```

---

## 11. Bash 脚本参数说明

```bash
# 安装后（推荐）
bash .ai-knowledge/scripts/run-archaeology.sh <项目显示名> [旧文档路径...]

# 示例
bash .ai-knowledge/scripts/run-archaeology.sh my-app
bash .ai-knowledge/scripts/run-archaeology.sh my-app docs/old-wiki

# 直接从工具仓库运行（开发调试用）
bash /path/to/ai-knowledge/scripts/knowledge-archaeology/run-archaeology.sh my-app
```

---

## 12. 常见错误处理

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `❌ 缺少必填参数` | 未提供 `旧文档=` | 补充参数重新输入 |
| `❌ 无法确定工具根目录` | 未安装且无参数 | 执行 `bash install.sh` 完成安装 |
| `❌ PROMPT_DIR 不存在` | 工具资产缺失 | 重新执行 `bash install.sh` |
| `❌ 指定的旧文档路径不存在` | `旧文档=path` 中的路径有误 | 检查路径是否相对于当前工作目录 |
| `{step} 未输出 [!SUCCESS] 块` | 子进程执行失败或超时 | 检查 `.logs/` 下对应步骤的日志文件 |

---

## 13. 注意事项

- **平台限制**：当前版本仅支持 macOS
- **SKILL 版本**：项目内的 SKILL 与工具仓库版本绑定，仓库更新后需重新执行 `install.sh`
- **Prompt 单一真源**：Prompt 模板的单一真源在工具仓库的 `.gemini/skills/archaeology-commander/resources/prompts/`；修改 `.ai-knowledge/prompts/` 内的文件在本地立即生效，但重新执行 `install.sh` 后会被覆盖
- **脚本版本同步**：修改 `scripts/knowledge-archaeology/run-archaeology.sh` 后，需重新执行 `install.sh` 将最新版本同步到 `.ai-knowledge/scripts/`
