# 08m 模块深潜：运维清理与Dataproc接入（ops-staging）

> 模块 id=`ops-staging`；权威范围=`dags/`（重点 `data_options/`、`qpon_staging_d/`、`task_kill/`、`Qpon_Adjust_Raw_Data/`）  
> 不重复 Step05 全链；本步钻取 **Dataproc 删簇补偿**、**Adjust 外部表**、**BQ kill**、**清理/归档失败模式**  
> Step08l 接力：(1) Unpause+`gcp_alter_webhook_url`；(2) 先接线 `etl_alter`+TeamtalkRobot 再删硬编码；(3) meta 吞绿 vs data_server ES raise 红；(4) 禁止 meta/监控/GenAI/alarm 时钟当 ADS 日；(5) device_active SLA=tag∪rpt-d∪analyst-serving；(6) alarm_h 日工厂等小时债仍开  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以用户指令 id=`ops-staging`/suffix=`m` + `step-08-ops-staging_prompt.md` 为准

> [!SUCCESS] 运维清理与Dataproc接入 模块深潜闭环验证
> - 扫描范围：DAG 入口×7（data_options / task_kill / Adjust / spark×3 变体）+ Python/BQ 任务×6 + 本地 Spark 脚本 `spark_mysql_to_bigquery.py`；ODS 消费边作交叉锚点
> - 提取结果：10 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：174 行（≤ 400 行）
> - 前序验证：Step 02 外部表/Sensor / Step 03 Dataproc·Secret·ES·GCS / Step 04 staging·Adjust·ug_rch
> - EOF 状态：四目录 13 文件已读至 EOF；无静默截断

---

## A. 模块定位

`ops-staging` 是仓内**运维清理 / 成本护栏 / 贴源接入旁路**：周五清理 staging 与埋点归档、双分钟杀超限 BQ Job、日批 Dataproc 临时簇同步 MySQL→BQ、以及 Adjust GCS→BQ 外部表；被 `qpon_ods_d` Sensor 消费，**不参与** device_active / ADS / 标签主扇出。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `data_options` | Orchestrator | 周五 `20 16 * * 5`；清理/归档/测试 ES；`retries=0` |
| `clear_staging_his_data` | Executor | 扫 `qpon_staging` 全表 + `ug_rch_send_record` 删 7 日前 CDC 戳 |
| `event_message_to_gcs` | Executor | 原始事件 EXPORT→GCS；稽核一致后删 BQ（>11 日） |
| `dwd_event_traffic_to_gcs` | Executor | DWD traffic 月窗 EXPORT；删逻辑仅入口调用、出口注释掉 |
| `task_write_es` | Executor | 渠道看板样例写 `test_store_sale_statis_dashboard`；**吞异常** |
| `task_kill` / `bq_monitor_kill_jobs` | Orchestrator/Executor | `*/2 0-12` 扫 RUNNING Job；白名单外超阈值 cancel |
| `Qpon_Adjust_Raw_Data` / `CREATE_EXTERNAL_TABLE_QponAdjust` | Orchestrator/Executor | `0 18` CREATE OR REPLACE 安卓/iOS 日外部表 |
| `spark_ug_rch_send_record_ephemeral`（`*_new.py`） | Orchestrator | **活链**：建簇→Spark→UPDATE meta→verify→删簇 `all_done` |
| `spark_ug_rch_send_record_20260421` | Orchestrator | 同构 ephemeral 副本（独立 `dag_id`） |
| `spark_ug_rch_send_record` | Orchestrator | 旧常驻簇 create/start/stop；ODS 已切走 |
| `spark_mysql_to_bigquery` | Executor | 仓内 Spark 脚本样例：Secret→JDBC 分批 APPEND BQ |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `data_options` parse | Composer | 注册清理/归档/ES 四任务（并行于 `start`） |
| DAG `task_kill` parse | Composer | 注册 `bq_monitor_kill_jobs` |
| DAG `Qpon_Adjust_Raw_Data` parse | Composer | 注册外部表 BQ 任务 |
| DAG `spark_ug_rch_send_record_ephemeral` | Composer / ODS Sensor | 活 Dataproc 日同步 |
| `clear_staging_his_data` / `event_message_to_gcs` / `dwd_event_traffic_to_gcs` | data_options | 清理与冷归档 |
| `task_write_es` | data_options | 测试索引 ES 写（无 failure_callback） |
| `bq_monitor_kill_jobs` | task_kill | 按运行时长/槽耗时 cancel |
| `CREATE_EXTERNAL_TABLE_QponAdjust` | Adjust DAG；`qpon_ods_d.wait_*` | 日替换外部表 |
| ephemeral 链五算子 | 同 DAG | create→submit→update→verify→delete |
| `spark_mysql_to_bigquery.main` | Dataproc（GCS 脚本 URI） | MySQL→BQ APPEND |

