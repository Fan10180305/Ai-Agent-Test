# 06_Async_Jobs_and_Compensation — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）；禁止 `scripts/`  
> 语义映射：Java Job/MQ Publisher/Listener/补偿/Lock4j → **DAG 定时调度 + ExternalTaskSensor/SkipSensor/TimeDeltaSensor + PubSubPullSensor + Dataproc 异步链 + Cloud Run ES 写 + TT on_failure_callback + max_active_runs**  
> BQ 锚点：`oppo-gcp-prod-digfood-129869` @ `asia-southeast2`  
> Legacy：NO_DOCS  
> 物理拦截：grep 全仓 Sensor/retries/callback/PubSub/Dataproc/ES；`airflow_config` 10 文件 + 关键 DAG 入口读至 EOF；禁止虚构配置值

> [!SUCCESS] 异步机制测绘闭环验证
> - 扫描范围：`dags/airflow_config/`（Sensor/TT/ES 工厂）+ 全仓 DAG 入口/任务（Job≡DAG；MQ≡Pub/Sub；无 RocketMQ）
> - 提取结果：[36+] 个 Job（DAG 调度单元）、[0] 个 Publisher（无出站 MQ 生产）、[1] 个 Listener（PubSubPullSensor）+ [441+] Sensor 等待边作跨 DAG「消费」、[3] 个分布式锁等价点（`max_active_runs=1`）
> - 补偿机制：[8] 个独立补偿/重试流程（日批 Sensor1000、小时 Skip/20、TimeDelta、daily_report delta、Dataproc 删集群、ES 幂等写、BQ Check24、分区 DELETE+INSERT）
> - 风险评估：🔴 [4] 个高风险 / 🟡 [5] 个中风险 / 🟢 [3] 个低风险
> - 衍生约束：[10] 条（🔴 [6] 条强制 / 🟡 [4] 条建议）
> - 旧文档差异：N/A（NO_DOCS）
> - EOF 状态：已确认关键实现文件遍历至最后一行，无静默截断

---

### 1. 定时任务全量清单

N/A：无 Java `@Scheduled` / CloudJob 类。等价「Job」= **Composer DAG 调度单元**（`schedule_interval` / `schedule`）。  
全量入口以 Step 05 §1 的 36 个 DAG 包为准；下表按**异步语义类别**汇总（同类 cron 合并行，避免 36 行重复展开）。

| Job 类名（DAG） | cron | 执行摘要 | 操作表/状态 | 风险标注 | 外部依赖 |
|---|---|---|---|---|---|
| `qpon_ods_d` | `0 18 * * *` | ODS 日批 MERGE/贴源；直连等 Spark；Adjust Sensor；TimeDelta 门控 | `qpon_ods_d.*`；等待 `success`/`failed` | ⚠️Sensor retries=1000；⚠️TimeDelta retries=1000/2000 | BQ；`spark_ug_rch_send_record_ephemeral`；`Qpon_Adjust_Raw_Data`；TT |
| `qpon_dim_d` / `qpon_dwd_d` / `qpon_dws_d` / `qpon_rpt_d` / `qpon_tag_d` / `qpon_analyst_d` / `qpon_data_server_d` / `qpon_email_date_d` / `qpon_risk_d` | `0 18 * * *` | 日批分层 ETL；工厂 Sensor 串上游 | 各层 `DELETE+INSERT`/`MERGE`；Sensor `allowed_states=['success']` | ⚠️工厂 Sensor retries=1000；🔴写任务依赖 DAG retries（常见 3）无业务幂等锁 | BQ；跨 DAG Sensor；部分 ES/飞书 |
| `qpon_ods_h` / `qpon_dim_h` / `qpon_dwd_h` / `qpon_dws_h` / `qpon_rpt_h` / `qpon_analyst_h` | `10 * * * *` | 小时批；SkipSensor 或 Sensor 等上游 | 常写日批 dataset；小时门控 `ShortCircuit` | ⚠️SkipSensor retries=20；`check_allowed_hours_is_run` 空转边 | BQ；小时上游 DAG |
| `qpon_daily_report` | `0 2 * * *` | 等 RPT 指标后 LLM 叙事发飞书 | 读 RPT 指标；飞书 webhook | ⚠️`execution_delta=+8h`；Sensor retries=100 | `qpon_rpt_d`；GenAI Variable；飞书；TT |
| `spark_ug_rch_send_record_ephemeral`（及旧版 spark_*） | `0 18 * * *` | Dataproc 建簇→Spark→BQ 元数据→校验→删簇 | MySQL→`market_db_user_growing.ug_rch_send_record` | ⚠️DAG retries=1；删簇 `all_done` | Dataproc；MySQL；Secret Manager；BQ |
| `Qpon_Adjust_Raw_Data` | `0 18 * * *` | Adjust 外部表创建 | BQ EXTERNAL TABLE | ⚠️被 ODS Sensor 等待 | Adjust/GCS/BQ |
| `gcp_monitoring_alert` | `*/1 * * * *` | Pub/Sub 拉 Incident 转 TT | 无表；ack Pub/Sub | ⚠️retries=0；解析失败 `continue` | Pub/Sub sub；TT |
| `sync_source_meta` / `sync_bigquery_staging_description` | 分钟/日（见入口） | 元数据同步 | staging/meta | 🟢`max_active_runs=1` | Datastream/BQ API |
| `data_options` / `task_kill` | 周五 / `*/2` | 运维清理/写 ES/杀 BQ Job | ES/BQ Jobs | ⚠️运维面 | Cloud Run ES；BQ |
| `*_test` 包族 | 同生产 cron | 测试镜像 + Sensor→test 上游 | test dataset | 🟡勿混生产 | 测试上游 DAG |
| `qpon_analyst_alarm_{d,h}` | 日/时 | Sensor+Python 告警 | 读 RPT/ADS | 🟢有 failure_callback | TT；上游 Marker/Sensor |
| `qpon_search_store_fea_export` | `0 18 * * *` | 搜索特征导出 | BQ | ⚠️Sensor 参数易混淆 | `qpon_dwd_d` |

