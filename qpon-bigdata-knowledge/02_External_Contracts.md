# 02_External_Contracts — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）  
> 语义映射：Java `*-client` Dubbo 契约 → **共享库对外函数签名 + DAG 入口调度契约 + ExternalTaskSensor 边 + pydantic Schema**  
> BQ 锚点：`oppo-gcp-prod-digfood-129869` @ `asia-southeast2`  
> Legacy：NO_DOCS

---

### 1. Dubbo 接口清单

N/A：无 Dubbo interface。等价「对外承诺面」拆为三层：**(A) `airflow_config` 共享工厂 API**、**(B) DAG 入口调度契约**、**(C) 跨 DAG Sensor/Marker 边**。

#### 1.A 共享库对外函数/类（`dags/airflow_config/`，client JAR 等价）

| 接口名（模块.符号） | 子包 | 方法签名 | 入参 | 返回类型 |
|---|---|---|---|---|
| `create_composer_bq_task.create_composer_bq_task` | airflow_config | `create_composer_bq_task(dag, warehouse_path, task_module_name, on_failure_callback=None)` | DAG; str 模块路径; str 任务模块名; Optional[Callable] | `BigQueryInsertJobOperator` |
| `create_composer_bq_task.create_composer_python_task` | airflow_config | `create_composer_python_task(dag, warehouse_path, task_module_name, on_failure_callback=None)` | 同上 | `PythonOperator` |
| `create_check_table_data.Check_BQ_Data_IsExists_Operator` | airflow_config | `Check_BQ_Data_IsExists_Operator(dag, warehouse_path, task_module_name, on_failure_callback=None)` | 同上 | `BigQueryCheckOperator`（location=`asia-southeast2`, retries=24） |
| `create_external_sensor.create_external_sensor` | airflow_config | `create_external_sensor(dag, dag_name, task_name, timeout=64800, poke_interval=600, priority_weight=100, on_failure_callback=None)` | DAG; 上游 dag_id; 上游 task_id; … | `ExternalTaskSensor`（retries=1000, mode=reschedule） |
| `create_external_sensor.create_external_sensor_hour` | airflow_config | `create_external_sensor_hour(dag, dag_name, task_name, timeout=7200, poke_interval=300, priority_weight=100, on_failure_callback=None)` | 同上 | `ExternalTaskSensor`（retries=20） |
| `create_external_sensor.ExternalTaskSkipSensor` | airflow_config | `__init__(external_dag_id, external_task_id, on_failure_callback=None, retries=0, …)` / `poke(context)` | 外部 dag/task | Sensor；success→True，skipped→Skip，failed→Exception |
| `create_external_sensor.create_external_task_skip_sensor_hour` | airflow_config | `create_external_task_skip_sensor_hour(dag, dag_name, task_name, timeout=7200, poke_interval=300, on_failure_callback=None)` | 同上 | `ExternalTaskSkipSensor` |
| `create_external_marker.create_external_marker` | airflow_config | `create_external_marker(dag, external_dag_id, external_task_id, task_id=None, execution_date_fn=None, **kwargs)` | 下游 dag/task | `ExternalTaskMarker` |
| `airflow_tt_send.TtSend` | airflow_config | `__init__(sendStr, send_url)` / `sendTT()` / `stream_upload(url, data, chunk_size=…)` | 告警正文; webhook URL | None（HTTP POST → mtp.myoas.com） |
| `airflow_tt_send.send_failure_alert_factory` | airflow_config | `send_failure_alert_factory(send_url: str)` | webhook URL | `Callable`（Airflow on_failure_callback） |
| `airflow_tt_send.send_tt_alert_factory` | airflow_config | `send_tt_alert_factory(message: str, send_url: str)` | message; URL | 立即发送后返回 `send_tt_alert` |
| `cloud_run_write_aliyun_es.access_cloud_run_write_aliyun_es` | airflow_config | `access_cloud_run_write_aliyun_es(select_sql, id_field=None, index_name=None)` | BQ SQL; ES doc id 字段; index | `"success"` / raise |
| `cloud_run_delete_aliyun_es.get_es_client` | airflow_config | `get_es_client(host, user_name, password, api_key)` | ES 连接四元组 | `Elasticsearch` |
| `cloud_run_delete_aliyun_es.delete_by_field_condition` | airflow_config | `delete_by_field_condition(index_name, field_name, field_value, batch_size=1000)` | index; 字段; 值\|list | int（删除条数） |
| `elasticsearch_write_operator.ElasticsearchWriteOperator` | airflow_config | `__init__(es_hosts, index_name, input_data, api_key=None, es_user=None, es_password=None, id_field=None, bulk_size=1000, timeout=30, **kwargs)` | ES 写入参数 | Operator |
| `elasticsearch_write_operator.excuete_write_es` | airflow_config | `excuete_write_es(select_sql, id_field, index_name, env)` | SQL; id; index; env | None（侧车写 ES） |
| `read_feishu_to_bg.ReadFeiShuToBigQuery` | airflow_config | 见下表方法清单 | 飞书 token/sheet/bitable → BQ | 各类 dict/DataFrame/`None` |
| `util.remove_unpaired_brackets` / `extract_text_before_parentheses` | airflow_config | `(text)` | str | str |

