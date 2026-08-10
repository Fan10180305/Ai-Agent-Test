# 03_Downstream_Dependencies — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）；禁止 `scripts/`  
> 语义映射：Dubbo 消费者 / HTTP 下游 → **BQ 表依赖 + ExternalTaskSensor 上游 + ES/Feishu/Datastream/Cloud Run/PubSub/Adjust/TT**  
> BQ 锚点：`oppo-gcp-prod-digfood-129869` @ `asia-southeast2`  
> Legacy：NO_DOCS  
> 物理拦截：对 `dags/**/*.py`（1167）做 backtick FQN 全量计数；活代码工厂调用严格正则；f-string `warehouse` 变量解析后 751/751 模块解析；441 Sensor 边上溯 task 模块 439/441

---

### 1. Dubbo 消费者接口全量清单

N/A：无 `DubboReferenceConfig` / `@DubboReference`。等价「下游依赖接口」按外部系统分组如下。

| 序号 | 接口（逻辑全名） | 所属外部服务（artifact 等价） | registry / 坐标 | check | retries | timeout | loadbalance |
|---:|---|---|---|---|---|---|---|
| 1 | `BigQueryInsertJobOperator` / SQL FQN 读写 | `google-cloud-bigquery` / project `oppo-gcp-prod-digfood-129869` | location=`asia-southeast2`；conn=`google_cloud_default` | N/A | DAG 默认多为 3；工厂未设 | 未配置（继承 Operator/Composer 默认） | N/A |
| 2 | `create_external_sensor` → `ExternalTaskSensor` | Airflow 元数据库跨 DAG | `external_dag_id`/`external_task_id` | `allowed_states=['success']` | **1000** | **64800**s；poke=**600** | mode=`reschedule` |
| 3 | `create_external_task_skip_sensor_hour` → `ExternalTaskSkipSensor` | 同上（小时批 Skip 语义） | 同上 | poke 分支 SUCCESS/SKIPPED/FAILED | 默认 0（构造参数） | 7200 / poke 300 | N/A |
| 4 | `create_external_sensor_hour` | 同上 | 同上 | 同上 | 20 | 7200 / 300 | **幽灵：定义存在，活调用=0** |
| 5 | `access_cloud_run_write_aliyun_es` | Cloud Run ES 写入服务 | Variable `write_es_service_url` | GET `/health` | 未配置 | GET **10**s；POST **30**s | N/A |
| 6 | `delete_by_field_condition` | 阿里云 ES（经同基址 Variable） | `write_es_service_url` + `es_*` | `es.ping()` | 未配置 | 未显式 timeout | N/A |
| 7 | `ElasticsearchWriteOperator` / `excuete_write_es` | 阿里云 ES 直连 | 硬编码 `http://10.3.13.241:19527` 或 Variable `es_*` | N/A | 未配置 | 默认 **30**s | **DAG 活调用=0（仅模块自测 `__main__`）** |
| 8 | `ReadFeiShuToBigQuery` | 飞书 OpenAPI | 硬编码 `FEISHU_APP_ID`/`SECRET`；host `open.feishu.cn` | HTTP raise | 未配置 | 未显式 timeout | N/A |
| 9 | `requests.get` Adjust Reports API | Adjust | `https://automate.adjust.com/reports-service/report` | status 检查 | 未配置 | 未显式 timeout | N/A |
| 10 | `TtSend` / `TeamtalkRobot` | TeamTalk MTP Webhook | `mtp.myoas.com`；DAG 硬编码 `yzjtoken` 或 Variable | status 200 | 未配置 | 未显式 timeout | N/A |
| 11 | `DatastreamApi` | Google Datastream REST | `datastream.googleapis.com/v1/projects/{QPON_GCP_PROJECT_ID}/locations/{QPON_GCP_LOCATION}` | status 200 | 未配置 | 未显式 timeout | N/A |
| 12 | `PubSubPullSensor` | Google Pub/Sub | subscription=`qpon-data-gcp-component-monitoring-sub` | N/A | DAG retries=0 | poke_interval=**10** | N/A |
| 13 | Dataproc*Operator | Google Dataproc + Spark | `qpon_staging_d/spark_*.py` | N/A | 见各 DAG | 见各 DAG | N/A |
| 14 | `SecretManagerServiceClient` | Google Secret Manager | `spark_mysql_to_bigquery.py` | N/A | N/A | N/A | N/A |
| 15 | `google.genai` | Google GenAI | Variable LLM key（`qpon_daily_report`） | N/A | N/A | N/A | N/A |

