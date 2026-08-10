# qpon-bigdata.mdc / qpon-bigdata.md 合规性审计报告

**审计时间**：2026-07-31  
**审计对象**：`.cursor/rules/qpon-bigdata.mdc`、`.gemini/rules/qpon-bigdata.md`  
**对照基线**：`qpon-bigdata-knowledge/00_Master_Catalog.md`  
**项目类型**：NON_JAVA（Airflow / Cloud Composer / `dags/`）  
**模板**：`step-audit-rules.md`（Java 检查项按 NON_JAVA 语义映射）

> **硬约束回显**：Step08 八项开放债在本审计中**全部保持 OPEN**，禁止假关闭。证据见下文 §4 与军规第四章第 2 条、第五章第 3 条。

---

## 1. 审计结果总览

| 审计项 | 初审 | 终审 | 说明 |
|--------|------|------|------|
| [A1] 全局入口 | ✅ | ✅ | 强制首读 `qpon-bigdata-knowledge/00_Master_Catalog.md` |
| [A2] 场景分流 | ✅ | ✅ | 11 条场景路径（≥8）；与 Catalog §3 对齐（Catalog 另有「性能/slot」场景，军规由 G-SEN-01 覆盖） |
| [A3] 禁止盲目搜索 | ✅ | ✅ | 明确禁止未读知识库即全库搜索/改 `dags/` |
| [B1] 封杀原生异常 | ❌ | ✅ | 初审缺显式异常红线；已补 **G-EX-01**（映射「禁止 catch 后 return null/false」→ 禁止 except 后假绿 SUCCESS） |
| [B2] 微服务防腐规约 | ❌ | ✅ | 初审缺显式超时防腐；已补 **G-TO-01**（映射「RPC 必须配置超时」→ Sensor/HTTP/ES/飞书/PubSub 显式 timeout） |
| [B3] 并发安全机制 | ✅ | ✅ | G-SEN-01（slot/retries）、G-SQL-02（分区写）、G-TEST-02（测包隔离）映射「分布式锁/缓存防腐」意图 |
| [C1] 触发条件 | ✅ | ✅ | 双写表 11 类（≥8），覆盖 DAG/工厂/BQ/下游/Sensor/配置/标签/ES/测包/骨架/manifest |
| [C2] 自我反思拦截词 | ❌ | ✅ | 初审仅有弱问句；已改为硬编码 `🔍 [知识库资产审计]：…？[是/否]` |
| [C3] 连带输出要求 | ✅ | ✅ | 「如有过期，必须连带输出对应 `.md` 文件的更新 Diff」 |

**初审通过率**：6/9  
**终审通过率**：9/9  
**双端正文一致性**：已复检（frontmatter 除外 body 相等）

---

## 2. NON_JAVA 语义映射说明

| 模板 Java 措辞 | 本仓等价意图 | 军规落点 |
|---|---|---|
| 禁止 catch 后 return null/false | 禁止 Task except 后 print/pass 假绿；吞绿须标注 | G-EX-01 + G-ES-01 |
| RPC 必须配置超时 | Sensor/HTTP/ES/飞书/PubSub 显式 timeout | G-TO-01 |
| 缓存 Repository / 分布式锁 | Composer slot 不盲目抬 retries；分区幂等写；测包隔离 | G-SEN-01 / G-SQL-02 / G-TEST-02 |
| Dubbo 接口场景 | 改 DAG/工厂契约 / ES 出口 | 场景分流 + 双写 02/08a/08k |
| Job/MQ | Sensor/Skip/TimeDelta/PubSub | 双写 06；场景「改小时批等待」「排障」 |

---

## 3. 未通过项补丁（已应用）

### [B1] 封杀原生异常补丁

```mdc
### 异常与下游防腐（NON_JAVA 映射）

🔴 **[G-EX-01]** 禁止在需失败可见的路径 `except` 后仅 `print`/`pass`/`return` 仍让 Task SUCCESS；既有吞绿路径（meta/ops/rpt ES）必须按 G-ES-01 标注且不得当作出口已验；禁止用裸 `Exception` 掩盖业务上下文。  
来源：07；08k/08l/08m（映射模板「禁止 catch 后 return null/false」）。违反后果：故障静默、排障无迹、开放债假关闭。
```

### [B2] 微服务防腐规约补丁

