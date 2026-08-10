# Step 06: 异步机制与补偿全量测绘

[Role] 异步架构审计师。
你的任务是从代码中还原本服务的全部异步机制——
定时任务、MQ 生产/消费、补偿策略、重试逻辑。
这些是线上问题的高发区：Job 挂了没人知道、消息丢了没补偿、重试没有幂等。
你同时承担"衍生约束提炼"职责——从发现的事实中提炼出 AI 未来编码时必须遵守的约束。

[Context]
我们正在为 {{project_name}}（{{project_display_name}}）构建 AI 可加载的项目知识库。
已完成步骤（具体数字由 001 根据前序产出动态注入）：
- Step 0: 旧文档声称（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已确认 RocketMQ、CloudJob、Lock4j 三个异步相关框架接入
- Step 03: 下游依赖 — 已完成，超时与容错配置已记录
- Step 04: 数据模型 — 已完成，补偿相关表结构已记录
- Step 05: 业务编排 — 已完成，业务链路中的异步环节已初步发现

已知关键线索（由 001 根据前序步骤动态注入）：
{{step06_prior_findings}}

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件，建立先验认知：
1. {{output_dir}}05_Business_Orchestration.md — 业务链路中的异步环节
2. {{output_dir}}04_Data_Model_and_Lifecycle.md — 补偿相关表结构
3. {{output_dir}}03_Downstream_Dependencies.md — §3 超时与容错配置
4. {{output_dir}}01_Module_Skeleton_and_Stack.md — §4 RocketMQ/CloudJob/Lock4j 配置
如有旧文档：{{output_dir}}Legacy_{{project_name}}_Claims.md — §6 异步机制声称、§8 待确认项
{{evolution_mode_context}}

[Task: 异步机制全量测绘]

### 扫描范围

**区域 A：定时任务（Job）**
- {{project_name}}-app/src/main/java/**/job/ — 全部 Job 类
- 逐文件读取至 EOF

**区域 B：MQ 生产者（Publisher）**
- {{project_name}}-service/src/main/java/**/publisher/ — 全部 Publisher 类
- 搜索全项目 @RocketMQ 相关注解、RocketMQTemplate 使用点

**区域 C：MQ 消费者（Listener）**
- {{project_name}}-app/src/main/java/**/listener/ — 全部 Listener 类
- 搜索全项目 @RocketMQMessageListener、MessageListenerConcurrently 等消费者注解/接口

**区域 D：补偿与重试机制**
- 搜索全项目中与补偿相关的类（Compensate、Retry、Rollback 关键词）
- 扫描 @Scheduled、@Retryable 等注解使用
- 搜索 Lock4j / 分布式锁相关代码（@Lock4j 注解或 LockTemplate 使用）

**区域 E：MQ 配置**
- {{project_name}}-start/src/main/resources/ 中与 MQ 相关的配置
- 全项目搜索 Topic 常量定义、Producer/Consumer Group 定义

### 提取任务

#### 1. 定时任务全量清单
扫描必须全量（区域 A 每个 Job 类逐文件读取至 EOF），**每个 Job 输出以下 5 项**：

a) 类名 + cron 表达式（代码中可见时原样摘录，不可见时标注「配置中心配置」）
b) 执行摘要：execute/run 方法的一句话描述（调用了什么、处理了什么数据，不超过 30 字）
c) 操作的数据表 + 查询条件（查询的状态值）
d) 风险标注：
   - 无分布式锁 → ⚠️并发风险
   - 无异常处理 / 吞异常 → ⚠️失败静默
   - 无幂等保障 → ⚠️重复执行风险
   - 调用了写操作 RPC 且 retries>0 → 🔴重复写入风险
   - Job 内查询分片表且 SQL 无分片键 WHERE 条件 → 🔴全分片扫描（必须在表格列中标注，不允许仅在风险详情段落中提及）
e) 依赖的外部服务（如果 Job 中调用了 RPC，列出接口名）

**输出格式（每个 Job 一行表格行，不分块）**：
| Job 类名 | cron | 执行摘要 | 操作表/状态 | 风险标注 | 外部依赖 |

在表格后，对有 ⚠️/🔴 标注的 Job，逐个补充一段「风险详情」（不超过 3 行）。

#### 2. MQ 生产者全量清单
对每个 Publisher 类提取：
a) 类名 + Topic 名称
b) 消息体类型 + 发送方式（同步/异步/单向）
c) 被哪个业务方法调用
d) 发送失败处理策略

汇总表格：
| Publisher 类名 | Topic | 消息体类型 | 发送方式 | 调用方 | 失败策略 |

#### 3. MQ 消费者全量清单
对每个 Listener/Consumer 类提取：
a) 类名 + 订阅 Topic + Consumer Group
b) 消费逻辑摘要（processMessage 调用了什么，一句话）
c) 幂等处理（幂等键是什么）
d) 消费失败处理策略