**BQ dataset 作为「逻辑接口」权重**（工厂任务内 backtick 引用的去重 task 数；>5=重度 / 2–5=中度 / 1=轻度）：

| 逻辑接口（dataset） | 消费 task 数 | 重量 |
|---|---:|---|
| `qpon_dwd_d` | 374 | 重度 |
| `qpon_ods_d` | 324 | 重度 |
| `qpon_dim_d` | 183 | 重度 |
| `qpon_rpt_d` | 182 | 重度 |
| `qpon_dws_d` | 94 | 重度 |
| `digital_food_order` | 71 | 重度 |
| `digital_food_market` | 57 | 重度 |
| `qpon_analyst_d` | 24 | 重度 |
| `qpon_email_date_d` / `_test` | 20 / 20 | 重度 |
| `order_center_hzero_platform` | 12 | 重度 |
| `pubsub_to_bq_qpon_events_collection` | 10 | 重度 |
| `qpon_operation` / `qpon_data_server` / `qpon_tmp` / `digital_food_settle` 等 | 7–9 | 重度 |
| `qpon_crm` / `Qpon_Adjust_Raw_Data` / `market_db_user_growing` 等 | 2–4 | 中度 |
| `qpon_sync_from_feishu` / 部分 test_env_* | 1–2 | 轻度/中度 |

全仓 backtick FQN：`5989` 处命中；唯一 FQN=`1062`；唯一 dataset=`35`；project 仅 `oppo-gcp-prod-digfood-129869`。

---

### 2. 实际调用点追踪

#### 2.0 扫描规模（工厂 / Sensor）

| 指标 | 数值 | 说明 |
|---|---:|---|
| 活工厂调用（严格正则） | **751** | BQ **693** + Python **57** + Check **1** |
| 注释掉的工厂调用残留 | **≈326** | 含注释行合计约 1077，与 Step02 字面合计对齐 |
| Sensor 活边 | **441** | `create_external_sensor` 407 + `create_external_task_skip_sensor_hour` 34 |
| 工厂 task 模块解析 | **751/751** | warehouse f-string 解析后 0 未解析 |
| Sensor 上游 task 模块解析 | **439/441** | 缺失见下 |

**Sensor 上游解析失败（2）**：

| src_dag | upstream_dag | task | 事实 |
|---|---|---|---|
| `qpon_dws_h` | `qpon_dwd_h` | `check_allowed_hours_is_run` | `dags/` 内无同名 `.py` stem |
| `qpon_test_d` | `qpon_dwd_h` | `check_allowed_hours_is_run` | 同上 |

#### 2.A BigQuery（主下游）

**直接调用方**：各 DAG 入口 → `create_composer_bq_task` → `BigQueryInsertJobOperator`（configuration.query；location 钉死 `asia-southeast2`）→ task 模块返回的 SQL。

**高频读表（工厂任务内 FROM/JOIN 字面 FQN Top）**：

| 次数 | FQN |
|---:|---|
| 251 | `…qpon_dwd_d.dwd_product_order_voucher_all` |
| 195 | `…qpon_dwd_d.dwd_qpon_event_traffic_inc_d` |
| 108 | `…qpon_dim_d.dim_daytime_info` |
| 77 | `…qpon_dws_d.dws_qpon_device_active_info_inc_d` |
| 75 | `…qpon_dwd_d.dwd_product_store_detail_d` |
| 65 / 61 / 58 | `dim_product_basic_info` / `dim_store_info` / `dim_merchant_basic_info` |

**跨层 SQL 读依赖（工厂展开，pkg 读外层 dataset 次数 Top）**：