**`ReadFeiShuToBigQuery` 方法签名（对外 HTTP/BQ 侧车）**：

| 方法 | 入参 | 返回（代码行为） |
|---|---|---|
| `__init__` | — | — |
| `date_to_timestamp` | `date_str` | int(ms) |
| `get_feishu_access_token` | — | tenant_access_token |
| `get_list_approval_list` | `approval_code, token, start_time, end_time` | 审批列表 |
| `get_approval_instances` | `instance_id, token` | 实例详情 |
| `get_approval_instances_batch` | `instance_ids: List[str], token: str, …` | 批量实例 |
| `get_wiki_real_tekon` | `node_token` | wiki token |
| `download_feishu_sheet` | `spreadsheet_token, sheet_id="0"` | sheet 数据 |
| `download_feishu_doc` | `document_token` | doc 数据 |
| `download_feishu_bitable` / `_all` / `_first_page` | `app_token, table_id[, page_token]` | bitable 数据 |
| `write_to_bigquery` | `dataframe, project_id, dataset_id, table_id, deleteCondation` | BQ 写入 |
| `convert_data` | `df, mapping_dict` | 转换后 DF |
| `main` | — | 编排入口 |

**导出名约定（breaking change 硬约束）**：`create_composer_bq_task` / `create_composer_python_task` / `Check_BQ_Data_IsExists_Operator` 通过 `importlib.import_module(f"{warehouse_path}.{task_module_name}")` 后执行 `getattr(module, task_module_name)`——**task 模块文件名 stem == 导出名 == Airflow task_id**。仓库内 `tasks/**/*.py` 抽样：1075 符合 / 5 例外（`qpon_daily_report/tasks/*` 3 个；`feishu_data_transformer.py`；`ods_expense_reimburse_daily` 导出为 `ods_ods_expense_reimburse_daily`）。

**硬编码运行时契约**：`create_composer_bq_task` 与 `Check_BQ_Data_IsExists_Operator` 将 BQ `location` 钉死为 `'asia-southeast2'`。

#### 1.B DAG 入口调度契约（对外 dag_id / schedule / 工厂调用清单）

约定：多数包 **包名 = `dag_name` = `dag_id`**。入口文件对 `create_composer_*` 的字面调用（包根 `*.py`，不含注释过滤以外的工厂计数）合计 **1077**：`create_composer_bq_task`=1001，`create_composer_python_task`=75，`Check_BQ_Data_IsExists_Operator`=1。

