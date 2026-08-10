---
description: qpon-bigdata 核心意图路由与防御性编码军规
globs: **/*
trigger: always_on
---

# qpon-bigdata 开发军规

> 适用：`dags/` 权威的 Composer/Airflow 数仓编排仓（NON_JAVA）。  
> 知识库根：`qpon-bigdata-knowledge/`。禁止以 `scripts/` 或其它目录替代业务事实。

## 第一章：意图路由协议

**强制首读**：任何涉及本服务的任务，先读 `qpon-bigdata-knowledge/00_Master_Catalog.md`，从场景路由表确定本次任务所需的知识文件。

**场景分流**（按场景路由表执行）：
- 快速上手 → 00 → 01 → 05 → 08a / manifest
- 改 DAG / 调度依赖 → 05 → 02 → 06 → 对应 08x
- 排障 Sensor / 绿仍错 → 06 → 07 → 03 → 对应 08x
- 改标签 → 08j → 04 → 05 → 08g
- 改 ES / 出口 → 08k → 08a → 03（对照 08h/08m 吞绿）
- 运维 Dataproc / kill / 清理 → 08m → 06 → 03
- 测试包隔离 → 08n → 01 → 04
- 新增/改表或分区 → 04 → 05 → 对应 08x
- 告警 / 监控静默 → 07 → 08l → 08a
- device_active / DAU SLA → 08g → 08j → 08h → 08k
- 改小时批等待 → 06 → 08f → 08c（反例：08k alarm_h、08n test_d）

**禁止**：未读取相关知识文件就直接全库搜索或修改 `dags/` 代码。

**Skill 优先**：考古流水线调度优先走指挥官/既有 Skill；本军规管业务仓改码与双写。

---

## 第二章：防御性编码红线

### 编排与 Sensor

🔴 **[G-HR-01]** 小时批跨 DAG 等待必须用 `create_external_task_skip_sensor_hour`（Skip 语义）；禁止对小时链路使用日批 `create_external_sensor`（retries=1000）。  
来源：06 §8 G-06-02；08f/08k/08n（`dwd_h`、`alarm_h`、`test_d→dwd_h` 反例）。违反后果：小时失败语义错误、slot 风暴、Skip 军规假闭环。

🔴 **[G-HR-02]** 禁止复制 `qpon_dwd_h`「日工厂等 `qpon_ods_h`/`qpon_dim_h`」模式；新增小时依赖以 `qpon_dim_h` / `qpon_dws_h` / `qpon_rpt_h` Skip 为正样本。  
来源：08f RELAY；08c/08d。违反后果：小时批与日批对齐语义错乱，上游 SKIPPED 无法透传。

🔴 **[G-SEN-01]** 禁止在无 Composer slot/`up_for_reschedule` 容量评估下提高日批 Sensor `retries`（当前 1000）或降低 `poke_interval`；仓内无 `pool=` 不得假设有池隔离。  
来源：07 G-07-01；08a C-08a-01。违反后果：调度队列打满，层间等待假死。

🔴 **[G-SEN-02]** 禁止新增仅挂在 `start_new_task`、不门控业务任务的 `wait_check_allowed_hours_is_run` 类空转边。  
来源：06 G-06-06。违反后果：误导依赖、噪音告警、假门控。

### 数据与 SQL

🔴 **[G-SQL-01]** 订单/结算类 ODS MERGE 若仅 `ON id`，禁止假设跨 Datastream 分表全局唯一；JOIN/去重须显式核对分表键（对照三键安全样本）。  
来源：08b/08c/08e RELAY。违反后果：跨分表串单、MERGE 覆盖错误行。

🔴 **[G-SQL-02]** 分区事实表变更必须走 DELETE+INSERT（或同文件已有 MERGE）；禁止无分区键全表覆盖误写；禁止把 `digital_food_*` 当仓内可写目标层。  
来源：05 C-05-01/02；04 RELAY。违反后果：历史分区被毁或写穿源库镜像。

🔴 **[G-DAY-01]** 对账 ADS/DAU/业务日 **禁止**使用：meta `date.today`、监控/alarm `datetime.now()`、GenAI fallback 时钟、`TimeDeltaSensor`、`data_options.current_date`、测包墙钟延时。业务日以 DAG `execution`/分区键/`tag_qpon_metadata.latest_dayno` 等权威水位为准。  
来源：08k–08n RELAY。违反后果：假对账、错日指标外发。

### 异常与下游防腐（NON_JAVA 映射）

🔴 **[G-EX-01]** 禁止在需失败可见的路径 `except` 后仅 `print`/`pass`/`return` 仍让 Task SUCCESS；既有吞绿路径（meta/ops/rpt ES）必须按 G-ES-01 标注且不得当作出口已验；禁止用裸 `Exception` 掩盖业务上下文。  
来源：07；08k/08l/08m（映射模板「禁止 catch 后 return null/false」）。违反后果：故障静默、排障无迹、开放债假关闭。

🔴 **[G-TO-01]** 新增/修改 ExternalSensor、HTTP/ES/Cloud Run、飞书、Pub/Sub 消费调用时，必须显式配置或继承工厂已在 `02`/`08a` 登记的 `timeout`/`poke_interval`/`retries`；禁止依赖未文档化的隐式默认。  
来源：02 工厂签名；03 下游；07；08a（映射模板「RPC 必须配置超时」）。违反后果：链路卡死或过早失败不可控，下游雪崩。

### ES 与旁路

🔴 **[G-ES-01]** 必须区分：**吞绿**（meta load 吞异常、ops `task_write_es`、rpt `*_es` except print）vs **raise 红**（生产 `qpon_data_server_d` ES 任务）。禁止把 TI SUCCESS / 测包 BQ 绿当作 ES 出口已验。  
来源：08k/08l/08m/08n RELAY。违反后果：ES 失败静默放行或误杀可恢复任务。

🔴 **[G-ES-02]** Cloud Run ES 写入必须传稳定 `id_field`；写失败必须 `raise`（生产红路径）；禁止生产路径 `print` ES password/api_key。  
来源：06 G-06-05；07 G-07-06；08a。违反后果：重复文档、假绿、Task Log 凭据泄漏。

### 告警与运维

🔴 **[G-OPS-01]** 部署/变更后必须核对：`gcp_monitoring_alert` 已 **Unpause**，且 Variable **`gcp_alter_webhook_url` 非空**。  
来源：07 §7.d / G-07-05；08l/08n 开放债 #1。违反后果：Pub/Sub→TT 整链静默。

🔴 **[G-OPS-02]** 告警治理顺序强制：先接线 `etl_alter_webhook_url` + `TeamtalkRobot` 到业务/`on_failure_callback`，再删除硬编码 `yzjtoken`；禁止只删硬编码或只配 Variable 不接线。  
来源：07 G-07-08；08a/08l–08n 开放债 #2。违反后果：「Variable 已配但告警不可达」；多轨 token 失控。

🔴 **[G-OPS-03]** 业务 DAG 禁止新增硬编码 `yzjtoken` / 飞书 `FEISHU_APP_SECRET`；飞书必须 `Variable.get`。  
来源：01 RF-1/2；07 G-07-02/07；08a。违反后果：密钥入库、无法轮换吊销。

### 测试包与 SLA

🔴 **[G-TEST-01]** 测试包 ExternalSensor 的 `external_dag_id` 须为 `*_test`（或文档化例外）；禁止新增对生产 ODS 主任务 / `spark_*ephemeral` / `Qpon_Adjust_Raw_Data` 的 Sensor；已知指向 `qpon_dim_d` 的债禁止复制。  
来源：08n C-08n-01/02 开放债 #7。违反后果：测链挂生产水位、假隔离。

🔴 **[G-TEST-02]** 测 SQL 隔离键=目标表名后缀 `_test` / `_test_all_d`（可同 dataset）；禁止把 `insert_table_id` 改成无后缀生产表名；禁止扩大对生产事件/标签源的混读。  
来源：08n C-08n-04/05。违反后果：覆盖生产分区、联调数字不可外推。

🔴 **[G-SLA-01]** 评估 `dws_qpon_device_active_*` 变更的下游 SLA 时，评估集固定为 **tag ∪ rpt-d ∪ analyst-serving**；不得用 test-dags 或小时 rpt 代替。  
来源：08g/08j/08h/08k 开放债 #5。违反后果：低估扇出、漏改标签/报表/出口。

---

## 第三章：知识库双写协议

代码变更提交前，必须执行知识库资产审计：

| 代码变更类型 | 必须同步更新的知识文件 | 更新内容 |
|---|---|---|
| 新增/修改 DAG 入口或调度 cron / Sensor 边 | 05_Business_Orchestration.md、02_External_Contracts.md | 入口映射 + Sensor 边 + 对应 08x |
| 新增/修改工厂函数或 `airflow_config` API | 02_External_Contracts.md、08a | 签名 + 默认 retries/timeout |
| 新增/修改 BQ 表/字段/分区/MERGE 键 | 04_Data_Model_and_Lifecycle.md、对应 08x | FQN + 生命周期 + ON 键 |
| 新增/修改下游 HTTP/ES/飞书/Dataproc/PubSub | 03_Downstream_Dependencies.md、07 | 调用点 + Variable + 超时 |
| 新增/修改 Sensor/Skip/TimeDelta/补偿 | 06_Async_Jobs_and_Compensation.md | 重试矩阵 + 失败模式 |
| 新增/修改 Variable/告警/可观测 | 07_Config_and_Observability.md、08l | 配置项 + Unpause/接线状态 |
| 新增/修改标签或 `tag_qpon_metadata` | 08j、04 | 宽表 + 水位 + Sensor |
| 新增/修改 ES 写删任务 | 08k 或 08h/08m（按包）、08a | raise vs 吞绿 + index |
| 新增/修改测试包 | 08n、01 | Sensor 目标 + 表后缀隔离 |
| 项目骨架/包树/中间件变更 | 01_Module_Skeleton_and_Stack.md | 包树 + Red Flags |
| 模块增删（Step08 范围） | 05_module_manifest.json、00_Master_Catalog.md | id/name + 导航 |

**自检清单**（每次提交前强制执行）：
> 🔍 [知识库资产审计]：本次代码变更是否导致现有架构资产过期？[是/否]  
> `[ ]` 02 契约 `[ ]` 03 依赖 `[ ]` 04 数据模型 `[ ]` 05 编排  
> `[ ]` 06 异步 `[ ]` 07 配置 `[ ]` 08x 业务模块 `[ ]` 00 总目录/开放债  
> 如有过期，必须连带输出对应 `.md` 文件的更新 Diff。

---

## 第四章：项目特有约束

1. **权威边界**：业务事实只认工作区 `dags/`；知识产出写 `qpon-bigdata-knowledge/`。NON_JAVA：无 pom/Dubbo 节标 N/A，不得因 Java 路径缺失熔断。
2. **开放债清单（改码不得假装已关闭）**：见 `00_Master_Catalog.md` §4.3 八项——Unpause+`gcp_alter`；etl 先接线；吞绿 vs raise；禁止旁路时钟当业务日；device_active 三方 SLA；hour-Skip 未闭环；测包 dim Sensor + 表后缀；`dwd_h` 日工厂 + MERGE ON id。
3. **日报偏移**：修改 `qpon_daily_report` 或 `qpon_rpt_d` cron 必须同步重算 `execution_delta`（当前 +8h）。来源：06 G-06-03。
4. **Dataproc**：ODS 等待活 DAG=`spark_ug_rch_send_record_ephemeral`；删簇保持 `trigger_rule=all_done`。来源：06 G-06-04；08m。
5. **完单口径**：日批 voucher 售后 `COMPLETED`→`RETURN` 与小时 voucher_h 透传不同义；禁止混用。来源：08e/08f/08i。
6. **维表 2999**：读商户/商品维须对账业务日分区 vs `2999-12-31` 当前镜像，勿只看 TI 绿。来源：08d/08g/08h。
7. **task 导出名**：`create_composer_*` 约定函数名=模块名；例外文件须在 PR 单独核对。来源：02。

---

## 第五章：知识库盲区行为规范

1. **未覆盖代码**：若触及知识库未点名的 `tasks/*.py` 或新 DAG 包，先补读邻近 08x + 04/05 相关节，再在对应 08x 或 05 追加锚点；禁止静默假设「与现网一致」。
2. **冲突裁决**：代码事实 > 知识库 > Legacy（本仓 NO_DOCS）。发现知识过期时，先改代码侧验证，再双写知识；不得为贴合旧 md 而改错代码。
3. **无法证实**：OCR/截断/环境外配置（Composer 实际 Unpause、Variable 运行时值）必须显式标注「待运行时确认」，禁止写成已关闭开放债。
4. **测包不等于生产**：测包无 ES、可挂生产 dim——任何「已在 test 验证」声明必须对照 08n 红线逐条自检。
5. **禁止取巧**：承诺「我会排查/修复」前，须给出将打开的物理文件路径或 grep/Sensor 边证据；否则承诺无效（服从 collaboration-protocol）。