**风险详情（有 ⚠️/🔴 者）**：

1. **日批 `create_external_sensor` retries=1000**：覆盖 DAG `default_args.retries`（常见 3）。上游 `failed` 时 Sensor 失败后仍可再试 1000 次，叠加 `timeout=64800`、`poke_interval=600`，长期占用 reschedule slot，延迟「永久失败」判定。锚点：`dags/airflow_config/create_external_sensor.py` L10–24。  
2. **TimeDeltaSensor retries=1000/2000**（如 `qpon_ods_d.wait_14_hours` retries=2000、retry_delay=60min）：延时门本身可极长重试。锚点：`dags/qpon_ods_d/qpon_ods_d.py` L141–171。  
3. **`qpon_daily_report` execution_delta**：日批 RPT `0 18` 与日报 `0 2` 差 8h，靠 `execution_delta=timedelta(hours=8)` 对齐 logical date；配错则永远 poke 不到成功实例。锚点：`dags/qpon_daily_report/qpon_daily_report.py` L143–156。  
4. **`check_allowed_hours_is_run`**：`qpon_dwd_h` 内为 `DummyOperator`（非 SQL 模块）；`qpon_dws_h` 仅 `start_new_task >> wait_*`，**不**门控三条 `dws_feature_*` → 编排空转。锚点见 §4。

---

### 2. MQ 生产者全量清单

N/A：本项目无 RocketMQ / `RocketMQTemplate` / 出站 Pub/Sub Publish Operator。  
唯一消息面为 **入站** `PubSubPullSensor`（见 §3）。无 Publisher 类可枚举。

| Publisher 类名 | Topic | 消息体类型 | 发送方式 | 调用方 | 失败策略 |
|---|---|---|---|---|---|
| （无） | N/A | N/A | N/A | N/A | N/A |

等价「异步出站」旁路（非 MQ）：`TtSend.stream_upload`（失败 `print`）、`access_cloud_run_write_aliyun_es`（HTTP POST）、飞书 webhook、GenAI —— 记入 §4/§7，不记入本表。

---

### 3. MQ 消费者全量清单

N/A：无 `@RocketMQMessageListener`。等价 Listener = **Pub/Sub 拉取传感器** + **跨 DAG Sensor（状态消费）**。