| 次数 | 边 |
|---:|---|
| 517 | `qpon_rpt_d` ← `qpon_dwd_d` |
| 297 | `qpon_rpt_d` ← `qpon_dim_d` |
| 164 | `qpon_rpt_d` ← `qpon_ods_d` |
| 116 | `qpon_risk_d` ← `qpon_dwd_d` |
| 96 | `qpon_dwd_d` ← `qpon_ods_d` |
| 76 | `qpon_rpt_d` ← `qpon_dws_d` |
| 73 | `qpon_tag_d` ← `qpon_dwd_d` |
| 64 | `qpon_dim_d` ← `qpon_ods_d` |

**经由 Sensor 间接依赖**：`wait_{task}` 成功后才跑本 DAG SQL；上溯 439 个上游模块内 FQN 以 `qpon_ods_d`（1256）、`qpon_dwd_d`（545）、`qpon_dim_d`（341）、源库 dataset `digital_food_order`/`digital_food_market` 为主。

**注入未直接调用**：N/A（无 DI 注入模型）。等价：大量 `# create_composer_*` 注释注册 = **类级别失活/注册失活**（约 326 条）。

#### 2.B ExternalTaskSensor（跨 DAG「RPC」）

每个边：`src_dag` 内 `wait_{task}` → 等待 `upstream_dag.task`。

| 次数 | src → upstream |
|---:|---|
| 64 | `qpon_dwd_d` → `qpon_ods_d` |
| 52 | `qpon_rpt_d` → `qpon_ods_d` |
| 36 | `qpon_rpt_d` → `qpon_dwd_d` |
| 32 | `qpon_dim_d` → `qpon_ods_d` |
| 28 | `qpon_dwd_h` → `qpon_ods_h` |
| 17 | `qpon_analyst_d` → `qpon_ods_d`；`qpon_rpt_d` → `qpon_dim_d` |
| 16 | `qpon_data_server_d` → `qpon_ods_d` |
| ≤12 | `qpon_email_date_*`、`qpon_tag_d`、`qpon_dws_*`、`qpon_risk_d` 等（完整对表见 Step02 §1.C；本步复核 53+ 唯一对） |

重量：Sensor 工厂本身为单一构造方法 → 按边数量计，对 `qpon_ods_d` 的等待为 **重度依赖**。

#### 2.C Cloud Run → 阿里云 ES

**接口方法**：`access_cloud_run_write_aliyun_es(select_sql, id_field, index_name)`  
链路：`DAG Python 任务` → `access_cloud_run_write_aliyun_es` → `requests.get({write_es_service_url}/health)` → `requests.post(.../api/write-to-es)` → Cloud Run → ES。

**直接调用方（活，22）**：

| 包 | 任务模块 | index_name（代码字面） |
|---|---|---|
| `qpon_rpt_d` | `rpt_channe_*_es`（5）、`rpt_department_*_es`（4）、`rpt_trade_*_es`（2） | `store_sale_statis_dashboard`、`*_ranking_statis`、`trade_*_dashboard` 等 |
| `qpon_dwd_d` | 4 个 `*_to_es` | `market_activity_dashboard_data`、`sync_merchant_*`、`recruit_activity_product_data` |
| `qpon_data_server_d` | 6 个写 + 与 dwd 同名副本 | 同上 + `store_sell_well_rank_20260521`、`merchant_refund_statistics_2026061501` |
| `data_options` | `task_write_es` | `test_store_sale_statis_dashboard` |

**删除**：`qpon_data_server_d/tasks/data_server_store_sell_well_rank_20260521_delete_es.py` → `delete_by_field_condition`（直连 ES client，非 POST write）。

重量：写接口 1 个方法、22 调用点 → **重度**（按调用点）；唯一 index 约 18 个。

#### 2.D 飞书 OpenAPI → BQ

**接口**：`ReadFeiShuToBigQuery`（token/审批/wiki/sheet/doc/bitable + `write_to_bigquery`）。

**活直接调用方**：

| 调用方 | 场景 | BQ 落点 dataset |
|---|---|---|
| `qpon_ods_d/tasks/qpon_feishu/ods_new_store_from_mkt_for_using.py` | bitable → BQ | `qpon_sync_from_feishu` |

**类级别注释失活（入口已 `# create_composer_python_task`）**：`ods_expense_application_*`、`ods_channel_info`、`ods_budget_summary_2025`、detail 系列等；模块文件仍存在并可手工调用，但 **DAG 未注册**。