---

## D. 调用链（引用 Step05，不重复追踪）

- Dataproc：`spark_ug_rch_send_record_ephemeral` → ODS `wait_spark_ug_rch_send_record`（整 DAG、无 `external_task_id`、retries=1000）→ `ods_ug_rch_send_record`（05 §A.13 / 06 §4.5）。
- Adjust：`CREATE_EXTERNAL_TABLE_QponAdjust` → ODS `wait_CREATE_EXTERNAL_TABLE_QponAdjust`（工厂 Sensor）→ `ods_qpon_adjust_raw_data_inc_d`。
- 运维：`data_options` / `task_kill` **无**主链 Sensor 进出；与 metadata 同属旁路。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | Adjust 外部表字段+URI；ODS Sensor 契约 | ✅；`execution_date+2` 日分区命名 |
| 03 下游 | Dataproc、Secret Manager、ES Cloud Run、GCS archive、BQ Jobs API | ✅；无 Pub/Sub/飞书/GenAI |
| 04 实体 | `qpon_staging.*`、`ug_rch_send_record`、Adjust DayNo 表、事件/traffic 冷存 | ✅；清理与 Spark **同表** `ug_rch` |
| 06 异步 | 删簇 `all_done`；ODS 整 DAG Sensor | ✅；见 §G；verify **不 assert** |
| 07 配置 | data_options/task_kill `retries=0`；spark ephemeral `retries=1`；硬编码 TT | ✅；未用 metadata Variable |

**08l 接力回执（本包不消化）**：无 Unpause 三 metadata DAG、无 `gcp_alter`/`etl_alter` 接线、无 meta load、无 ADS 业务日、无 device_active、无 alarm_h。收官仍须保留 08l/08k 全部开放债。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08m-01 | ODS `wait_spark_*` 的 `external_dag_id` 必须指向**活** ephemeral；切换 DAG 时同步改 Sensor，禁止留旧 `spark_ug_rch_send_record` | `qpon_ods_d.wait_spark_ug_rch_send_record`；`*_new.py` | ODS 永不绿或等错链 |
| C-08m-02 | ephemeral 删簇须保持 `trigger_rule=all_done`；禁止改回仅 success 才删；新建同类必须 delete 挂在失败仍可调度的拓扑上 | `DataprocDeleteClusterOperator` | 失败挂费 / 孤儿簇 |
| C-08m-03 | Spark 幂等键语义=`CREATE_MYSQL_WHERE`(日窗+status)+PK `id`；重跑前须知 `WRITE_APPEND` **无先删**——禁止假设重试幂等（已知技术债，禁止复制无 DELETE 的 APPEND） | `spark_mysql_to_bigquery` write；WHERE 宏 | 重复行；ODS 假满 |
| C-08m-04 | `verify_data_integrity` 仅为 SELECT diff，**不得**当作硬门禁；缺口须另加 ASSERT/CheckOperator | ephemeral `verify_data_integrity` | 缺 meta 戳仍 SUCCESS→ODS 推进 |
| C-08m-05 | Adjust 表日=`execution_date+2`；URI 前缀安卓 `4tt61o72u58g_` / iOS `bxxrs0ow1tz4_`；改桶或 app token 须双改；`max_bad_records=100` 允许静默丢行 | `CREATE_EXTERNAL_TABLE_QponAdjust` | ODS 读空/缺日/脏数仍绿 |
| C-08m-06 | `clear_staging_his_data` 用 `current_date()-7` 且 `client.query` **不等待/不检查**；勿与 `execution_date` 对账；改保留期须评估与 Spark 写入并发 | `clear_staging_his_data` | 误删近期 CDC；失败仍绿 |
| C-08m-07 | `task_write_es` 吞异常=**吞绿**（对照 data_server ES raise 红）；测试索引变更禁止当生产就绪信号 | `task_write_es` except print | 假绿；与 08k/08l 口径混淆 |
| C-08m-08 | `bq_monitor_kill_jobs`：白名单 SA/`v-mick` 与空 `user_email` **不杀**；`cdc_background_merge` 跳过；时长阈值为 **8 分钟**（非注释「17 小时」）；禁止扩大白名单掩盖成本 | `bq_monitor_kill_jobs` | 误杀 ETL 或漏杀贵 Job |
| C-08m-09 | 告警仍硬编码 `TtSend` token；治理服从 08l：先接线 `etl_alter`+TeamtalkRobot 再删硬编码；本包不得新增第三条 webhook 轨 | 三入口 `send_url` | 多轨告警；Variable 假覆盖 |