| DAG id（接口名） | 子包/入口 | schedule | BQ 工厂调用 | Python 工厂调用 | Sensor 边(活) | 方法数≈任务槽 |
|---|---|---|---:|---:|---:|---:|
| `qpon_ods_d` | `qpon_ods_d/qpon_ods_d.py` | `0 18 * * *` | 139 | 26 | 1 | 165 |
| `qpon_ods_h` | `qpon_ods_h/qpon_ods_h.py` | `10 * * * *` | 40 | 6 | 0* | 46 |
| `qpon_ods_d_test` | `qpon_ods_d_test/…` | `0 18 * * *` | 4 | 10 | 0* | 14 |
| `qpon_dim_d` / `qpon_dim_h` | 对应入口 | `0 18 * * *` / `10 * * * *` | 32 / 3 | 0 | 38† / 8 | 32 / 3 |
| `qpon_dwd_d` / `qpon_dwd_h` / `_test` | 对应入口 | 日/时/日 | 108 / 25 / 6 | 4 / 0 / 0 | 64+… / 28+… / 3 | 112 / 25 / 6 |
| `qpon_dws_d` / `qpon_dws_h` | 对应入口 | 日/时 | 29 / 4 | 0 | 23 / 7 | 29 / 4 |
| `qpon_rpt_d` / `qpon_rpt_h` | 对应入口 | 日/时 | 271 / 21 | 13 / 0 | 115† / 15 | 284 / 21 |
| `qpon_tag_d` / `_test` | 对应入口 | `0 18 * * *` | 143 / 4 | 0 | 21 / 1 | 143 / 4 |
| `qpon_analyst_d` / `_h` | 对应入口 | 日/时 | 49 / 4 | 0 | 35 / 3 | 49 / 4 |
| `qpon_analyst_alarm_d` / `_h` | 对应入口 | 日/时 | 0 | 1 / 1 | 2 / 1 | 1 / 1 |
| `qpon_data_server_d` / `_test` | 对应入口 | `0 18 * * *` | 10 / 10 | 7 / 0 | 22 / 9 | 17 / 10 |
| `qpon_email_date_d` / `_test` | 对应入口 | `0 18 * * *` | 21 / 21 | 0 | 14 / 10 | 21 / 21 |
| `qpon_risk_d` | `qpon_risk_d/…` | `0 18 * * *` | 46 | 0 | 11 | 46 |
| `Qpon_Adjust_Raw_Data` | `Qpon_Adjust_Raw_Data/…` | `0 18 * * *` | 2 | 1 | 0* | 3 |
| `data_options` | `data_options/…` | `20 16 * * 5` | 0 | 4 | 0 | 4 |
| `task_kill` | `task_kill/…` | `*/2 0-12 * * *` | 0 | 1 | 0 | 1 |
| `qpon_review_score_test` / `qpon_test_d` | 对应入口 | 日 / 时 | 5 / 4 | 1 / 0 | 0* / 1 | 6 / 4 |
| `qpon_daily_report` | `qpon_daily_report/qpon_daily_report.py` | `0 2 * * *` | 0（直写 PythonOperator） | 0 | 见入口（等 `qpon_rpt_d`） | 自定义 |
| `qpon_search_store_fea_export` | `qpon_search_d/qpon_search_store_fea_export.py` | `0 18 * * *` | 0（自定义） | 0 | — | 自定义 |
| `gcp_monitoring_alert` / `sync_source_meta` / `sync_bigquery_staging_description` | `qpon_metadata/*` | `*/1 * * * *` / `@daily` / — | 0 | 0 | — | 自定义 |
| `spark_ug_rch_send_record*` / spark MySQL | `qpon_staging_d/*` | `0 18 * * *` | 0（Dataproc） | 0 | — | 自定义 |

\* Sensor 列对部分包为「作为依赖方」边数；`qpon_ods_*` 主要为被等待方。† `qpon_dim_d`/`qpon_rpt_d` 的 Sensor 边含对多上游 DAG 的合计（见 §1.C）。

按 DAG 汇总工厂调用 Top：`qpon_rpt_d`(284)、`qpon_ods_d`(165)、`qpon_tag_d`(143)、`qpon_dwd_d`(112)、`qpon_analyst_d`(49)、`qpon_ods_h`(46)、`qpon_risk_d`(46)。

#### 1.C ExternalTaskSensor 全量边表（活代码，剔除 `#` 注释）

扫描函数：`create_external_sensor`（407）+ `create_external_task_skip_sensor_hour`（34）= **441 条活边**；`create_external_sensor_hour` **仅定义未调用**。  
`create_external_marker` 活调用 **2** 条：`qpon_rpt_d` → `qpon_analyst_alarm_d.wait_rpt_bq_l0l1_statistic_indicators_details_d` / `wait_rpt_bq_l0l1_indicators_monitoring_quantile_details_d`。