| Listener 类名 | Topic | Consumer Group | 消费摘要 | 幂等键 | 失败策略 |
|---|---|---|---|---|---|
| `gcp_monitoring_alert.wait_for_pubsub`（`PubSubPullSensor`） | subscription=`qpon-data-gcp-component-monitoring-sub` | 同 subscription（GCP） | 拉 1 条 Incident → `monitoring_alert` 发 TT | `ack_messages=True`（拉后 ack） | DAG `retries=0`；单条解析 `except` 后 `continue` |
| `ExternalTaskSensor` / `create_external_sensor`（活边 ≈407+ 工厂调用，Step03 计 441 边量级） | 外部 `dag_id.task_id` 状态 | N/A（Airflow 元库） | poke 上游 `success`；`failed_states=['failed']` | logical date / execution_delta | `retries=1000`；`timeout=64800`；`mode=reschedule`；可选 TT callback |
| `ExternalTaskSkipSensor` / `create_external_task_skip_sensor_hour`（活调用 ≈34） | 同上 | N/A | SUCCESS→成功；SKIPPED→`AirflowSkipException`；FAILED→`AirflowException` | 同 `run_id` 查 TI（见风险） | 工厂 `retries=20`；`timeout=7200`；poke=300 |

**SkipSensor 实现要点**（`create_external_sensor.py` L45–122）：`TaskInstance.get_task_instance(..., run_id=context['run_id'])` —— 跨 DAG 依赖**同一 run_id**；与标准 `ExternalTaskSensor` 的 execution_date 对齐语义不同。上游未启动返回 `False` 继续等；无独立「补偿表」。

**`create_external_sensor_hour`**：已定义（retries=20, timeout=7200），**仓内无活调用**（仅定义处）。

**直连 `ExternalTaskSensor`（非工厂）**：

| 位置 | 配置事实 |
|---|---|
| `qpon_ods_d.wait_spark_ug_rch_send_record` | `external_dag_id=spark_ug_rch_send_record_ephemeral`；**未设** `external_task_id`（等整 DAG）；`retries=1000`；`mode=reschedule` |
| `qpon_daily_report.wait_rpt_business_indicator_summary_d` | `external_dag_id=qpon_rpt_d`；task=`rpt_business_indicator_summary_d`；`execution_delta=+8h`；`timeout=28800`；`poke_interval=600`；`retries=100` |

---

### 4. 补偿机制深度解析

#### 4.1 日批 ExternalTaskSensor 超长重试（retries=1000）

- **场景**：下游层等待上游 task 成功；上游失败或长时间未成功。  
- **入口**：`create_external_sensor` → 几乎所有日批 DAG。  
- **参数**：`timeout=64800`，`poke_interval=600`，`retries=1000`，`allowed_states=['success']`，`failed_states=['failed']`。  
- **最大重试 / 终态**：任务级最多约 1000 次重试；超时后失败并触发 `on_failure_callback`（若传入）。  
- **幂等**：Sensor 本身只读元库状态；下游 BQ 任务依赖各自 SQL（DELETE+INSERT/MERGE）做重跑幂等。  
- **补偿性质**：属「等待补偿」而非业务回滚；高 retries **延长失败暴露**，不是业务补偿表。

#### 4.2 小时批 ExternalTaskSkipSensor（跳过透传）

- **场景**：小时上游被 ShortCircuit/跳过时，下游应跳过而非硬失败。  
- **入口**：`create_external_task_skip_sensor_hour`（dim_h/dws_h/rpt_h/analyst_h/test）。  
- **行为**：上游 SKIPPED → 本 Sensor `AirflowSkipException`（软失败/跳过补偿）；FAILED → `AirflowException` + 可 callback；工厂 `retries=20`。  
- **幂等**：跳过不写数；成功后下游仍靠 SQL 幂等。

#### 4.3 TimeDeltaSensor 调度偏移门控

- **场景**：DAG 触发后人为延迟 1/2/3/12/14 小时再跑贴源或报表。  
- **入口**：`qpon_ods_d` / `qpon_rpt_d` / `qpon_dwd_d` / `qpon_email_date_d` 等。  
- **事实**：多处 `retries=1000`；`wait_14_hours` 为 `retries=2000` + `retry_delay=timedelta(minutes=60)`（`qpon_ods_d` L166–171）。  
- **补偿**：无业务回滚；仅时间门 + 超长重试。

#### 4.4 qpon_daily_report 跨调度 execution_delta

