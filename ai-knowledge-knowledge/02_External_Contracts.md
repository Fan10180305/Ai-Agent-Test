# 02_External_Contracts (对外契约审计)

### 1. 核心接口清单 (脚本入口与工具链)

本项目作为非 Java 项目，其对外“承诺”体现为安装脚本的分发接口、调度脚本的命令行参数以及 AI Skill 的交互协议。

| 接口名称 | 调用方式 | 入参/位置参数 | 输出/副作用 |
| :--- | :--- | :--- | :--- |
| **安装分发** | `bash install.sh` | `[--allow-self-install]` | 初始化 `.ai-knowledge/` 环境，同步 Prompt 模板，生成 `config.json` |
| **考古调度** | `bash run-archaeology.sh` | `<Display_Name>` (位置 1)<br>`[Legacy_Paths...]` (位置 2+) | 驱动 8 步分析流水线，生成全量知识库；通过环境变量 `CURSOR_MODEL` 指定模型 |
| **环境清理** | `bash uninstall.sh` | `[--purge]` | 安全卸载工具链，可选清空历史产出目录 |
| **指挥官 Skill** | `activate_skill archaeology-commander` | 自然语言指令 | 唤起 001 会话持久层，开始任务编排与 Prompt 生成循环 |

---

### 2. DTO/请求/响应对象清单 (数据契约)

#### 2.1 项目配置对象 (config.json)
- **物理位置**: `.ai-knowledge/config.json` (由 `install.sh` 生成)
- **字段定义**:
  - `project_name` (String): 项目显示名称
  - `project_dir` (Path): 目标项目绝对路径
  - `output_dir` (Path): 知识库产出目录 (默认 `${project_name}-knowledge`)
  - `tool_home` (Path): `.ai-knowledge` 物理路径
  - `prompt_dir` (Path): 模板存储路径 (默认 `${tool_home}/prompts`)
  - `installed_from` (Path): 工具仓库源路径
  - `cursor_cmd` (Path): IDE 命令行工具路径

#### 2.2 模块清单对象 (module_manifest.json)
- **物理位置**: `ai-knowledge-knowledge/05_module_manifest.json` (Step 05 产出)
- **契约约束**: 数组对象，驱动 Step 08 循环。
- **核心字段**:
  - `id` (String): 模块物理目录名 (必填，用于 `jq` 遍历与 `find` 定位)
  - `name` (String): 模块业务描述名
  - `complexity` (Enum): `high` | `medium` | `low`

#### 2.3 AI 认知接力对象 (next-prompt.md)
- **物理位置**: `${OUTPUT_DIR}/.tmp/next-prompt.md`
- **结构约定**: 遵循 **RCAC (Role-Context-Action-Constraint)** 8 层架构的 Markdown 文本。
- **作用**: 001 指挥官与执行 Agent 之间的“上下文 DTO”。脚本通过 `cat` 读取该文件并经 stdin 传给执行层 AI。

#### 2.4 审计闭环块 ([!SUCCESS])
- **结构约定**: Markdown 引用块格式，包含固定字段（如 `WRITE_TARGET`, `WRITE_RESULT` 等）。
- **作用**: 流水线步骤成功的物理标志，解析失败将导致“认知接力”熔断。

---

### 3. 枚举与常量定义清单

| 常量/枚举名称 | 物理定义位置 | 取值范围/取值示例 | 业务含义 |
| :--- | :--- | :--- | :--- |
| **`STEP_LIST`** | `run-archaeology.sh` L82 | `step-0-legacy` ~ `step-07-config` | 主流程原子步骤序列 (顺序不可调换) |
| **`SUFFIXES`** | `run-archaeology.sh` L93 | `a, b, c, ..., z` | 模块深潜文件 (08a-08z) 的索引后缀 |
| **`CURSOR_MODEL`** | `run-archaeology.sh` L96 | `auto` (默认), `opus-thinking` | 指定执行层 AI 的计算模型 |
| **`CURSOR_AGENT_FLAGS`** | `run-archaeology.sh` L97 | `--print --yolo --model ${MODEL}` | 执行 Agent 的非交互式强制参数集 |
| **`max_wait`** | 编排协议约定 | `1800` (秒) | 脚本等待 AI 写文件的超时阈值 |

---

### 4. 常量定义清单 (路径与环境)

- **`LEGACY_DOCS_DIR`**: `old-readme/` (收集用户提供的旧文档副本)
- **`PROTOCOL_TARGET`**: `.cursor/rules/collaboration-protocol.mdc` (IDE 行为准则注入点)
- **`TRANSCRIPT_BASE`**: `~/.cursor/projects/.../agent-transcripts` (心跳监控的数据源)

---

### 5. 子包结构全景图 (NON_JAVA 项目结构)

```text
ai-knowledge/ (Root) [2 scripts]
├── scripts/knowledge-archaeology/ (调度核心) [4 files]
│   ├── run-archaeology.sh (API Entry)
│   ├── logs/ (Internal Persistence)
│   └── test/ (Verification Layer)
├── .ai-knowledge/ (运行时/分发层) [4 categories]
│   ├── prompts/ (Internal Contracts - 12 templates)
│   ├── config.json (Runtime DTO)
│   └── collaboration-protocol.md (Rule Source)
├── .gemini/skills/archaeology-commander/ (AI 能力契约)
└── ai-knowledge-knowledge/ (最终产出 - 知识持久层)
```

---

### 6. 接口依赖与契约耦合分析

1.  **二进制工具强耦合 (⚠️ 环境红线)**:
    - `jq`: 必须存在，用于解析所有 JSON 契约。
    - `sed`: 强耦合 BSD 风格 (`-i ''`)，仅限 macOS 环境。
    - `python3`: 强耦合，用于心跳监控中 `transcript.jsonl` 的实时流式解析。
2.  **CLI 会话协议耦合**:
    - 强依赖 `Gemini/Cursor CLI` 的 `--print --yolo --resume` 标志位。
3.  **Prompt 变量契约**:
    - 脚本通过 `sed` 向 `.ai-knowledge/prompts/` 模板注入 `{{project_name}}`, `{{output_dir}}` 等变量。若模板变量名变更，注入将失效。

---

### 7. 旧文档交叉验证摘要

- ✅ **已验证**: 旧文档声称的“8 步流水线”与 `STEP_LIST` 定义完全一致。
- ✅ **已验证**: `05_module_manifest.json` 作为动态循环驱动源的逻辑在代码中得到确认。
- 🆕 **新发现**: 识别到 `install.sh` 中的 `--allow-self-install` 是一个未在旧文档中披露的调试/自举接口。
- 🆕 **新发现**: 发现脚本对 `python3` 的依赖不仅是可选的，而是心跳监控（L420+）的硬性要求。

---

> [!SUCCESS] 对外契约测绘闭环验证
> - 扫描范围：`install.sh`, `run-archaeology.sh`, `05_module_manifest.json`, 12 个 Prompt 模板
> - 提取结果：4 个脚本接口、4 个核心数据结构 (JSON/Markdown)、5 组枚举/常量类
> - 子包覆盖：scripts, runtime, skills, knowledge
> - 旧文档差异：❌不符 0 条 / 🆕新发现 2 条 / ✅其余已验证
> - EOF 状态：已确认遍历 `run-archaeology.sh` 至 L742 行，契约逻辑提取完整。
