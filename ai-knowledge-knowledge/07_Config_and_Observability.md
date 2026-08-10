# 07_Config_and_Observability (配置体系与可观测性全量测绘)

本模块定义了 `ai-knowledge` 的配置加载优先级、环境变量依赖、退出码规范以及基于实时日志的心跳观测体系。

## 1. 配置项决策清单 (Configuration)

本项目采用“配置驱动型流水线”，加载优先级为：**运行时推导 < 配置文件 (config.json) < 环境变量**。

### 1.1 物理配置文件 (`.ai-knowledge/config.json`)
由 `install.sh` 生成，记录项目静态属性。

| 配置字段 | 默认值/来源 | 用途说明 | 是否可修改 |
| :--- | :--- | :--- | :--- |
| `project_name` | `$(basename $(pwd))` | 内部项目标识。 | 是 |
| `project_dir` | `$(pwd)` | 项目绝对路径。 | 否 |
| `output_dir` | `${PROJECT_NAME}-knowledge` | 知识库输出目录名。 | 是 |
| `tool_home` | `.ai-knowledge/` | 工具包本地安装路径。 | 否 |
| `prompt_dir` | `.ai-knowledge/prompts` | 分析模板存储目录。 | 是 |
| `cursor_cmd` | `[空]` | 可选：手动指定的 Cursor CLI 路径。 | 是 |

### 1.2 运行时环境变量 (Environment Variables)
在 `run-archaeology.sh` 启动前或启动时注入，用于动态调整执行模式。

| 变量名 | 默认值 | 物理锚点 | 核心作用 |
| :--- | :--- | :--- | :--- |
| `CURSOR_CMD` | `/Applications/Cursor.app/...` | `L85` | 驱动 Agent 的执行引擎路径。 |
| `CURSOR_MODEL` | `auto` | `L86` | 指定 AI 模型（如 `thinking`）。 |
| `CURSOR_AGENT_FLAGS` | `--print --yolo --model ${MODEL}` | `L87` | Agent 执行行为控制（非交互式）。 |
| `PYTHON3` | `python3` (硬编码) | `L457` | **[RED FLAG]** 用于解析心跳摘要，未参数化。 |

## 2. 缓存与临时状态全景 (State & Cache)

| 缓存类型 | 存储位置 | 生命周期 | 核心用途 |
| :--- | :--- | :--- | :--- |
| **流水线接力棒** | `${OUTPUT_DIR}/.tmp/next-prompt.md` | 跨步骤持续 | 存储上一步生成的下一步指令。 |
| **Agent 转录轨** | `${HOME}/.cursor/projects/.../agent-transcripts/` | 永久保留 (Cursor 侧) | 心跳监控的数据源。 |
| **步骤日志快照** | `${OUTPUT_DIR}/.logs/${TS}/${STEP}.log` | 持久保留 | 审计 AI 思考过程与工具调用。 |
| **指挥官初始化消息** | `${LOG_DIR}/commander-init-msg.tmp` | 瞬时 | 指挥官 System Prompt 注入中转。 |

## 3. 异常处理体系 (Error Handling)

### 3.1 鲁棒性开关
- **硬熔断**：`set -euo pipefail` (L2)。任何命令失败、变量未定义或管道崩溃均会立即触发脚本退出。
- **清理锁**：`trap 'stop_heartbeat' EXIT` (L529)。确保无论是正常完成、报错退出还是 `Ctrl+C` 中断，后台心跳进程都会被强制 `kill`。

### 3.2 退出码字典 (Exit Codes)
| 退出码 | 含义 | 触发点 | 补偿建议 |
| :--- | :--- | :--- | :--- |
| `0` | SUCCESS | 最后一个 Step 成功闭环 | N/A |
| `1` | GENERIC_FAILURE | 任何 Step 执行失败、超时或配置缺失 | 检查 `${STEP}.log` 或执行器 Stdout |
| `1` | COMMANDER_TIMEOUT | 指挥官在 1800s 内未响应 (L441) | 检查网络连接或 CLI 状态 |

## 4. 可观测性与日志规范 (Observability)

### 4.1 日志三层架构
1. **Pipeline 总纲 (`pipeline.log`)**: 记录流水线各步骤的耗时、Agent ID 和退出码。
2. **Agent 明细 (`${STEP}.log`)**: 捕获执行 Agent 的原始 Stdout/Stderr（包含 AI 思考细节）。
3. **心跳采样 (`${STEP}.heartbeat.log`)**: 每 6s 记录一次进度快照。

### 4.2 实时监控逻辑 (Heartbeat)
通过 `tail -1` 实时监听 Cursor 的 `agent-transcripts`，并调用 Python3 进行语义解析：
- **Turn 数提取**：监控交互轮次，识别 AI 是否陷入死循环。
- **Hint 摘要**：提取 AI 的最后一条 `thought` 或 `tool_use`，实时显示“AI 正在做什么”。
- **锚点**：`run-archaeology.sh:L454 (_extract_transcript_hint)`。

## 5. 衍生约束清单 (Constraints)

| 约束编号 | 约束内容 | 物理证据 | 严重级别 |
| :--- | :--- | :--- | :--- |
| **C-07-01** | **Python3 环境强制要求**。若环境无 `python3`，心跳监控将静默失去 Hint 功能。 | `run-archaeology.sh:L457` | 🔴 强制 |
| **C-07-02** | **30min 超时阈值**。指挥官生成 Prompt 的硬超时为 1800s，无法通过配置调整。 | `run-archaeology.sh:L429` | 🟡 建议 |
| **C-07-03** | **macOS 专有 CLI 路径**。默认 `CURSOR_CMD` 仅兼容 macOS。 | `run-archaeology.sh:L85` | 🔴 强制 |
| **C-07-04** | **目录访问权限**。执行用户必须对 `${HOME}/.cursor/projects/` 有读权限以读取心跳数据。 | `run-archaeology.sh:L88` | 🔴 强制 |

---

### 演进对比记录

- **事实修正**：[修正了 `config.json` 包含 Python 路径和超时的错误假设，代码显示其为硬编码]
- **章节保持**：[保持了日志三层架构描述]
- **章节补充**：[补充了 trap EXIT 的生命周期清理锁逻辑]
- **章节重写**：[根据代码重写了退出码字典与环境变量列表]
- **删除章节**：[无]
- **结构调整原因**：无意义。
- **无意义重写判定**：否。
- **最小证据**：`run-archaeology.sh:L457` (python3 parse), `L529` (trap EXIT)。
- **退化风险申报**：无。

> [!SUCCESS] 配置与可观测性测绘闭环验证
> - 扫描范围：run-archaeology.sh + install.sh + config.json
> - 提取结果：6 个核心配置项、1 个硬编码 Python 依赖、1 个 30min 硬超时门禁
> - 衍生约束：4 条（🔴 3 条强制 / 🟡 1 条建议）
> - 旧文档差异：❌不符 2 条（Python/超时配置项在 config.json 中的存在性）/ ✅其余已验证
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 心跳监控强依赖 `python3` 命令且无配置覆盖点；指挥官超时硬编码为 1800s。
> - **推演约束 (Constraint)**: Step 08 在分析基础设施模块时，必须评估 `python3` 缺失对监控健壮性的影响，并建议将超时时间参数化。
> - **物理锚点 (Anchors)**: `run-archaeology.sh:L457` (python3), `L429` (max_wait)