- **场景**：日报 `0 2 * * *`（注释：02:00 UTC = 10:00 UTC+8）等待日批 `qpon_rpt_d`（`0 18 * * *`）的 `rpt_business_indicator_summary_d`。  
- **入口**：直连 `ExternalTaskSensor`，`execution_delta=timedelta(hours=8)`。  
- **最大重试**：`retries=100`，`timeout=28800`。  
- **幂等**：查询/分析/飞书；飞书侧未见去重键（重复跑可能重复推送）。  
- **失败**：各 PythonOperator + Sensor 挂 `failure_callback`。

#### 4.5 Dataproc Spark 异步链 + ODS 直连 Sensor

- **场景**：MySQL `ug_rch_send_record` → 临时 Dataproc → BQ；ODS 再贴源。  
- **入口**：`spark_ug_rch_send_record_ephemeral`（`qpon_staging_d/spark_ug_rch_send_record_new.py`）：`create_cluster >> submit_spark_job >> update_datastream_metadata >> verify_data_integrity >> delete_cluster`。  
- **资源补偿**：`DataprocDeleteClusterOperator` `trigger_rule="all_done"` —— Spark 失败仍删簇，避免挂费。  
- **DAG retries**：`retries=1`；DAG 级 `on_failure_callback=failure_callback`。  
- **ODS 侧**：`wait_spark_ug_rch_send_record` 等整 DAG success，`retries=1000`，再跑 `ods_ug_rch_send_record`。  
- **数据幂等**：Spark WHERE `status in ('SUCC','FAIL')` + 时间窗；BQ `PRIMARY_KEY_COLUMN=id` 传入脚本；元数据 UPDATE 补 `datastream_metadata`。

#### 4.6 Cloud Run ES 写失败重试与幂等

- **场景**：RPT/DWD/data_server/data_options Python 任务写阿里云 ES。  
- **入口**：`access_cloud_run_write_aliyun_es(select_sql, id_field, index_name)`。  
- **重试**：函数内**无**重试循环；失败 `raise Exception`。依赖外层 PythonOperator / DAG `default_args.retries`（常见 3，`retry_delay` 10min）。  
- **超时**：GET `/health` timeout=10；POST `/api/write-to-es` timeout=30。  
- **幂等键**：调用方普遍传 `id_field="id"` 或 `"Id"`，请求体带 `id_field` —— 由 Cloud Run 服务按文档 ID 写入（客户端假定 upsert；**本仓不见服务端源码**）。  
- **删除补偿**：`delete_by_field_condition` 按字段值批量删（`batch_size=1000`）；失败 `raise`；部分批次 `failed` 仅 print，不中断整批（L121–122）。  
- **活调用规模**：`access_cloud_run_write_aliyun_es(` 非注释命中约 22 业务处 + 模块自测；`ElasticsearchWriteOperator` 活 DAG 调用=0。

#### 4.7 悬空/空转上游 `check_allowed_hours_is_run`

- **代码事实（纠正「task 不存在」表述）**：`qpon_dwd_h` L97–99 定义 `DummyOperator(task_id="check_allowed_hours_is_run")`，挂在 `wait_check_allowed_hours`（`ShortCircuitOperator`）之后。允许小时列表见 L83–86。  
- **等待方**：`qpon_dws_h` L102、`qpon_test_d` L112 用 SkipSensor 等待该 task_id。  
- **悬空点**：  
  1. 无对应 `tasks/*.py` 数据模块（非产出任务）；  
  2. `qpon_dws_h` 中 `start_new_task >> wait_check_allowed_hours_is_run` **未**连接到 `dws_feature_*`（L132–148 主链独立）→ Sensor 空转；  
  3. ShortCircuit 跳过时 Dummy 为 SKIPPED，SkipSensor 会 skip —— 但因未门控业务，无业务补偿效果。  
- **结论**：属**编排空转/测试残留边**，不是缺失 task_id；也不是有效失败补偿。

#### 4.8 TT `on_failure_callback` 与「是否掩盖真实失败」

- **入口**：`send_failure_alert_factory` → 多数 DAG `failure_callback`；部分 DAG 级 `on_failure_callback`。  
- **行为事实**（`airflow_tt_send.py` L52–68）：  
  - 读取 `context["exception"]` 到 `error_message`，但 **message 正文未包含 exception**，仅 `execution_date` + `dag_id` + `task_id`。  
  - `TtSend.sendTT` 外层 `try/except Exception: print(e)` —— **告警发送失败被吞掉**，只打控制台。  
  - 回调**不会**把 Airflow 任务改成 success；任务状态仍失败。  