**命名例外**：`ods_expense_reimburse_daily`、`feishu_data_transformer` **不在**活工厂任务名集合中（后者为辅助模块）。

重量：活路径 1 个入口任务 → **轻度**；HTTP 方法面（token/bitable/write）>5 → 库级能力 **重度**，调度级 **轻度**。

#### 2.E Datastream / Meta

| 调用方 | 接口方法 | 场景 |
|---|---|---|
| `sync_bigquery_staging_description.py` | `DatastreamApi.list_streams` / `list_all_stream_objects` | 同步 staging 表描述 |
| `sync_source_meta.py` | Airflow Connection 前缀 `datastream-*` + MySQL meta mixin | 源表/列元数据同步（非 DatastreamApi HTTP） |

重量：2 个 DAG 入口级使用 → **轻度**。

#### 2.F Pub/Sub / Adjust / TT / GenAI / Dataproc

| 下游 | 直接调用方 | 方法/场景 | 重量 |
|---|---|---|---|
| Pub/Sub | `gcp_monitoring_alert` | `PubSubPullSensor` → TT | 轻度 |
| Adjust API | `ods_adjust_daily_report_*`；`qpon_dau_bigquery_adjust_contrast_alert_h` | GET report | 中度（2–3 模块） |
| TT Webhook | 几乎全部 DAG `failure_callback`；`TeamtalkRobot` | `TtSend.sendTT` | 重度（横切） |
| GenAI | `qpon_daily_report` → `generate_narrative` | `google.genai` | 轻度 |
| Dataproc | `qpon_staging_d/spark_*` | Create/Submit/Delete Cluster | 中度 |
| Secret Manager | `spark_mysql_to_bigquery.py` | 取 MySQL 密码 | 轻度 |

#### 2.G 幽灵依赖 / 失活

| 类型 | 项 |
|---|---|
| 幽灵依赖 | `create_external_sensor_hour`：已定义，活调用 **0** |
| 幽灵依赖 | `ElasticsearchWriteOperator` / `excuete_write_es`：仅 `airflow_config/elasticsearch_write_operator.py` 自身 `__main__`，无业务 DAG 引用 |
| 类级别注释失活 | ≈326 条注释掉的 `create_composer_*`；飞书多任务入口整段注释 |
| Sensor 悬空上游 | `check_allowed_hours_is_run`（2 边）— 等待目标 task 模块在 `dags/` 不存在 |

---

### 3. 超时与容错配置审计

#### 3.1 全局「Dubbo」配置

N/A：无 `dubbo` XML/YML。等价全局默认：

| 配置源路径 | 项 | 值 |
|---|---|---|
| `dags/airflow_config/create_external_sensor.py` L10–23 | Sensor timeout / poke / retries | 64800 / 600 / **1000** |
| 同文件 L27–40 | hour 变体（幽灵） | 7200 / 300 / 20 |
| `dags/airflow_config/create_composer_bq_task.py` L22 | BQ location | `asia-southeast2` |
| 多数 DAG `default_args` | retries / retry_delay | 常见 **3** / `timedelta(minutes=10)` |
| `dags/qpon_metadata/gcp_monitoring_alert.py` | DAG retries | **0** |

#### 3.2 接口级配置汇总

| 接口短名 | retries | timeout | 备注 |
|---|---|---|---|
| `create_external_sensor` | 1000 | 64800s | 覆盖 DAG retries |
| `create_external_sensor_hour` | 20 | 7200s | 无活调用 |
| `create_external_task_skip_sensor_hour` | 0（默认） | 7200s | 34 活边 |
| `access_cloud_run_write_aliyun_es` | 未配置 | 10s / 30s | health / write-to-es |
| `ElasticsearchWriteOperator` | 未配置 | 30s | 无 DAG 调用 |
| `ReadFeiShuToBigQuery` HTTP | 未配置 | 未配置（继承 requests 默认） | — |
| `TtSend` | 未配置 | 未配置 | — |
| `DatastreamApi` | 未配置 | 未配置 | google http client |
| `PubSubPullSensor` | DAG=0 | poke 10s | — |
| `BigQueryInsertJobOperator` | 继承 DAG | 未在工厂显式配置 | location 钉死 |

#### 3.3 熔断降级