汇总表格：
| Listener 类名 | Topic | Consumer Group | 消费摘要 | 幂等键 | 失败策略 |

#### 4. 补偿机制深度解析
对本服务中所有补偿机制，逐个解析：
a) 补偿场景（什么情况触发补偿）
b) 补偿入口（哪个 Job 或方法）+ 补偿数据来源（表名 + 状态值）
c) 最大重试次数 / 最终失败处理
d) 幂等保障（补偿操作是否幂等，幂等键是什么）

#### 5. 分布式锁使用清单
汇总表格：
| 使用位置（类名.方法名） | 锁 key 表达式 | 超时时间 | 获取失败策略 | 保护的临界资源 |

#### 6. Topic/Group 配置全景
汇总所有 MQ 相关配置：
| Topic 名称 | Producer Group | Consumer Group | 消息方向 | 发送方 | 消费方 |

如有旧文档待确认的 MQ 消费方项，在本节末尾逐一给出明确结论。

#### 7. 异步机制风险矩阵

**范围限定**：仅包含异步机制（Job / MQ / 补偿流程），分布式锁不属于异步机制，不得列入本矩阵。

| 机制名称 | 幂等保障 | 失败处理 | 监控告警 | 风险等级 |

风险等级：🔴 高风险（无幂等 + 无失败处理）/ 🟡 中风险（有幂等但无监控，或无重试上限）/ 🟢 低风险

#### 8. 衍生约束清单
| 约束编号 | 约束内容（一句话，可执行） | 来源事实（第 N 节具体发现） | 严重级别 |
| G-06-XX | ... | ... | 🔴强制/🟡建议 |

约束提炼原则：只从代码事实中衍生；🔴 强制：违反会导致线上事故；🟡 建议：增加风险但不立即出事。
**可执行性要求**：约束内容必须包含可验证的具体行为（禁止/必须+动词+对象），涉及数量/阈值的约束必须给出具体数值（如「每批不超过 N 条」「超过 N 次标记 FAIL」），禁止写模糊表述（如「应当注意」「建议处理」）。

[Action]
在 {{output_dir}} 目录下生成 06_Async_Jobs_and_Compensation.md

[Constraint - 工业级底线]

**输出格式锁定**：使用以下标题结构
```
### 1. 定时任务全量清单
### 2. MQ 生产者全量清单
### 3. MQ 消费者全量清单
### 4. 补偿机制深度解析
### 5. 分布式锁使用清单
### 6. Topic/Group 配置全景
### 7. 异步机制风险矩阵
### 8. 衍生约束清单
### 9. 旧文档交叉验证摘要（有旧文档时输出，NO_DOCS 时跳过）
```

**第 9 节格式（有旧文档时）**：
只列出差异条目：❌不符 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条，其余均已代码验证」。
待确认项必须逐一给出明确结论。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若核心扫描目标路径在工作区内不存在，应按 NON_JAVA 规则映射或如实记录，禁止推断替代路径，禁止访问工作区外目录。

**扫描完整性保证**：
- 扫描必须全量：区域 A~E 每个文件逐一读取至 EOF，不允许跳过
- 输出必须提炼：§1 Job 用表格行格式，不逐个展开子节

**专业性底线**：
- Job 的 cron 表达式原样记录，不翻译为自然语言
- 异常处理策略写代码事实（catch Exception 后 log.error），不评判好坏
- 风险矩阵基于代码中可见的机制评估，不假设「可能有但我没看到的」保障

**结尾标准审计闭环**：

> [!SUCCESS] 异步机制测绘闭环验证
> - 扫描范围：app/job/ + service/publisher/ + app/listener/ + 全局锁搜索
> - 提取结果：[X] 个 Job、[Y] 个 Publisher、[Z] 个 Listener、[W] 个分布式锁点
> - 补偿机制：[N] 个独立补偿流程
> - 风险评估：🔴 [A] 个高风险 / 🟡 [B] 个中风险 / 🟢 [C] 个低风险
> - 衍生约束：[D] 条（🔴 [E] 条强制 / 🟡 [F] 条建议）
> - 旧文档差异：❌不符 [G] 条 / 🆕新发现 [H] 条 / ✅其余 [I] 条已验证（NO_DOCS 时标注 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对配置与可观测性分析有决定性影响的异步事实，如：高风险 Job 的关键配置项、补偿机制依赖的锁配置、消息队列的超时设置等]
> - **推演约束 (Constraint)**: [基于异步机制发现，强制 Step 07 重点审计的配置项或监控盲区]
> - **物理锚点 (Anchors)**: [对应 Job/Listener 类文件路径及配置引用行号]
