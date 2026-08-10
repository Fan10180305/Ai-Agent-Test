# 业务模块深潜：archaeology (考古执行器逻辑)

### A. 模块定位
`archaeology` 模块是本项目的核心执行引擎与认知中枢。它不仅包含 12 个引导式分析模板（Prompt Templates），还包括调度脚本 `run-archaeology.sh` 中的状态机逻辑。它实现了从“探测物理事实”到“生成语义知识”的闭环，是跨长会话、高冗余 Token 环境下的“金鱼记忆”解决方案。

### B. 核心组件职责
| 组件 | 类型 | 职责 |
| :--- | :--- | :--- |
| `run-archaeology.sh` | 调度引擎 (Bash) | 负责流程串联、Agent 孵化、Stdout 拦截、异步心跳及 Step 08 动态循环驱动。 |
| `Commander (001)` | 认知指挥官 (AI) | 负责认知接力 (Cognitive Relay)，解析摘要、替换变量并生成下一步 Prompt。 |
| `Executor Agent` | 短效分析员 (AI) | 执行原子考古任务，产出带有 `[!SUCCESS]` 标记的标准化 MD 文档。 |
| `Prompt Templates` | 引导规约 (MD) | 定义各步骤的扫描意图、审计红线及 NON_JAVA 映射规则。 |

### C. 入口功能/方法
| 入口功能 | 物理实现 | 描述 |
| :--- | :--- | :--- |
| **Cognitive Relay** | `ask_commander()` | 核心状态中转。提取 `$step.log` 中的摘要并注入下一步模板。 |
| **Dynamic Module Loop**| `main() -> Step 08` | 基于 `05_module_manifest.json` 动态构建子任务序列。 |
| **Execution Sandbox** | `run_step()` | 孵化拥有独立 Token 预算的 Agent，防止长链路上下文爆炸。 |
| **Async Heartbeat** | `start_heartbeat()` | 后台进程，通过 Python3 实时解析 `transcript.jsonl` 以追踪 Agent 进度。 |

### D. 调用链引用
引用自 `05_Business_Orchestration.md`：
`run-archaeology.sh` -> `ask_commander` -> `.tmp/next-prompt.md` -> `run_step` -> `Executor Agent` -> `[!SUCCESS] 块` -> `get_result_summary` -> 下一步循环。

### E. 前序步骤验证
- **Step 02**: 确认了脚本参数对 `PROJECT_NAME` 和 `OUTPUT_DIR` 的依赖。
- **Step 03**: 确认了对 `cursor` CLI、`jq` 和 `python3` 的二进制依赖。
- **Step 04**: 确认了 `.tmp/next-prompt.md` 作为唯一无锁状态文件的合法性。

### F. 衍生约束清单
| 约束 ID | 约束内容 | 代码证据 | 严重级别 |
| :--- | :--- | :--- | :--- |
| **C-ARCH-01** | `[!SUCCESS]` 必须在 Log 最后 25 行内完整呈现。 | `run-archaeology.sh:L539` | 🔴 核心 |
| **C-ARCH-02** | 严禁使用 macOS 专有 `sed -i ''`，需兼容 Linux。 | `run-archaeology.sh:L265` | 🔴 物理 (CI 崩溃) |
| **C-ARCH-03** | NON_JAVA 模式下严禁因 Java 路径缺失而熔断。 | `prompts/*.md` [Context] | 🟡 语义 |
| **C-ARCH-04** | 指挥官响应超时硬编码为 1800s，需注意大文件延迟。 | `run-archaeology.sh:L429` | 🟡 性能 |

### G. 认知接力 (Cognitive Relay) 深度解析
- **实现本质**: 一种基于物理文件交换的分布式状态机。
- **决策支点**: 指挥官（Commander）不仅是变量替换器，更是**意图修正器**。它根据前序步骤的“遗留问题”动态调整下一步的任务权重。
- **风险**: 若 `get_result_summary` 提取到的摘要包含幻觉或关键信息缺失，错误会沿着接力链条无限放大。

### H. 演进模式与审计审计 (Evolution Mode)
- **核心逻辑**: 通过对比旧知识库与当前代码事实，输出 10 个审计字段（如 `事实修正`、`无意义重写判定`）。
- **底线要求**: 代码事实是唯一权威。禁止“先入为主”地接受旧文档的架构描述。
- **写回策略**: 最小化变更原则。若无实质性事实修正，严禁因文风调整而重写整个章节。

### I. NON_JAVA 语义映射规约
- **意图映射层**: 处于 Prompt 模板层。执行 Agent 需将 `pom.xml` 自动映射为项目的依赖管理文件（如 `package.json`），将 `MyBatis` 映射为等价 ORM。
- **物理拦截**: 模板显式声明“熔断指令自动失效”，强制 AI 执行语义推理而非物理路径匹配。

### J. 异步监控与心跳机制
- **技术栈**: `Bash 后台进程` + `Python3 JSONL 解析`。
- **脆弱性**: 强依赖 `transcript.jsonl` 的文件权限与格式一致性。若 CLI 版本升级导致 JSON 结构变化，监控将失效。

---
事实修正：[补充了 sed -i '' 的 macOS 专有风险、摘要提取的 25 行脆弱性约束]
章节保持：[模块定位、核心组件清单、入口功能]
章节补充：[超时机制影响、心跳机制脆弱性分析]
章节重写：[NON_JAVA 语义映射规约，明确了其作为模板层指令的本质]
删除章节：[无]
结构调整原因：[无]
无意义重写判定：[否]
最小证据：[无]
退化风险申报：[无]

[!SUCCESS] 考古执行器逻辑 模块深潜闭环验证
- 扫描范围：run-archaeology.sh + 12 个分析模板
- 提取结果：4 个分析意图映射、4 条衍生约束、4 个业务特性章节
- EOF 状态：已确认遍历至最后一行，无静默截断

[!RELAY] 定向审计约束
- **物理事实 (Context)**: 指挥官超时硬编码 1800s；摘要提取依赖 `grep -A 25`；存在 `sed -i ''` 兼容性硬伤。
- **推演约束 (Constraint)**: 下一步（基础设施模块 08c）需重点审计 `install.sh` 是否也存在类似的平台依赖性，并核实日志收集逻辑在 `EXIT` trap 触发时的原子性。
- **物理锚点 (Anchors)**: run-archaeology.sh:L265 (sed), L429 (timeout), L539 (grep), L525 (trap EXIT)