- **结论**：  
  - **不掩盖任务失败状态**（UI/调度仍 failed）。  
  - **掩盖/削弱可观测性**：告警缺异常栈；告警通道失败静默 → 易误判「没告警=没失败」或「只有 task 名不知根因」。  
- **附加缺陷**：`send_tt_alert_factory`（L70–76）`return send_tt_alert` 但函数未定义 —— 若误用会在回调期 NameError（当前主路径用的是 `send_failure_alert_factory`）。

#### 4.9 其他补偿

| 机制 | 入口 | 次数/终态 | 幂等 |
|---|---|---|---|
| `Check_BQ_Data_IsExists_Operator` | `create_check_table_data.py` | `retries=24`，`retry_delay=1h` | Check 只读 |
| 分区 DELETE+INSERT / MERGE | 各 `tasks/*.py` | 依赖 DAG retries | 分区键 / MERGE 键 |
| Pub/Sub ack | `gcp_monitoring_alert` | retries=0 | ack 后不重投；解析失败 skip 单条 |

---

### 5. 分布式锁使用清单

N/A：无 Lock4j / `@Lock4j` / Redis 锁。等价物：

| 使用位置（类名.方法名） | 锁 key 表达式 | 超时时间 | 获取失败策略 | 保护的临界资源 |
|---|---|---|---|---|
| `gcp_monitoring_alert` DAG | `max_active_runs=1` | N/A（调度并发） | 新 run 排队/不启动 | Pub/Sub 消费单飞 |
| `sync_source_meta` DAG | `max_active_runs=1` | N/A | 同上 | 源元数据同步 |
| `sync_bigquery_staging_description` DAG | `max_active_runs=1` | N/A | 同上 | staging 描述同步 |
| 多数业务 DAG | `depends_on_past=False` | N/A | 无跨 run 串行 | **无** past 依赖锁 |

Sensor `priority_weight`（默认 100）仅影响调度优先级，非互斥锁。

---

### 6. Topic/Group 配置全景

| Topic 名称 | Producer Group | Consumer Group | 消息方向 | 发送方 | 消费方 |
|---|---|---|---|---|---|
| `qpon-data-gcp-component-monitoring-sub`（subscription） | N/A（GCP Monitoring→Pub/Sub，仓外） | 同 subscription | 入站 | GCP Alerting（仓外） | `gcp_monitoring_alert.wait_for_pubsub` |
| （跨 DAG 状态「伪 Topic」）`{external_dag_id}.{external_task_id}` | N/A | Sensor task `wait_*` | 状态消费 | 上游 DAG task | 下游 Sensor |
| RocketMQ / 其他 Broker | N/A | N/A | N/A | N/A | N/A |

旧文档 MQ 待确认项：NO_DOCS / 无 Legacy §6 声称 → 跳过。

**工厂默认参数全景（异步配置权威）**：

| 工厂 | retries | timeout | poke | 其他 |
|---|---|---|---|---|
| `create_external_sensor` | **1000** | 64800 | 600 | `failed_states=['failed']` |
| `create_external_sensor_hour` | 20 | 7200 | 300 | 无活调用 |
| `create_external_task_skip_sensor_hour` | 20 | 7200 | 300 | Skip 透传 |
| `Check_BQ_Data_IsExists_Operator` | 24 | — | — | delay 1h |
| `qpon_daily_report` 直连 Sensor | 100 | 28800 | 600 | `execution_delta=+8h` |
| `wait_spark_*` 直连 Sensor | 1000 | （未显式，用默认） | （未显式） | 无 `external_task_id` |

---

### 7. 异步机制风险矩阵

**范围**：仅 Job / MQ / 补偿流程（不含 §5 锁行）。