---

## G. Dataproc 删簇补偿与校验空洞

**业务背景**：日批把 MySQL `ug_rch_send_record` 拉进 BQ `market_db_user_growing`，供 ODS 贴源；临时簇避免常驻费用。

**实现方式**：活 DAG=`spark_ug_rch_send_record_ephemeral`（`spark_ug_rch_send_record_new.py`）。动态簇名 `spark-ug-{{ ts_nodash[:15].lower() }}`。链：`create_dataproc_cluster` → `submit_spark_job`（GCS `mysql_to_bigquery_20260421.py`）→ `update_datastream_metadata`（填 `source_timestamp`/`change_type`）→ `verify_data_integrity` → `delete_dataproc_cluster(all_done)`。WHERE：`status in ('SUCC','FAIL')` 且 `create_time`∈`[execution_date+1d, +2d)`。旧 DAG `spark_ug_rch_send_record` 为 create/start/stop 常驻模式；`*_20260421` 为同构第二 ephemeral。

**关键决策点**：
- `delete_dataproc_cluster` — `trigger_rule=all_done` → 上游终态后仍删（资源补偿意图）。
- `CUSTOM_MYSQL_WHERE_CLAUSE` — `execution_date.add(days=1/2)` → 注释自承「处理明天窗」。
- `verify_data_integrity` — 只 SELECT expected/actual/diff → **无失败分支**。
- Spark `main` — `total_rows==0` 直接 return；计数不一致仅 `warning`；异常 `sys.exit(1)`。
- ODS Sensor — 等整 DAG success，不绑定 `delete` 或 `verify` 单任务。

**失败模式**：Spark 失败后删簇仍应调度，但 create 阶段权限/配额失败仍可能留操作痕迹；verify 绿≠戳齐全；APPEND 重跑重复；双 ephemeral+旧 DAG 若同时 schedule 会双写。排障：Composer 以 `*_ephemeral` 为准；查簇名宏、Secret `passwd-mysql-qpon-market-id`、BQ 窗内行与 `source_timestamp IS NULL`。

---

## H. Adjust 外部表接入

**业务背景**：Adjust 日文件落 GCS，BQ 外部表给 ODS/DWD 归因链；与主仓 Sensor 强耦合。

**实现方式**：`schedule=0 18`，`retries=3`。`CREATE OR REPLACE EXTERNAL TABLE` 两张：`Qpon_Adjust_Raw_DayNo` / `Qpon_Adjust_Raw_DayNo_IOS`，表名后缀 `execution_date+2` 的 `YYYYMMDD`；URI 含同日 `YYYY-MM-DD`。CSV+`max_bad_records=100`+`allow_jagged_rows`。

**关键决策点**：
- 分区日 — `add(days=2)` 必须与 ODS 读表日一致。
- `CREATE OR REPLACE` — 同日重跑覆盖表定义（幂等键=项目+dataset+表名日后缀）。
- 坏行配额 — 最多丢 100 行仍 SUCCESS。

**失败模式**：GCS 无匹配对象→外部表空→ODS Sensor 绿但贴源空；字段漂移未改 `table_fields`→查询失败。排障：对账桶前缀与 `+2` 日；勿用 alarm/meta 时钟替代该业务日。

---

## I. BQ Job Kill 护栏

**业务背景**：限制非关键账号长跑/高槽 Job，控制费用。

**实现方式**：`task_kill` `*/2 0-12 * * *`，`retries=0`。`list_jobs(RUNNING, all_users)`→解析 jobId→跳过非法 ID / `cdc_background_merge`→`get_job`→白名单或空邮箱 skip→`running_ms>480000` **或** `slot_ms>86400000`→`cancel()`。文件头注释写「17 小时」，**代码阈值为 8 分钟**。