未发现显式熔断降级配置（无 Sentinel / Hystrix / Resilience4j）。等价容错事实：Sensor `failed_states=['failed']`；Cloud Run 非 200 / JSON `error` 字段直接 `raise Exception`。

---

### 4. HTTP/其他协议调用清单

#### 4.1 HTTP 调用点表

| 业务触发方 | 完整调用链路 | 目标 URL 来源 | HTTP 方法 | 连接超时(ms) | 读取超时(ms) | 含异步层 |
|---|---|---|---|---|---|---|
| `*_es` Python 任务（rpt/dwd/data_server/data_options） | task → `access_cloud_run_write_aliyun_es` → `requests` | 动态配置（Variable `write_es_service_url`）+ `/health`、`/api/write-to-es` | GET / POST | 未单独配置 | 10000 / 30000 | 否（Airflow worker 同步） |
| `data_server_store_sell_well_rank_*_delete_es` | task → `delete_by_field_condition` → `Elasticsearch` client | Variable `es_hosts` 等 | ES API | 未配置 | 未配置 | 否 |
| `ods_new_store_from_mkt_for_using` 等飞书 task | task → `ReadFeiShuToBigQuery.*` → `requests` | 硬编码: `https://open.feishu.cn/open-apis/...` | GET/POST | 未配置 | 未配置 | 否（内部 `ThreadPoolExecutor` 批量审批除外） |
| `ods_adjust_daily_report_*` / dau alert | task → `requests.get` | 硬编码: `https://automate.adjust.com/reports-service/report?...` | GET | 未配置 | 未配置 | 否 |
| 各 DAG `failure_callback` | Airflow → `send_failure_alert_factory` → `TtSend.sendTT` → `stream_upload` → `requests.post` | 硬编码 DAG `send_url`（`mtp.myoas.com/...yzjtoken=...`）或 Variable webhook | POST | 未配置 | 未配置 | 否（回调同步） |
| `gcp_monitoring_alert` | PubSub → `monitoring_alert` → `TeamtalkRobot.send_text` → `requests.post` | Variable `gcp_alter_webhook_url` | POST | 未配置 | 未配置 | 否 |
| `sync_bigquery_staging_description` | DAG → `DatastreamApi` → `Client()._http.get` | 硬编码模板: `https://datastream.googleapis.com/v1/projects/{id}/locations/{loc}/...` | GET | 未配置 | 未配置 | 否 |
| `qpon_daily_report.send_feishu` | DAG → `send_feishu` → `requests.post` | Variable 飞书 webhook | POST | 未配置 | 未配置 | 否 |

N/A：无 `@Async` Spring 异步；Airflow 任务并行由 executor 调度，不记作 `@Async` 层。

#### 4.2 其他协议

| 协议 | 状态 |
|---|---|
| gRPC | 未发现 |
| WebSocket | 未发现 |
| JDBC（Spark） | `qpon_staging_d` Spark 作业经 Dataproc 读 MySQL（密码来自 Secret Manager） |
| Pub/Sub | `PubSubPullSensor`（见上） |
| BigQuery Job API | `BigQueryInsertJobOperator`（主路径，非裸 HTTP） |

---

### 5. 外部依赖拓扑图

#### 5.1 按外部服务分组

| 外部服务（逻辑 artifactId） | 接口/能力 | 整体依赖级别 |
|---|---|---|
| `google-cloud-bigquery` | 1062 FQN / 35 dataset / 751 工厂任务 SQL | 重度 |
| `apache-airflow` ExternalTaskSensor | 441 边 | 重度 |
| `cloud-run-write-aliyun-es` + Aliyun ES | 22 写 + 1 删 | 重度 |
| `teamtalk-mtp-webhook` | 全局 failure_callback | 重度 |
| `feishu-open-api` | 1 活任务 + 多失活模块 | 轻度（调度）/ 中度（代码面） |
| `adjust-reports-api` | 2–3 模块 | 中度 |
| `google-datastream` | 1–2 DAG | 轻度 |
| `google-pubsub` | 1 DAG | 轻度 |
| `google-dataproc` + Spark | `qpon_staging_d` | 中度 |
| `google-secret-manager` | Spark MySQL | 轻度 |
| `google-genai` | daily_report | 轻度 |

#### 5.2 ASCII 拓扑图