| 机制名称 | 幂等保障 | 失败处理 | 监控告警 | 风险等级 |
|---|---|---|---|---|
| 日批 `create_external_sensor` retries=1000 | Sensor 只读；下游靠 SQL | 失败可再试 1000；timeout 64800 | 可选 TT callback | 🟡 中风险（无重试上限业务语义 / 长占 slot） |
| 小时 `ExternalTaskSkipSensor` | 跳过不写 | SKIPPED→skip；FAILED→fail+retries=20 | TT callback | 🟢 低风险（设计符合小时语义） |
| SkipSensor 用 `run_id` 对齐 | 依赖同 run_id | TI 找不到则一直等至 timeout | timeout 后 callback | 🟡 中风险（与 ExternalTaskSensor 语义不一致） |
| `TimeDeltaSensor` retries=1000/2000 | N/A | 超长重试 | 多数无单独告警直至最终失败 | 🟡 中风险 |
| `qpon_daily_report` execution_delta=8h | 飞书无去重 | Sensor retries=100；任务 retries=2 | TT | 🟡 中风险（偏移配错则空等；重复推送） |
| Dataproc ephemeral + ODS 整 DAG Sensor | Spark PK/WHERE；删簇 all_done | DAG retries=1；ODS Sensor 1000 | TT | 🟢 低风险（资源补偿清晰） |
| Cloud Run ES 写 | `id_field` 文档 ID | 函数内无重试；靠 DAG retries；raise | TT on task fail | 🟡 中风险（短超时 30s + 依赖外层重试） |
| `check_allowed_hours_is_run` 空转边 | Dummy 无数据 | SkipSensor 空转不门控业务 | 可告警但无业务价值 | 🔴 高风险（误导依赖 / 噪音） |
| TT `on_failure_callback` | N/A | 不改任务状态；告警吞异常且无 exception 正文 | 告警本身可静默失败 | 🔴 高风险（可观测性掩盖） |
| Pub/Sub monitoring | ack 后不重投 | retries=0；解析失败 continue | TT 发送 | 🔴 高风险（丢告警消息无补偿） |
| 分区 DELETE+INSERT 重跑 | 分区键覆盖 | DAG retries | TT | 🟢 低风险 |
| `send_tt_alert_factory` 死代码 | N/A | NameError | 不可用 | 🔴 高风险（若被误用） |

---

### 8. 衍生约束清单

| 约束编号 | 约束内容（一句话，可执行） | 来源事实（第 N 节具体发现） | 严重级别 |
|---|---|---|---|
| G-06-01 | 禁止对新增日批跨 DAG 依赖把 Sensor `retries` 设为 ≥1000；必须显式文档化 timeout/poke，且上游永久失败时不得依赖「靠重试熬过去」 | §4.1 / §6 工厂表 | 🔴强制 |
| G-06-02 | 小时批跨 DAG 等待必须用 `create_external_task_skip_sensor_hour`（或等价 Skip 语义）；禁止对小时链路误用日批 `retries=1000` 工厂 | §3 SkipSensor；§4.2 | 🔴强制 |
| G-06-03 | 修改 `qpon_daily_report` 或 `qpon_rpt_d` 任一方 cron 时，必须同步重算并更新 `execution_delta`（当前代码值为 `timedelta(hours=8)`） | §4.4 | 🔴强制 |
| G-06-04 | ODS 等待 Spark 时必须核对 `external_dag_id` 与活 DAG（当前为 `spark_ug_rch_send_record_ephemeral`）；删簇任务必须保持 `trigger_rule=all_done` | §4.5 | 🔴强制 |
| G-06-05 | 所有 Cloud Run ES 写入必须传入稳定 `id_field`；禁止 `id_field=None` 的生产写；写函数失败必须 `raise`（禁止吞异常返回 success） | §4.6 | 🔴强制 |
| G-06-06 | 禁止新增仅挂在 `start_new_task`、不门控业务任务的 `wait_check_allowed_hours_is_run` 类空转边；现有 dws_h 空转边应删除或接到真实下游 | §4.7 | 🔴强制 |
| G-06-07 | `on_failure_callback` 发出的 TT 正文必须包含 `exception` 字符串；`TtSend.sendTT` 不得 `except: print` 吞掉告警失败（至少 log.error 或二次降级通道） | §4.8 | 🟡建议 |
| G-06-08 | 禁止调用或复制 `send_tt_alert_factory`（当前 `return send_tt_alert` 未定义）；统一使用 `send_failure_alert_factory` | §4.8 | 🟡建议 |
| G-06-09 | Pub/Sub 监控 DAG 保持 `max_active_runs=1`；解析失败不得在未落盘/未告警的情况下仅 `continue` 而不计量丢弃 | §3 / §4.9 | 🟡建议 |
| G-06-10 | TimeDeltaSensor 禁止再提高至 `retries>1000`；`wait_14_hours` 的 `retries=2000` 变更须附容量评估 | §4.3 | 🟡建议 |

---

### 9. 旧文档交叉验证摘要