**边语义**：`src_dag` 内 `wait_{task}` 等待 `upstream_dag.task` 成功。

| 次数 | src_dag → upstream_dag |
|---:|---|
| 64 | `qpon_dwd_d` → `qpon_ods_d` |
| 52 | `qpon_rpt_d` → `qpon_ods_d` |
| 36 | `qpon_rpt_d` → `qpon_dwd_d` |
| 32 | `qpon_dim_d` → `qpon_ods_d` |
| 28 | `qpon_dwd_h` → `qpon_ods_h` |
| 17 | `qpon_analyst_d` → `qpon_ods_d` |
| 17 | `qpon_rpt_d` → `qpon_dim_d` |
| 16 | `qpon_data_server_d` → `qpon_ods_d` |
| 12 | `qpon_email_date_d` → `qpon_ods_d` |
| 10 | `qpon_dws_d` → `qpon_dwd_d` |
| 10 | `qpon_rpt_h` → `qpon_ods_h` |
| 9 | `qpon_dws_d` → `qpon_ods_d` |
| 9 | `qpon_email_date_d_test` → `qpon_ods_d_test` |
| 9 | `qpon_tag_d` → `qpon_ods_d` |
| 8 | `qpon_analyst_d` → `qpon_dwd_d` |
| 8 | `qpon_data_server_d_test` → `qpon_ods_d_test` |
| 8 | `qpon_dim_h` → `qpon_ods_h` |
| 8 | `qpon_tag_d` → `qpon_dwd_d` |
| 7 | `qpon_analyst_d` → `qpon_dim_d` |
| 7 | `qpon_rpt_d` → `qpon_dws_d` |
| 6 | `qpon_dwd_d` → `qpon_dim_d` |
| 6 | `qpon_dws_h` → `qpon_dwd_h` |
| 5 | `qpon_rpt_h` → `qpon_dwd_h` |
| 4 | `qpon_dws_d` → `qpon_dim_d` |
| 3 | `qpon_analyst_d` → `qpon_dws_d`；`qpon_data_server_d` → `qpon_dwd_d`/`qpon_dim_d`；`qpon_dim_d` → `qpon_dwd_d`；`qpon_dwd_d_test` → `qpon_ods_d_test`；`qpon_risk_d` → `qpon_ods_d`/`qpon_dim_d`；`qpon_tag_d` → `qpon_dws_d` |
| ≤2 | `qpon_analyst_alarm_*`、`qpon_risk_d`↔多层、`qpon_rpt_d`→`qpon_analyst_d`/`qpon_data_server_d`、`qpon_ods_d`→`Qpon_Adjust_Raw_Data`、`qpon_test_d`→`qpon_dwd_h` 等（共 53 个唯一 (src,upstream) 对） |

被等待上游 dag_id 全集：`Qpon_Adjust_Raw_Data`、`qpon_analyst_d`、`qpon_analyst_h`、`qpon_data_server_d`、`qpon_dim_d`、`qpon_dim_h`、`qpon_dwd_d`、`qpon_dwd_h`、`qpon_dws_d`、`qpon_ods_d`、`qpon_ods_d_test`、`qpon_ods_h`、`qpon_rpt_d`。

**注释模板残留（非活边）**：多处入口存在已注释的 `create_external_sensor(dag, "ods_t_act_award", "ods_t_act_award")`——将 **task 名误作 dag_id** 的复制粘贴模板；活扫描中 suspicious=0，但改模板时仍属契约风险。

---

### 2. DTO/请求/响应对象清单

N/A：无 Java DTO/Req/Resp。等价物 = **`qpon_metadata/schemas/**` pydantic `BaseModel`**（16 个）+ 工厂调用的隐式「请求三元组」`(dag, warehouse_path, task_module_name)`。

#### 2.A 工厂隐式请求契约