```mdc
🔴 **[G-TO-01]** 新增/修改 ExternalSensor、HTTP/ES/Cloud Run、飞书、Pub/Sub 消费调用时，必须显式配置或继承工厂已在 `02`/`08a` 登记的 `timeout`/`poke_interval`/`retries`；禁止依赖未文档化的隐式默认。  
来源：02 工厂签名；03 下游；07；08a（映射模板「RPC 必须配置超时」）。违反后果：链路卡死或过早失败不可控，下游雪崩。
```

### [C2] 自我反思拦截词补丁

```mdc
> 🔍 [知识库资产审计]：本次代码变更是否导致现有架构资产过期？[是/否]  
> `[ ]` 02 契约 `[ ]` 03 依赖 `[ ]` 04 数据模型 `[ ]` 05 编排  
> `[ ]` 06 异步 `[ ]` 07 配置 `[ ]` 08x 业务模块 `[ ]` 00 总目录/开放债  
> 如有过期，必须连带输出对应 `.md` 文件的更新 Diff。
```

## 补丁应用指令

以上 3 个补丁已**同时**写入：

- `.cursor/rules/qpon-bigdata.mdc`
- `.gemini/rules/qpon-bigdata.md`

复检后 9/9 通过。

---

## 4. Step08 八项开放债（强制保持 OPEN — 禁止假关闭）

对照 `00_Master_Catalog.md` §4.3 与军规第四章第 2 条。审计结论：**全部仍为开放债**，军规仅固化「不得假装已关闭」约束，**不视为已修复**。

| # | 开放债 | 军规锚点 | 审计状态 |
|---|---|---|---|
| 1 | Unpause `gcp_monitoring_alert` + `gcp_alter_webhook_url` 非空 | G-OPS-01；Ch4 #2 | **OPEN** |
| 2 | 先接线 `etl_alter_webhook_url`+TeamtalkRobot，再删硬编码 TT | G-OPS-02；Ch4 #2 | **OPEN** |
| 3 | 区分吞绿 vs ES raise 红；禁测包 BQ 绿代替 | G-ES-01 / G-EX-01；Ch4 #2 | **OPEN** |
| 4 | 禁止旁路时钟当 ADS/业务日 | G-DAY-01；Ch4 #2 | **OPEN** |
| 5 | device_active SLA = tag ∪ rpt-d ∪ analyst-serving | G-SLA-01；Ch4 #2 | **OPEN** |
| 6 | hour-Skip 未闭环（alarm_h / test_d→dwd_h） | G-HR-01；Ch4 #2 | **OPEN** |
| 7 | 测包 dim Sensor 债 + 表后缀隔离 | G-TEST-01/02；Ch4 #2 | **OPEN** |
| 8 | `dwd_h` 日工厂等小时 + MERGE ON id | G-HR-02 / G-SQL-01；Ch4 #2 | **OPEN** |

**假关闭拦截**：第五章第 3 条要求运行时未证实事项标注「待运行时确认」，禁止写成已关闭开放债。本报告不将上述任一项标为 CLOSED。

---

## 5. 与 00_Master_Catalog 对照摘要

| 检查点 | 结果 |
|---|---|
| 知识库入口路径一致 | ✅ |
| 场景分流覆盖 Catalog 主场景 | ✅（11 条；Catalog「性能」由 G-SEN-01 承载） |
| 开放债 §4.3 八项入库军规 | ✅ 且保持 OPEN |
| 双写覆盖 Catalog 所列变更面 | ✅ |
| Cursor/Gemini frontmatter 分端正确 | ✅（Cursor=`alwaysApply`；Gemini=`trigger`；无交叉污染字段） |
| 双端正文一致 | ✅ |

---

## 6. 最终审计结论

规则文件满足知识库三大目的（意图路由、防御性红线、知识库双写）。初审 3 项缺口已双端补丁并复检通过。Step08 八项开放债在 Catalog 与军规中均以 **OPEN** 形式保留，本审计未假关闭。

---

> [!SUCCESS] Rules 审计闭环验证
> - 审计范围：qpon-bigdata.mdc + qpon-bigdata.md（双端）
> - 审计结果：9/9 通过（初审 6/9 → 终审 9/9）
> - 补丁应用：3 个补丁已双端应用（G-EX-01、G-TO-01、C2 拦截词）
> - 开放债：8/8 保持 OPEN（禁止假关闭）
> - 最终状态：9/9 通过 ✅
> - EOF 状态：已确认遍历至最后一行，无静默截断