NO_DOCS：`Legacy_qpon-bigdata_Claims.md` 无异步机制声称，本节跳过。

---

## 附录 A：强制审计项回执（Step05 RELAY）

| # | 审计项 | 结论（代码事实） |
|---|---|---|
| 1 | Sensor retries=1000 / SkipSensor 与失败补偿 | 日批工厂 `retries=1000`+`timeout=64800`；Skip 工厂 `retries=20`，SKIPPED→skip，FAILED→fail；无独立补偿表 |
| 2 | `qpon_daily_report` execution_delta | `timedelta(hours=8)`；`retries=100`；`timeout=28800`；对齐 `0 18` vs `0 2` |
| 3 | Dataproc spark 与 ODS 直连 Sensor | ephemeral 链 + `delete` `all_done`；ODS 等整 DAG、`retries=1000`、无 `external_task_id` |
| 4 | Cloud Run ES 重试与幂等 | 无函数内重试；靠 DAG retries；`id_field` 幂等；health 10s / write 30s |
| 5 | `check_allowed_hours_is_run` | DummyOperator **存在**于 `qpon_dwd_h`；dws_h/test 等待；dws_h **不门控** feature 任务 → 空转 |
| 6 | TT on_failure_callback 是否掩盖失败 | **不**改失败状态；**是**削弱可观测性（无 exception 正文 + 发送失败静默） |

## 附录 B：物理锚点

| 锚点 | 路径 |
|---|---|
| Sensor 工厂 | `dags/airflow_config/create_external_sensor.py` L10–136 |
| TT callback | `dags/airflow_config/airflow_tt_send.py` L8–76 |
| Cloud Run ES | `dags/airflow_config/cloud_run_write_aliyun_es.py` L5–100 |
| ES 删除 | `dags/airflow_config/cloud_run_delete_aliyun_es.py` L22–138 |
| BQ Check | `dags/airflow_config/create_check_table_data.py` L7–26 |
| daily_report Sensor | `dags/qpon_daily_report/qpon_daily_report.py` L143–186 |
| ODS Spark/TimeDelta | `dags/qpon_ods_d/qpon_ods_d.py` L127–171 / L508 |
| Dataproc ephemeral | `dags/qpon_staging_d/spark_ug_rch_send_record_new.py` L48–193 |
| hours Dummy + ShortCircuit | `dags/qpon_dwd_h/qpon_dwd_h.py` L78–99 / L258–259 |
| 空转 Skip 边 | `dags/qpon_dws_h/qpon_dws_h.py` L101–127 |
| Pub/Sub | `dags/qpon_metadata/gcp_monitoring_alert.py` L42–69 |

---

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 异步主干是 ExternalTaskSensor（日批 retries=1000/timeout=64800）与 SkipSensor（小时 retries=20）；无 RocketMQ；Pub/Sub 仅监控入站且 retries=0；ES 写无函数级重试、靠 `id_field`+DAG retries；TT callback 不改状态但丢掉 exception 正文且发送失败可静默；`check_allowed_hours_is_run` 为 Dummy 空转边；daily_report 依赖 execution_delta=8h；Dataproc 删簇 all_done + ODS 整 DAG Sensor。
> - **推演约束 (Constraint)**: Step 07 必须重点审计 (1) Composer/变量中与 Sensor timeout、slot、DAG concurrency 相关的运行时配置；(2) TT webhook Variable/硬编码 token 与告警可达性；(3) `write_es_service_url`/`es_*` Variable 与 Cloud Run 超时是否在配置层可调；(4) Pub/Sub subscription 与 `is_paused_upon_creation=True` 是否导致监控静默；(5) 日志/指标是否覆盖 Sensor up_for_retry 风暴与 callback 发送失败。
> - **物理锚点 (Anchors)**: `dags/airflow_config/create_external_sensor.py` L10-24/L125-136；`dags/airflow_config/airflow_tt_send.py` L52-68；`dags/airflow_config/cloud_run_write_aliyun_es.py` L5-100；`dags/qpon_daily_report/qpon_daily_report.py` L143-156；`dags/qpon_ods_d/qpon_ods_d.py` L127-137；`dags/qpon_staging_d/spark_ug_rch_send_record_new.py` L181-193；`dags/qpon_dws_h/qpon_dws_h.py` L101-127；`dags/qpon_metadata/gcp_monitoring_alert.py` L42-69。
