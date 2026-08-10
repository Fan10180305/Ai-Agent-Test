# 03_Downstream_Dependencies (下游依赖全量测绘)

### 1. 外部工具/API 消费者全量清单

本项目作为一个 AI 驱动的考古流水线，其外部依赖主要集中在 **AI 执行引擎** 与 **数据/脚本工具链**。

| 序号 | 依赖项名称 | 角色/用途 | 来源 (PATH/API) | 超时/限制 | 配置来源 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Gemini CLI** | 核心 AI 执行引擎 | 系统 PATH | N/A (依赖 API Quota) | `README.md` / `USAGE.md` |
| 2 | **Cursor CLI** | 备选/平行 AI 引擎 | `/Applications/Cursor.app/...` | 1800s (指挥官响应) | `.ai-knowledge/config.json` |
| 3 | **jq** | JSON 解析与数据提取 | 系统 PATH | N/A | `run-archaeology.sh` |
| 4 | **Python 3** | 心跳监控日志解析 | 系统 PATH | 6s (轮询频率) | `run-archaeology.sh` L420 |
| 5 | **Bash (4.x+)** | 脚本逻辑运行环境 | `/bin/bash` | N/A | `run-archaeology.sh` L2 |
| 6 | **Unix 工具集** | `sed`, `grep`, `find` 等 | 系统 PATH | N/A | POSIX/BSD 环境 |

---

### 2. 实际调用点追踪

#### 2.1 Gemini CLI 调用
- **调用场景**：流水线步骤的实际执行层（执行 Agent）。
- **物理锚点**：`.gemini/skills/archaeology-commander/SKILL.md`
- **调用方式**：`cat ${NEXT_PROMPT} | gemini -p '' --yolo --model ${MODEL}`
- **耦合度**：**重度**。项目逻辑高度依赖 Gemini CLI 的管道输入与非交互模式（`--yolo`）。

#### 2.2 Cursor CLI 调用
- **调用场景**：初始化指挥官会话（Commander）及步骤执行。
- **物理锚点**：`run-archaeology.sh:L310` (init), `L544` (executor)
- **调用方式**：`$CURSOR_CMD agent create-chat` / `$CURSOR_CMD agent --resume $ID`
- **耦合度**：**重度**。作为当前调度器的主要 AI 载体，负责维持长会话状态。

#### 2.3 jq 调用
- **调用场景**：读取项目配置及循环处理业务模块。
- **物理锚点**：`run-archaeology.sh:L46` (config), `L615` (manifest)
- **调用逻辑**：从 `.ai-knowledge/config.json` 提取参数，从 `05_module_manifest.json` 提取模块 ID。
- **耦合度**：**中度**。结构化数据的提取核心。

#### 2.4 Python 3 调用 (隐形关键依赖)
- **调用场景**：实时解析 Cursor Agent 的 `.jsonl` 运行日志，提取当前正在执行的动作摘要。
- **物理锚点**：`run-archaeology.sh:L491` (heartbeat)
- **调用逻辑**：`tail -1 $file | python3 -c "import sys, json; ..."`
- **耦合度**：**中度**。虽不参与核心逻辑，但决定了无人值守模式下的监控可见性。

---

### 3. 配置与容错审计

#### 3.1 全局环境配置
- **指挥官等待超时**：`max_wait=1800` (30分钟)。脚本轮询检测 `${OUTPUT_DIR}/.tmp/next-prompt.md` 是否生成的硬上限。
- **心跳轮询频率**：`sleep 6` (6秒)。心跳监控进程提取日志摘要的频率。
- **重试机制**：本项目目前**无自动重试逻辑**。遵循 `set -e` 原则，任一命令失败即触发流水线熔断。

#### 3.2 熔断降级逻辑
- **Bash 军规**：全局开启 `set -euo pipefail`，确保管道中任一环节失败都能被捕获。
- **前置检查 (Preflight)**：在 `run-archaeology.sh:L310` 之前检查 `PROTOCOL`, `CURSOR_CMD`, `jq`, `PROMPT_DIR` 的存在性，不满足则拒绝启动。
- **哨兵校验**：`SKILL.md` 中规定必须从日志中成功提取 `[!SUCCESS]` 块，否则判定为该步失败。

---

### 4. 外部协议交互协议 (Gemini/Cursor API)