| 类名（逻辑） | 包路径 | 所属接口 | 字段 | 继承 |
|---|---|---|---|---|
| `ComposerTaskRequest`（逻辑名） | 运行时参数 | `create_composer_bq_task` / `create_composer_python_task` / `Check_BQ_Data_IsExists_Operator` | `dag: DAG`; `warehouse_path: str`; `task_module_name: str`; `on_failure_callback: Optional[Callable]=None` | — |
| `ExternalSensorRequest`（逻辑名） | 运行时参数 | `create_external_sensor*` | `dag`; `dag_name`（upstream_dag）; `task_name`; `timeout`; `poke_interval`; `priority_weight`; `on_failure_callback` | — |
| `EsWriteRequest`（逻辑名） | Cloud Run POST body | `access_cloud_run_write_aliyun_es` | `host`; `select_sql`; `es_index_name`; `id_field`; `api_key`; 可选 `user_name`/`password` | — |

#### 2.B pydantic Schema（DTO）

| 类名 | 全限定路径 | 所属接口（引用方） | 字段（按声明序提炼） | 继承 |
|---|---|---|---|---|
| `MysqlProfile` | `qpon_metadata.schemas.gcp.datastream.connection_profile` | `DatastreamApi` / ConnectionProfile.mysqlProfile | `hostname: str`; `port: int`; `username: str`; `password: str`; `sslConfig: Optional[Dict]`; `secretManagerStoredPassword: Optional[str]`（共 6） | BaseModel |
| `ConnectionProfile` | 同上 | `DatastreamApi.get_connection_profile` | `name`; `displayName`; `createTime`; `updateTime`; `labels` + 「共 13 个字段」 | BaseModel |
| `ListConnectionProfilesResponse` | 同上 | Datastream list API | `ConnectionProfiles: Optional[List[ConnectionProfile]]`; `nextPageToken`; `unreachable` | BaseModel |
| `StreamObject` | `…datastream.object` | `DatastreamApi.list_stream_objects` | `name`; `sourceObject`; `displayName`; `backfillJob`; `errors`; `createTime`; `updateTime`（共 7） | BaseModel |
| `ListStreamObjectsResponse` | 同上 | 同上 | `streamObjects: Optional[List[StreamObject]]`; `nextPageToken` | BaseModel |
| `Stream` | `…datastream.stream` | `DatastreamApi.list_streams` | `name`; `displayName`; `createTime`; `updateTime`; `labels` + 「共 11 个字段」 | BaseModel |
| `ListStreamsResponse` | 同上 | 同上 | `streams: Optional[List[Stream]]`; `nextPageToken`; `unreachable` | BaseModel |
| `Aggregation` | `…monitoring.incident` | Incident.condition… | `alignmentPeriod: str`; `perSeriesAligner: str` | BaseModel |
| `ConditionThreshold` | 同上 | Condition | `filter`; `aggregations: List[Aggregation]`; `comparison`; `thresholdValue`; `duration`; `trigger`（共 6） | BaseModel |
| `Condition` | 同上 | Incident | `name`; `displayName`; `conditionThreshold: ConditionThreshold` | BaseModel |
| `Link` | 同上 | Documentation | `displayName`; `url` | BaseModel |
| `Documentation` | 同上 | Incident | `content`; `mime_type`; `subject`; `links: List[Link]` | BaseModel |
| `Incident` | 同上 | `gcp_monitoring_alert` / IncidentData | 主键/状态：`incident_id`; `scoping_project_id`; `state`; `started_at`; `ended_at` + 「共 24 个字段」 | BaseModel |
| `IncidentData` | 同上 | Pub/Sub 告警载荷 | `version: str`; `incident: Incident` | BaseModel |
| `ColumnMeta` | `qpon_metadata.schemas.meta.column_meta` | `MysqlMetaMixin.list_column_metas` / `sync_column_meta` | `id`; `database_name`; `table_name`; `column_name`; `data_type` + 「共 18 个字段」 | BaseModel |
| `TableMeta` | `qpon_metadata.schemas.meta.table_meta` | `MysqlMetaMixin.list_table_metas` / `sync_table_meta` | `id`; `database_name`; `schema`; `table_name`; `table_type` + 「共 13 个字段」 | BaseModel |