```
qpon-bigdata (Composer DAGs)
├── BigQuery oppo-gcp-prod-digfood-129869 @ asia-southeast2
│   ├── qpon_ods_d / digital_food_* / pubsub_to_bq_* / qpon_sync_from_feishu ...  [重度]
│   ├── qpon_dim_d / qpon_dwd_d / qpon_dws_d / qpon_rpt_d / qpon_tag_d ...      [重度]
│   └── qpon_tmp / qpon_analyst_* / qpon_data_server / test_env_*                 [中~重]
├── ExternalTaskSensor (441)
│   └── ods → dim/dwd → dws/rpt/tag/analyst/risk/data_server/email               [重度]
├── Cloud Run (write_es_service_url) → Aliyun ES indexes (~18)                    [重度]
├── Feishu open.feishu.cn → BQ qpon_sync_from_feishu                             [轻度活]
├── Adjust automate.adjust.com                                                   [中度]
├── TeamTalk mtp.myoas.com                                                       [重度横切]
├── Datastream API + Connection datastream-*                                     [轻度]
├── Pub/Sub qpon-data-gcp-component-monitoring-sub                               [轻度]
├── Dataproc/Spark + Secret Manager                                              [中度]
└── GenAI (daily_report)                                                         [轻度]
```

#### 5.3 幽灵依赖识别

- **幽灵依赖**：`create_external_sensor_hour`（注册/定义但无活调用）；`ElasticsearchWriteOperator`/`excuete_write_es`（无业务 DAG 调用点）。
- **类级别注释失活**：≈326 条注释工厂注册；飞书多任务入口注释块。
- **悬空等待**：`check_allowed_hours_is_run` ×2。

---

### 6. Step 01 遗漏追踪

N/A：无 Maven client POM。按 Step01「中间件雷达」逐项用本步调用事实核验：

| Step01 项 | 代码是否有实际调用 | 调用接口 / 类 |
|---|---|---|
| BigQuery | 是 | 751 工厂 + 全仓 5989 FQN |
| ExternalTaskSensor | 是 | 441 活边 |
| ES / Cloud Run | 是 | 22×`access_cloud_run_write_aliyun_es` + 1×delete |
| 飞书 | 是（活 1）+ 多失活 | `ReadFeiShuToBigQuery`；入口仅 `ods_new_store_from_mkt_for_using` 活注册 |
| Datastream | 是 | `DatastreamApi` in `sync_bigquery_staging_description`；`datastream-*` Connections in `sync_source_meta` |
| Pub/Sub | 是 | `gcp_monitoring_alert.PubSubPullSensor` |
| Adjust | 是 | `ods_adjust_daily_report_*` 等 |
| TT | 是 | `TtSend` / `TeamtalkRobot` |
| Dataproc/Spark / Secret Manager | 是 | `qpon_staging_d` |
| GenAI | 是 | `generate_narrative` |
| Redis | 否 | 确认无调用（与 Step01 N/A 一致） |
| RocketMQ | 否 | 确认无 |
| dbt profile Variables | 坐标存在 | 本步未发现 `dags/` 内执行 dbt CLI 的活调用（作业路径待 Step04+） |

**Step01 未单独强调、本步确认的依赖**：

- 源库 BQ dataset 直读：`digital_food_order`/`digital_food_market`/…（Datastream 落地表被 ODS/下游 SQL 直接引用）
- UDF/函数型 FQN：`digital_food_order.aes_decrypt`、`pubsub_to_bq_qpon_events_collection.url_decode`

**命名例外核对（Step02 接力）**：

| 文件/符号 | 工厂引用 | 结论 |
|---|---|---|
| `feishu_data_transformer` | 否 | 辅助模块，非工厂 task |
| `ods_expense_reimburse_daily` | 否 | 模块存在；入口未活注册 |
| `generate_narrative` | 否（非 create_composer_*） | 由 `qpon_daily_report` 内 `PythonOperator` 直接绑定 |
| `calculate_metrics` / `send_report` | 无对应 stem 文件 | Step02 例外列表中的逻辑名；实际入口为 `query_metrics`/`send_feishu` 等 |

---

### 7. 旧文档交叉验证摘要