本项目不直接通过 HTTP 请求调用远程 API，而是通过 **CLI 管道协议** 进行交互：
1. **Stdin 注入**：将渲染好的 Markdown Prompt 通过管道传入 CLI。
2. **Stdout 捕获**：CLI 将 AI 响应流式输出，由脚本重定向至 `${LOG_DIR}/${step_name}.log`。
3. **副作用观测**：AI 通过 `run_shell_command` 或 `write_file` 对本地工作区产生物理变更，由后续脚本进行审计。

---

### 5. 外部依赖拓扑图

```ascii
[ 用户终端 ]
      |
      v
[ run-archaeology.sh (Bash 4.x) ] <------ [ .ai-knowledge/config.json ]
      |
      +--- [ jq (JSON 解析) ]
      |
      +--- [ Python 3 (日志心跳提取) ]
      |
      +--- [ sed/find (文本/文件操作) ]
      |
      +-----------------+-----------------+
      |                 |                 |
      v                 v                 v
[ Gemini CLI ]    [ Cursor CLI ]    [ 本地文件系统 ]
      |                 |                 |
      +------ API ------> [ 远程 LLM 服务 ] <--- (Gemini-2.0-flash / Opus / Thinking)
```

---

### 6. Step 01 遗漏追踪

- 在 Step 01 中发现的 `python3` 依赖已在本项目中确认，其物理坐标位于 `run-archaeology.sh` 的心跳监控函数中。
- **修正项**：Step 01 将 `python3` 标记为“辅助工具”，实际审计发现其在监控逻辑中不可或缺，且在 `preflight` 检查中存在缺失（见下文风险分析）。

---

### 7. 旧文档交叉验证摘要

- ✅ **已验证**：旧文档声称支持 `Gemini CLI` (0.33.2+) 和 `jq`。
- ❌ **不符**：旧文档声称兼容 Linux，但代码中的 `sed -i ''` (run-archaeology.sh L357) 是典型的 macOS/BSD 风格，在 Linux 环境下会抛出 `sed: -i may not be used with stdin` 错误。
- 🆕 **新发现**：发现 `Python 3` 的 `json.load` 脚本块被内嵌在 Bash 字符串中，存在逃逸风险且缺乏环境预检。

---

### 8. 演进与风险申报

- **事实修正**：将 `python3` 从“可选”提升为“心跳监控核心依赖”。
- **风险申报 (RED_FLAG)**：
  - **环境缺陷**：`preflight` 函数检查了 `jq` 和 `cursor`，但**漏检了 `python3`**。若环境无 Python，监控将静默失效。
  - **平台锁定**：`sed -i ''` 导致工具在 Linux 容器环境下无法直接运行，与“兼容 Linux”的初衷漂移。
  - **超时僵尸**：30 分钟的 `max_wait` 缺乏动态衰减机制，在 AI 响应极快或极慢时缺乏弹性。

---

> [!SUCCESS] 下游依赖测绘闭环验证
> - 扫描范围：`install.sh`, `run-archaeology.sh`, `SKILL.md`, `USAGE.md`
> - 提取结果：4 个核心外部二进制工具 (Gemini CLI, Cursor CLI, jq, Python3)、2 个关键超时配置 (1800s/6s)
> - 幽灵依赖：0 个；漏检依赖：1 个 (Python3 未在 preflight 校验)
> - 超时配置：指挥官等待 1800s，心跳频率 6s
> - Step 01 遗漏追踪：已确认 Python3 的核心监控地位
> - 旧文档验证：2 项已验证 / 1 项不符 (Linux 兼容性) / 1 项新发现 (内嵌 Python 逻辑)
> - EOF 状态：已确认遍历 `run-archaeology.sh` 至 L742 行。

[!RELAY] 定向审计约束
- **物理事实 (Context)**: 心跳监控依赖 `python3` 解析 `~/.cursor/projects/.../agent-transcripts/` 下的 JSONL 文件。
- **推演约束 (Constraint)**: Step 04 应重点关注此路径下的 JSONL 结构，将其作为执行 Agent 状态流转的“动态数据模型”。
- **物理锚点 (Anchors)**: `run-archaeology.sh:L480` (TRANSCRIPT_BASE), `L491` (_extract_transcript_hint)