共 **16** 个 DTO（含逻辑请求 3 个则业务 Schema 为 16），分布在 **4** 个子包：`schemas.gcp.datastream`、`schemas.gcp.monitoring`、`schemas.meta`、（逻辑）`airflow_config` 参数面。

---

### 3. 枚举定义清单

N/A：`dags/` 内 **0** 个 `Enum`/`IntEnum`/`StrEnum`/`Flag` 类定义。

等价「枚举行为」的代码事实（非 Enum 类型）：

| 名称 | 路径 | 取值 / 含义 | 引用 |
|---|---|---|---|
| Sensor `allowed_states` | `create_external_sensor.py` | `['success']` | ExternalTaskSensor |
| Sensor `failed_states` | 同上 | `['failed']` | ExternalTaskSensor |
| `ExternalTaskSkipSensor` 分支 | 同上 `poke` | SUCCESS / SKIPPED / FAILED / RUNNING\|QUEUED\|SCHEDULED\|UP_FOR_RETRY | Airflow `State` |
| ES `date_operator`（注释文档） | `cloud_run_delete_aliyun_es.py` | `<=,<,>=,>,=,between`（文档描述；现行函数已改为 term/terms） | 删除侧车 |

---

### 4. 常量定义清单

N/A：无 Java `constant/` / `DubboConstants`。等价常量如下。

#### 4.A `airflow_config` 模块级常量

| 类/模块 | 常量名 | 值 | 注释 |
|---|---|---|---|
| `read_feishu_to_bg` | `FEISHU_APP_ID` | `cli_a9e313099e389bc7` | Variable 读取被注释；明文硬编码 |
| `read_feishu_to_bg` | `FEISHU_APP_SECRET` | `[REDACTED]`（源码明文存在） | 同上；改动即凭证契约变更 |

#### 4.B 共享运行时钉死常量（工厂内）

| 位置 | 常量语义 | 值 |
|---|---|---|
| `create_composer_bq_task.py` L22 | BQ query location | `asia-southeast2` |
| `create_check_table_data.py` L20 | BQ check location | `asia-southeast2` |
| `create_check_table_data.py` L19 | gcp_conn_id | `google_cloud_default` |
| `create_external_sensor` | 默认 timeout / poke / retries | `64800` / `600` / `1000` |
| `create_external_sensor_hour` | 默认 timeout / poke / retries | `7200` / `300` / `20` |
| `elasticsearch_write_operator.excuete_write_es` | 默认 BQ project | `oppo-gcp-prod-digfood-129869` |

#### 4.C `qpon_metadata.utils.variables`（Variable 契约 = Dubbo group/version 等价）

| 常量名 | 来源 | 默认/形态 |
|---|---|---|
| `COMPOSER_GCS_BUCKET` | `Variable.get("composer_gcs_bucket")` | `gs://` + value |
| `PROJECT_HOME` | `project_home` 或 `AIRFLOW_HOME` | str |
| `DBT_PROFILE_NAME` | `dbt_profile_name` | 默认 `qpon` |
| `DBT_PROFILE_TARGET` | `dbt_profile_target` | 默认 `dev` |
| `DBT_DEFAULT_PATH` | 派生 | `dags/dbt/{target}` |
| `QPON_GCP_PROJECT_ID` / `QPON_GCP_LOCATION` | Variable（被 DatastreamApi 默认注入） | 与主项目/location 对齐 |

其他被 `Variable.get` 引用的 Key（契约坐标）：`write_es_service_url`、`es_hosts`、`es_user_name`、`es_password`、`es_api_key`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`etl_alter_webhook_url`、`gcp_alter_webhook_url`、`owner_job_no_dict`、`qpon_gcp_project_id`、`qpon_gcp_location`。

#### 4.D 元数据 Connection 前缀

| 常量 | 值 | 用途 |
|---|---|---|
| `ETL_CONNECTION_PREFIX`（`sync_source_meta.py`） | `datastream-` | 枚举 Airflow Connection 做源库元数据同步 |

---

### 5. 子包结构全景图

N/A：无 `qpon-bigdata-client/src/main/java` 包树。等价「client 面」= `airflow_config` + `qpon_metadata/schemas` + 各 DAG 入口。