**关键决策点**：
- 白名单 — compute SA + `v-mick@oppo.com` 永不杀。
- 空 `user_email` — `continue`（不杀）。
- cancel 失败 — print，任务仍绿。
- 调度窗 — 仅 UTC 0–12；下午长跑不在本 DAG 覆盖。

**失败模式**：误杀业务 Job（8 分钟过短）；或白名单过大导致成本护栏失效；REDACTED jobId 分支依赖 `_properties`。排障：先对日志「触发 Kill 规则」与用户邮箱，再对注释/常量是否漂移。

---

## J. 清理与归档失败模式

**业务背景**：控制 staging/埋点热存成本；附带测试 ES 写。

**实现方式**：
- `clear_staging_his_data`：枚举 `qpon_staging` 全表，按 `datastream_metadata.source_timestamp < current_date()-7` 拼 DELETE，500 条一批 `client.query`（**无 result 等待**）；另删同条件 `ug_rch_send_record`。
- `event_message_to_gcs`：导出 `<current_date()-11` 分区→与 `*_ext` 行数稽核→删热表；导出前后各稽核一次。
- `dwd_event_traffic_to_gcs`：导出「上上月整月」窗；**开头** `check_delete_data`，**结尾调用被注释**→本 run 导出后不删。
- `task_write_es`：读 RPT 近 60 日→Cloud Run ES；except 仅 print；**未挂** `failure_callback`。

**关键决策点**：
- 时钟 — 清理/归档一律 `current_date()`，忽略 `logical_date` 形参。
- traffic — 出口删注释 → 依赖下周入口稽核才删。
- ES — 吞绿 vs data_server raise 红（接力强制区分）。
- `start_new_task` — 空挂 Dummy（与出口层同模式，非就绪信号）。

**失败模式**：query 提交失败仍绿；清理与 Spark 同表竞态；traffic 只导出不删致双计费；测试 ES 成功≠看板生产。排障：查 INFORMATION_SCHEMA 与 archive 桶；禁止用本包时钟对账 ADS/DAU。

---

> [!SUCCESS] 运维清理与Dataproc接入 模块深潜闭环验证
> - 扫描范围：13 文件（四目录）+ ODS Sensor 交叉锚点
> - 提取结果：10 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：174 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅ / Step 06 ✅ 删簇+整 DAG Sensor / Step 07 ✅ retries 分层
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 活 Spark=`spark_ug_rch_send_record_ephemeral`（删簇 `all_done`；verify 仅 SELECT）；ODS 整 DAG Sensor→ephemeral；Adjust `+2` 日外部表+`max_bad_records=100`；清理 `current_date`+fire-and-forget query；`task_write_es` 吞绿；kill 阈值=8min 非注释 17h；硬编码 TT 未接 `etl_alter`。08l/08k 债（Unpause+gcp_alter、etl 接线、meta 吞绿 vs ES raise、不可信旁路时钟、device_active 三方、alarm_h 日工厂等小时）**未被本包消化**。
> - **推演约束 (Constraint)**: 下一模块（test-dags / 收官）必须 (1) 核对生产 Unpause+`gcp_alter_webhook_url` 非空；(2) 告警治理优先接线 `etl_alter`+TeamtalkRobot 再删硬编码；(3) 区分 meta/ops「吞绿」与 data_server「ES raise 红」；(4) 对账 ADS/DAU **禁止**用 meta/监控/GenAI/alarm/`data_options.current_date` 当业务日；(5) device_active SLA 评估集仍为 **tag∪rpt-d∪analyst-serving**；(6) 勿假设 hour-Skip 已闭环（alarm_h 反例仍在）；(7) 测试包 Sensor 须指向 test 上游，勿误连本包生产 ephemeral/Adjust。
> - **物理锚点 (Anchors)**: `dags/qpon_staging_d/spark_ug_rch_send_record_new.py` L48–193；`dags/qpon_ods_d/qpon_ods_d.py` L127–137 / L184 / L508 / L713；`dags/Qpon_Adjust_Raw_Data/tasks/CREATE_EXTERNAL_TABLE_QponAdjust.py` L112–151；`dags/data_options/tasks/clear_staging_his_data.py`；`dags/data_options/tasks/dwd_event_traffic_to_gcs.py` L50–51；`dags/data_options/tasks/task_write_es.py` L27–28；`dags/task_kill/tasks/bq_monitor_kill_jobs.py` L40–135；`dags/qpon_staging_d/spark_mysql_to_bigquery.py` L172–216