NO_DOCS：`Legacy_qpon-bigdata_Claims.md` LEGACY_COUNT=0，跳过声称级 ❌/✅ 分条。

🆕相对空旧文档：下游依赖主体是 **BQ dataset/FQN 图 + 441 Sensor 边 + Cloud Run ES + 飞书/Adjust/TT/Datastream/PubSub**，而非 Dubbo 消费者清单。

---

> [!SUCCESS] 下游依赖测绘闭环验证
> - 扫描范围：N/A DubboReferenceConfig；等价扫描 = `dags/` 1167 `.py` + `airflow_config` 网关 10 业务文件 + 全量工厂/Sensor/HTTP/ES/Feishu/Datastream 搜索（禁止 scripts/）
> - 提取结果：15 类外部服务/协议能力；0 个 Dubbo 消费者；BQ 唯一 FQN 1062 / dataset 35；活工厂调用点 751（注释残留≈326）；Sensor 边 441；HTTP 主调用族 ≥8 类（Cloud Run/Feishu/Adjust/TT/Datastream/daily_report webhook 等）；Cloud Run ES 写 22 + 删 1
> - 幽灵依赖：2 类（`create_external_sensor_hour`；`ElasticsearchWriteOperator` 无 DAG 调用）；类级别注释失活：≈326 工厂 + 飞书入口块；悬空 Sensor 上游：2
> - 超时配置：全局 Sensor 默认来自 `dags/airflow_config/create_external_sensor.py`，值为 timeout=64800s / retries=1000；Cloud Run 接口自定义 10s/30s；其余多数「未配置（继承默认）」
> - Step 01 遗漏追踪：BigQuery/Sensor/ES/飞书/Datastream/PubSub/Adjust/TT/Dataproc/GenAI [已确认有调用]；Redis/RocketMQ [确认无]；dbt CLI [仅 Variable 坐标]
> - 旧文档验证：N/A（NO_DOCS）
> - EOF 状态：已确认工厂 751/751 模块解析、Sensor 439/441 上溯、FQN 全仓计数与 ES/飞书落点枚举至扫描输出最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 主下游是 BQ project `oppo-gcp-prod-digfood-129869`（35 dataset / 1062 FQN）；活工厂 751（非 Step02 含注释的 1077）；跨 DAG 等待 441 边，上游 SQL 以 `qpon_ods_d`/`qpon_dwd_d`/`qpon_dim_d` 为枢纽；ES 落点经 Cloud Run Variable `write_es_service_url`，约 18 index，写调用 22；飞书活落点 dataset=`qpon_sync_from_feishu`（仅 `ods_new_store_from_mkt_for_using` 活注册）；Datastream REST + `datastream-*` Connection；Pub/Sub subscription=`qpon-data-gcp-component-monitoring-sub`；幽灵：`create_external_sensor_hour`、直连 `ElasticsearchWriteOperator`；悬空上游 task=`check_allowed_hours_is_run`
> - **推演约束 (Constraint)**: Step 04 数据模型必须：① 以 backtick FQN 为权威建「表实体」清单（优先 Top 读表与各层 CREATE/INSERT 目标，注意大量 `{project_id}.{insert_dataset_id}.{insert_table_id}` 模板需结合 task 变量展开）；② 区分源库 dataset（`digital_food_*` 等）与仓内分层 dataset；③ 为每个 ES index 反查对应 SELECT SQL 字段→文档映射；④ 飞书表仅活路径 + `qpon_sync_from_feishu.*`；⑤ 禁止 scripts/
> - **物理锚点 (Anchors)**: `dags/airflow_config/create_composer_bq_task.py:7-27`；`dags/airflow_config/create_external_sensor.py:10-40`；`dags/airflow_config/cloud_run_write_aliyun_es.py:5-66`；`dags/airflow_config/read_feishu_to_bg.py:22-51`；`dags/qpon_metadata/utils/datastream.py:17-27`；`dags/qpon_metadata/gcp_monitoring_alert.py:57-65`；`dags/qpon_ods_d/qpon_ods_d.py:40-85,451`；`dags/qpon_rpt_d/tasks/rpt_*_es.py`；`dags/qpon_dwd_d/tasks/*_to_es.py`；`dags/qpon_data_server_d/tasks/*_es.py`