```
dags/                                    # 权威根（1167 .py / Step01）
├── airflow_config/                      # 11 .py — 对外共享契约（client 核心）
│   ├── create_composer_bq_task.py       # BQ/Python 任务工厂
│   ├── create_external_sensor.py        # 跨 DAG Sensor / SkipSensor
│   ├── create_external_marker.py        # 下游 Marker
│   ├── create_check_table_data.py       # BQ Check 工厂
│   ├── airflow_tt_send.py               # TT 告警
│   ├── cloud_run_write_aliyun_es.py     # ES 写入（Cloud Run）
│   ├── cloud_run_delete_aliyun_es.py    # ES 删除
│   ├── elasticsearch_write_operator.py  # ES Operator + 侧车
│   ├── read_feishu_to_bg.py             # 飞书→BQ
│   └── util.py                          # 文本工具
├── qpon_metadata/
│   ├── schemas/
│   │   ├── gcp/datastream/              # 3 模型文件（ConnectionProfile/Stream/Object）
│   │   ├── gcp/monitoring/              # Incident 载荷模型
│   │   └── meta/                        # TableMeta / ColumnMeta
│   ├── utils/                           # DatastreamApi / MetaMixin / Teamtalk / variables
│   ├── gcp_monitoring_alert.py
│   ├── sync_source_meta.py
│   └── sync_bigquery_staging_description.py
├── {qpon_ods,dim,dwd,dws,rpt,tag,...}_* /  # 业务 DAG 包（入口 = 对外调度 API）
├── data_options/ / task_kill/ / Qpon_Adjust_Raw_Data/
├── qpon_staging_d/ / qpon_search_d/ / qpon_daily_report/
└── …
```

旧文档未覆盖子包：NO_DOCS → 全部视为 🆕。

---

### 6. 接口依赖与契约耦合分析

N/A：无 client `pom.xml` 外部 client JAR。耦合点改为 **运行时/跨系统契约**：

| 耦合点 | 证据 | 标记 |
|---|---|---|
| BigQuery project/location | 工厂钉死 `asia-southeast2`；FQN/`Client(project='oppo-gcp-prod-digfood-129869')` | ⚠️ 契约耦合点 |
| Airflow ExternalTaskSensor 跨 DAG | 441 活边；改上游 `task_id`/`dag_id` 即 breaking | ⚠️ 契约耦合点 |
| task 导出名 = 模块名 = task_id | `getattr(module, task_module_name)` | ⚠️ 契约耦合点 |
| Cloud Run ES 服务 | `Variable write_es_service_url` + `/health` + `/api/write-to-es` | ⚠️ 契约耦合点 |
| 阿里云 Elasticsearch | Variables `es_*`；直连 Operator 另含内网 `http://10.3.13.241:19527` | ⚠️ 契约耦合点 |
| 飞书 OpenAPI | `open.feishu.cn`；硬编码 AppId/Secret | ⚠️ 契约耦合点 |
| TeamTalk / MTP Webhook | `mtp.myoas.com`；DAG 入口 `yzjtoken` 硬编码 | ⚠️ 契约耦合点 |
| Datastream REST | `datastream.googleapis.com/v1/projects/{QPON_GCP_PROJECT_ID}/locations/{QPON_GCP_LOCATION}` | ⚠️ 契约耦合点 |
| Airflow Connection 前缀 | `datastream-*` | ⚠️ 契约耦合点 |
| ExternalTaskMarker → alarm DAG | `qpon_rpt_d` → `qpon_analyst_alarm_d`（2） | ⚠️ 契约耦合点 |
| 层依赖倒置边 | `qpon_dim_d`→`qpon_dwd_d`(3)、`qpon_dwd_d`→`qpon_dws_d`(2)、`qpon_risk_d`→`qpon_rpt_d`(1) 等 | ⚠️ 契约耦合点 |
| 注释错误模板 | `create_external_sensor(dag, "ods_t_act_award", …)` | ⚠️ 契约耦合点（模板污染） |

`qpon_metadata` 辅助对外 API（非 airflow_config，但属仓内可复用契约）：

