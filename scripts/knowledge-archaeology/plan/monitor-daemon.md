# 待办：常驻监控 Chat 守护进程（Monitor Daemon）

> **状态**：设计草案，未开发。记录思路与难点供后续参考。
> **关联文档**：`ARCHITECTURE.md §十`（已移至本文件）

---

## 1. 设计动机

当前流水线的可观测性依赖两种被动手段：
1. 轮询日志文件（`tail -f *.log`）
2. 心跳文件时间戳监控（`heartbeat.log`）

两者都需要人工盯守，且无法主动汇报、归因或提出建议。

**核心痛点**：当子进程卡死、配额耗尽、产出质量异常时，指挥官无法自主感知，需要人工介入后才能定位。

**设想**：起一个独立的常驻 Chat 会话（Monitor Daemon），专职监控流水线状态，主动汇报进度、识别异常、生成执行摘要，形成「双会话」架构：

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│   指挥官会话（Commander）     │     │   监控会话（Monitor Daemon）   │
│                             │     │                              │
│  Step 0 → Step 01 → ...    │────▶│  轮询日志 / 读取心跳 / 汇报   │
│  子进程孵化 / 状态传递       │     │  异常归因 / 进度摘要 / 建议   │
└─────────────────────────────┘     └──────────────────────────────┘
         写入                                    读取
    .logs/latest/*.log              .logs/latest/*.log
    heartbeat.log                   heartbeat.log
    pipeline-monitor-log.md    ───▶ pipeline-monitor-log.md（写入）
```

---

## 2. 三条实现路径对比

### 路径 A：Gemini CLI 新会话（gemini -y）

**原理**：在独立终端启动第二个 `gemini -y` 会话，加载监控专用 Skill（`monitor-daemon`），通过轮询文件系统感知指挥官进度。

**触发方式**：
```bash
# 在另一个终端手动启动，或由 run-archaeology.sh 在 preflight 阶段 fork
gemini -y  # 然后输入：激活监控守护进程 run_id=2026-03-19_172544
```

**优点**：复用现有 Gemini CLI 基础设施，无额外依赖，天然支持自然语言汇报。

**缺点**：Gemini CLI 交互式会话本身不支持定时触发，轮询依赖模型主动发起工具调用，长时间运行稳定性存疑。

---

### 路径 B：Cursor Chat 新会话（手动 Agent 模式）

**原理**：在 Cursor 中手动新建一个 Chat，使用 Agent 模式，持续调用文件读取工具轮询日志，形成对话式监控看板。

**触发方式**：手动新建 Chat，输入启动指令，传入 `run_id`。

**优点**：
- 可与 Cursor 编辑器无缝集成，直接在 IDE 内看到汇报
- 支持随时追问（「Step 05 产出了什么？」「当前最大的风险是什么？」）
- 零改动即可验证，适合作为 MVP

**缺点（与路径 C 对比的本质局限）**：

| 特性 | 手动 Chat Agent（路径 B）| 真正的守护进程 |
|------|--------------------------|---------------|
| 生命周期 | 依赖用户不关闭窗口 | 独立进程，后台运行 |
| 触发机制 | 模型主动「选择」继续轮询 | 定时器 / 事件驱动 |
| 可靠性 | context 溢出后失效，无 crash recovery | 进程崩溃可被 supervisor 重启 |
| 启动方式 | 手动（需人工同步启动）| 可由脚本自动 fork |
| CI / 无头环境 | 不适用 | 适用 |

路径 B 的本质是**在对话轮次里模拟轮询**，不是真正的守护进程。模型在 context 接近上限时会停止主动发起工具调用，是根本性缺陷。

**定位**：路径 B 适合作为零成本 MVP，用来验证「增量读取」「context 消耗估算」「幂等性」等核心假设，验证通过后再切换到路径 C。

---

### 路径 C：Cursor CLI `create-chat`（推荐演进方向）

**原理**：通过 Cursor CLI 以脚本方式启动 headless Chat 会话，由 `run-archaeology.sh` 在 preflight 阶段自动 fork 到后台，生命周期由脚本完全管控。

**触发方式**：
```bash
# preflight 阶段自动拉起，PID 写入 .tmp/monitor.pid
cursor chat --model claude-3-5-sonnet \
  --message "激活监控守护进程 run_id=${RUN_ID}" \
  > "${LOG_DIR}/monitor-daemon.log" 2>&1 &
echo $! > .tmp/monitor.pid

# Step Final 完成后由脚本主动 kill
kill $(cat .tmp/monitor.pid) 2>/dev/null
```

**优点**：
- 可编程启动，无需人工介入
- PID 管理，生命周期完全受控（preflight 拉起，Step Final 后 kill）
- 不依赖 IDE 窗口是否打开，适合 CI / 远程服务器
- 标准输出可重定向，监控日志本身可被记录

**当前难点**：
- Cursor CLI 的 `create-chat` 是否支持「持续监听、多轮主动发起工具调用」的守护模式**尚未验证**——这是最大的未知数
- Context window 上限问题与路径 B 相同（模型层面无区别），需要增量读取策略配合
- headless Chat 的自然语言输出如何可靠解析为结构化告警，需要额外的提取层

---

## 3. 监控守护进程的核心职责

| 职责 | 输入来源 | 输出 |
|------|----------|------|
| 进度追踪 | `.logs/latest/` 文件列表 + 时间戳 | 当前执行到第几步 |
| 异常检测 | `heartbeat.log` 最后更新时间 | 心跳停止告警（超过 60s）|
| 质量门禁 | 各 `step-xx.log` 中的 `[!SUCCESS]` 提取 | 哪些步骤缺失 SUCCESS 块 |
| 配额感知 | 日志中的 `429` / `quota` 关键词 | 配额耗尽告警 + 建议切换模型 |
| 执行摘要 | 所有已完成步骤的 `[!SUCCESS]` 块 | 滚动摘要，写入 `pipeline-monitor-log.md` |
| 问答服务 | 用户追问 + 已读日志 | 对任意步骤的即时解释 |

---

## 4. 关键难点与验证项

### 难点 1：轮询频率 vs Context 消耗

**问题**：Monitor 需要定期重读日志文件，每次读取都消耗 token。间隔太短（10s）→ context 溢出；间隔太长（5min）→ 实时性丧失。

**验证项**：
- [ ] 测试单个 `step-xx.log` 的平均大小（当前观测约 1-6KB）
- [ ] 估算 10 步完整日志的累计 token 消耗
- [ ] 验证「只读新增内容（增量读取）」是否可行：记录上次已读行号，只读新增行
- [ ] 验证 Gemini CLI / Cursor Agent 是否支持「只读文件尾部 N 行」的工具调用

### 难点 2：跨会话通信无原生支持

**问题**：指挥官会话和监控会话之间没有进程间通信机制，只能通过文件系统共享状态。

**验证项**：
- [ ] 验证「信号文件」方案可行性：指挥官在每步开始时写入 `.tmp/current-step.txt`，Monitor 读取
- [ ] 验证 `pipeline-monitor-log.md` 作为双向通信信道的可行性（指挥官写进度，Monitor 写告警）
- [ ] 评估是否需要引入 named pipe / FIFO，或继续坚持纯文件方案

### 难点 3：Monitor 自身的生命周期管理

**问题**：Monitor Daemon 应该在流水线结束后自动退出，而不是一直轮询空日志。

**验证项**：
- [ ] 验证「终止信号文件」方案：指挥官在 Step Final 完成后写入 `.tmp/pipeline-done.flag`，Monitor 检测到后优雅退出
- [ ] 验证路径 C（Cursor CLI headless）能否在检测到终止信号后通过 `kill PID` 被外部结束
- [ ] 验证路径 A（Gemini CLI）会话能否响应 `/quit` 命令实现优雅退出

### 难点 4：监控汇报的幂等性

**问题**：Monitor 每次轮询都可能读到同一批日志，需要保证不重复写入 `pipeline-monitor-log.md`。

**验证项**：
- [ ] 验证「已处理步骤集合」的状态维护：Monitor 在内存中记录已汇报的步骤 ID，跳过重复处理
- [ ] 验证跨轮询的状态持久化：Monitor 会话重启后，如何从 `pipeline-monitor-log.md` 中恢复已处理状态

### 难点 5：多项目并发监控

**问题**：同时对多个项目运行流水线时，Monitor 如何区分不同的 `run_id` 和日志目录？

**验证项**：
- [ ] 验证「run_id 隔离」方案：Monitor 启动时接收 `run_id` 参数，只监控对应的 `.logs/{run_id}/` 目录
- [ ] 验证 `pipeline-monitor-log.md` 的多 run_id 分区写入格式

---

## 5. 最小可行原型（MVP）设计

**路径 B 验证**（零代码改动，下次跑流水线时即可执行）：

在流水线运行时，手动在 Cursor 新建 Chat，输入：
```
请每隔 30 秒读取 ai-knowledge-knowledge/.logs/latest/ 目录，
汇报新增的日志文件和其中的 [!SUCCESS] 块。检测到 heartbeat.log
超过 60 秒未更新时发出告警。检测到 pipeline-done.flag 时停止。
每次只读取新增文件，不重读已汇报过的文件。
```

**验证成功标准**：
- [ ] Monitor 能在流水线全程（约 30 分钟）内保持活跃，不因 context 溢出而失效
- [ ] 配额耗尽事件能在发生后 1 次轮询内（≤ 60s）被识别并告警
- [ ] `pipeline-monitor-log.md` 中的进度记录与实际日志文件一一对应，无遗漏、无重复
- [ ] Monitor 在检测到 `pipeline-done.flag` 后能在 1 次轮询内自动停止

若以上验证通过，再推进路径 C（Cursor CLI `create-chat` headless 方案）的实现。

---

## 6. 与现有架构的关系

Monitor Daemon 是**纯读取**的旁观者，不参与指挥官的任何决策：

- 不需要修改 `run_pipeline.py` / `run-archaeology.sh` 任何逻辑
- 不需要修改任何 Prompt 模板
- 唯一的协议扩展：指挥官在 Step Final 完成时写入 `.tmp/pipeline-done.flag`（一行代码，可选）

MVP 验证完全可以在**零代码改动**的前提下进行。 