| 符号 | 签名要点 |
|---|---|
| `DatastreamApi.__init__(project_id=QPON_GCP_PROJECT_ID, location=QPON_GCP_LOCATION)` | |
| `DatastreamApi.get_connection_profile(connection_profile)` → `ConnectionProfile` | |
| `DatastreamApi.list_streams()` → `ListStreamsResponse` | |
| `DatastreamApi.list_stream_objects(stream_name, page_size=100, page_token=None)` | |
| `DatastreamApi.list_all_stream_objects(stream_name, page_size=1000)` → `list[StreamObject]` | |
| `MetaMixin` / `MysqlMetaMixin.list_schemas/list_table_metas/list_column_metas` | |
| `TeamtalkRobot.send_text` / `create_common_teamtalk_alter_callback(webhook_url)` | |

---

### 7. 旧文档交叉验证摘要

NO_DOCS：本节跳过声称级 ❌/🆕/✅ 分条验证。

🆕相对空旧文档的代码事实：对外契约面是 Composer 共享工厂 + ExternalTaskSensor 边表 + pydantic Schema，而非 Dubbo 接口 JAR。

---

> [!SUCCESS] 对外契约测绘闭环验证
> - 扫描范围：`dags/` 权威根；client 等价 = `airflow_config/` 10 个业务 `.py` + 全量 DAG 入口 `create_*` 调用 + `create_external_sensor*` 活边 + `qpon_metadata/schemas` 16 个 BaseModel（禁止 scripts/、ai-knowledge-knowledge/）
> - 提取结果：18 个共享库对外符号（函数/类）、约 30 个 DAG 入口调度契约、1077 处工厂任务注册（BQ 1001 / Python 75 / Check 1）、441 条活 Sensor 边（407+34）、2 条 Marker、16 个 DTO（pydantic）、0 个 Enum、常量面含 FEISHU_*/Variable Keys/BQ location 钉死值
> - 子包覆盖：airflow_config；qpon_metadata.schemas.{gcp.datastream,gcp.monitoring,meta}；qpon_metadata.utils；各 `qpon_*` / data_options / task_kill / Qpon_Adjust_Raw_Data / qpon_staging_d / qpon_search_d / qpon_daily_report 入口
> - 旧文档差异：❌不符 N/A 条 / 🆕新发现 N/A 条 / ✅其余 N/A 条已验证（NO_DOCS）
> - EOF 状态：已确认遍历 `airflow_config` 全文件、DAG 入口工厂/Sensor 全量正则扫描、schemas 16 模型至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 对外契约入口为 `airflow_config.create_composer_bq_task`/`create_composer_python_task`/`create_external_sensor`；task 导出名必须等于模块名；BQ location 钉死 `asia-southeast2`，主 project `oppo-gcp-prod-digfood-129869`；活跨 DAG 边 441 条（ods→dim/dwd→dws→rpt 为主）；ES 经 Cloud Run（`write_es_service_url`）与直连 Operator；飞书/TT/Datastream 为旁路 HTTP 契约；pydantic Schema 集中在 `qpon_metadata/schemas`
> - **推演约束 (Constraint)**: Step 03 下游依赖分析必须：① 沿 441 条 Sensor 边与 1077 工厂任务展开 task 模块内 BQ FQN/SQL 依赖；② 追踪 `access_cloud_run_write_aliyun_es`/`ReadFeiShuToBigQuery.write_to_bigquery`/`DatastreamApi` 的数据落点；③ 对命名例外 5 个 task 文件单独核对是否被工厂引用；④ 禁止从 scripts/ 取业务依赖事实
> - **物理锚点 (Anchors)**: `dags/airflow_config/create_composer_bq_task.py:7,30`；`dags/airflow_config/create_external_sensor.py:10,27,125`；`dags/airflow_config/cloud_run_write_aliyun_es.py:5`；`dags/airflow_config/read_feishu_to_bg.py:22`；`dags/qpon_ods_d/qpon_ods_d.py`；`dags/qpon_dwd_d/qpon_dwd_d.py`；`dags/qpon_rpt_d/qpon_rpt_d.py`；`dags/qpon_metadata/schemas/meta/{table_meta,column_meta}.py`；`dags/qpon_metadata/utils/datastream.py:17`
