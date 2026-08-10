# 08l 模块深潜：元数据与GCP监控（metadata）

> 模块 id=`metadata`；权威范围=`dags/`（重点 `dags/qpon_metadata/`）  
> 不重复 Step05 全链；本步钻取 **is_paused_upon_creation**、**Variable 集中点**、**Pub/Sub 监控静默**、**schema 契约**  
> Step08k 接力：(1) 出口层未消化 hour-Skip（alarm_h 反例仍在）；(2) ES raise 红 vs 吞异常绿；(3) 维表/特征 `2999` 读写语义分开；(4) 勿把 GenAI fallback 或 alarm `datetime.now()` 当可信业务日；(5) device_active SLA=tag∪rpt-d∪analyst-serving  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以用户指令 id=`metadata`/suffix=`l` + `step-08-metadata_prompt.md` 为准  
> **边界**：`tag_qpon_metadata` 属 tag-d（08j），**不是**本包；本包写 `qpon_meta.meta_source_*`

> [!SUCCESS] 元数据与GCP监控 模块深潜闭环验证
> - 扫描范围：DAG 入口×3 + utils×4 + schemas（meta×2 / monitoring×1 / datastream×3）+ `__init__` 空壳；包内 import 闭环（他包 0 处 `from qpon_metadata`）
> - 提取结果：8 个入口方法、8 条衍生约束、4 个业务特性章节
> - 全文行数：167 行（≤ 400 行）
> - 前序验证：Step 02 契约=pydantic+Variable+Datastream REST / Step 03 下游=Pub/Sub·TT·BQ·Datastream API / Step 04 实体=`qpon_meta.meta_source_{table,column}`
> - EOF 状态：`qpon_metadata/` 20 文件已读至 EOF；无静默截断

---

## A. 模块定位

`qpon_metadata` 是仓内**横切元数据与 GCP 组件监控旁路**：同步 MySQL 源表/列注释到 BQ `qpon_meta`、经 Datastream 回写 staging 表/列 description、以及 Pub/Sub Incident→TT；**不参与** ODS→DWD→RPT 主链 Sensor，也不消费 device_active / ES / 标签水位。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `gcp_monitoring_alert` | Orchestrator | `*/1` 拉 Pub/Sub→解析 Incident→TT |
| `sync_source_meta` | Orchestrator | `@daily` 扫 `datastream-*` Connection→写 meta 表/列 |
| `sync_bigquery_staging_description` | Orchestrator | `schedule=None`；Datastream RUNNING 流→ALTER BQ description |
| `variables` | Config | Variable 集中导出（GCP/告警/DBT/owner） |
| `TeamtalkRobot` / `create_common_teamtalk_alter_callback` | Handler/Factory | TT Variable webhook；common callback **仓内 0 活调用** |
| `MetaMixin` / `MysqlMetaMixin` / `META_MIXIN_DICT` | Repository | INFORMATION_SCHEMA→`TableMeta`/`ColumnMeta`；仅 `mysql` |
| `DatastreamApi` | Executor | Datastream REST list/get；`get_connection_profile` **无活调用** |
| `TableMeta` / `ColumnMeta` | Schema | BQ `qpon_meta` 行契约 + `id` 生成器 |
| `IncidentData` / `Incident`（+嵌套） | Schema | Monitoring 通知 JSON 契约 |
| `Stream` / `StreamObject` / `ConnectionProfile` | Schema | Datastream API 响应契约 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `gcp_monitoring_alert` parse | Composer | 注册 PubSubPull + `monitoring_alert` |
| DAG `sync_source_meta` parse | Composer | 注册 `sync_table_meta` / `sync_column_meta`（无边） |
| DAG `sync_bigquery_staging_description` parse | Composer/人工 | collect→表/列 description 扇出 |
| `monitoring_alert` | `send_tt_alter` | XCom 消息→`IncidentData`→TT 文本 |
| `sync_table_meta` / `sync_column_meta` | 同名 PythonOperator | DELETE 当日库分区切片 + load JSON |
| `collect_datastream_objects` | collect 任务 | 仅 RUNNING stream→schema/table 清单 XCom |
| `sync_table_description` / `sync_column_description` | 同名任务 | 对比 meta 注释 vs INFORMATION_SCHEMA→ALTER |
| `TeamtalkRobot.send_text` / `_send` | 监控任务（及死 callback） | POST webhook；失败 `logger.error` |

---

## D. 调用链（引用 Step05，不重复追踪）

- 监控：`wait_for_pubsub`（ack）→ `monitoring_alert`→`TeamtalkRobot`（05 §A.12）。
- 源元数据：Connection 前缀过滤→`MysqlMetaMixin`→BQ `qpon_meta.meta_source_{table,column}`。
- staging 描述：`DatastreamApi.list_streams`→objects→读最新 `sync_date` meta→`ALTER TABLE/COLUMN … OPTIONS(description=…)`。
- 与主 ETL：**弱耦合**；无 ExternalTaskSensor 进出本包。`tag_qpon_metadata` 水位链见 08j，勿混读。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | schemas 16 BaseModel；Variable；Datastream REST；`datastream-*` Connection | ✅；`get_connection_profile` 仍无活调用 |
| 03 下游 | Pub/Sub sub、TT、BQ、Datastream HTTP | ✅；无 ES/飞书/主链 Sensor |
| 04 实体 | `qpon_meta.meta_source_*`（DDL 注释在 schema 文件头） | ✅；≠ `tag_qpon_metadata` |
| 06 异步 | 唯一 PubSub Listener；`max_active_runs=1`；ack 后解析失败不重投 | ✅；见 §G |
| 07 配置 | 三 DAG `is_paused_upon_creation=True`；`gcp_alter` 有消费 / `etl_alter` 无 | ✅；见 §H |

**08k 接力回执（本包不消化）**：本模块无 hour-DAG Sensor、无 ES 写、无 `2999`、无 GenAI/alarm 业务日；收官仍须保留 alarm_h Skip 违规、ES raise/吞异常、2999 读写分审、不可信业务日、device_active=tag∪rpt-d∪analyst-serving。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08l-01 | 部署/同步 Composer 后必须 Unpause 三 metadata DAG，或改 `is_paused_upon_creation=False` 并文档化；禁止默认假设监控已活 | 三 DAG `is_paused_upon_creation=True` | Pub/Sub→TT / meta 同步整链静默 |
| C-08l-02 | `gcp_alter_webhook_url` 生产非空；空串时禁止宣称「GCP 组件已告警到 TT」 | `GCP_ALTER_WEBHOOK_URL`；`TeamtalkRobot._send` | HTTP 打空 URL；监控假覆盖 |
| C-08l-03 | 新增 Variable 消费须从 `variables.py` 接线；禁止新增硬编码 TT token；`etl_alter_webhook_url`/`create_common_teamtalk_alter_callback` 要么接到业务 DAG 要么删除（已知技术债，禁止复制死配置） | `variables`；callback 0 调用 | 双轨告警；配置「已配未生效」 |
| C-08l-04 | Pub/Sub `ack_messages=True` + 解析 `except continue`：坏消息不可靠重投；改解析须兼容 `IncidentData` 或先校验再 ack | `monitoring_alert`；`PubSubPullSensor` | Incident 丢告警且任务仍绿 |
| C-08l-05 | `meta_source_*` 幂等键=`sync_date`+`database_name`（行 `id` 再含 schema/table[/column]）；重跑依赖 DELETE 同日同库切片；`sync_date=date.today()`≠`execution_date` | `TableMeta`/`ColumnMeta.generate_id`；`sync_*_meta` DELETE | 跨日重复切片或错删 |
| C-08l-06 | BQ `load_table_from_json` 失败仅 `logger.error` 不 raise——视为**吞异常绿**；排障勿等同「raise 红」路径（对照 data_server ES） | `sync_table_meta`/`sync_column_meta` except | 元数据空洞但 DAG SUCCESS |
| C-08l-07 | staging 描述仅处理 Datastream `state==RUNNING`；改 destination 模式须同步 `get_dataset_id_and_table_name_prefix`（singleTarget vs sourceHierarchy） | `collect_datastream_objects`；`get_dataset_id_and_table_name_prefix` | 改错 dataset/表前缀或 ValueError |
| C-08l-08 | 禁止把本包当 SLA 对账源：勿用 meta `sync_date`/`etl_time` 或监控 `started_at` 替代 ADS/DAU 业务日；device_active 变更评估集仍为 **tag∪rpt-d∪analyst-serving** | 本包无 device_active/日报读边 | 误用旁路时钟掩盖出口债 |

---

## G. Pub/Sub 监控与 paused 静默

**业务背景**：GCP Monitoring 告警经固定 subscription 入仓，再转 TT；与业务 DAG 硬编码 `TtSend` 双轨。

**实现方式**：`schedule=*/1`，`retries=0`，`max_active_runs=1`，`is_paused_upon_creation=True`。`PubSubPullSensor`：`subscription=qpon-data-gcp-component-monitoring-sub`，`ack_messages=True`，`max_messages=1`，`poke_interval=10`。`monitoring_alert`：base64→JSON→`IncidentData`→拼 subject/policy/started_at(上海)/summary/url→`TeamtalkRobot(GCP_ALTER_WEBHOOK_URL).send_text`。

**关键决策点**：
- DAG 构造 — `is_paused_upon_creation=True` → 新建默认可静默直至 Unpause。
- `monitoring_alert` — 单条 `except` → `warning`+`continue`（任务仍 SUCCESS）。
- `TeamtalkRobot._send` — `success!=True` → `logger.error`（不 raise）。
- Sensor — ack 后无重投窗口；坏载荷永久丢失。

**失败模式**：Composer 仍 paused → 整链不跑；Variable 空 → POST 无效；解析失败 → 绿但无 TT。排障：先查 paused / Variable / task log「无法解析消息体」。

---

## H. Variable 集中点与死接线

**业务背景**：本包是仓内少数「Variable 常量导出」点；业务失败回调多数未接入。

**实现方式**：`variables.py` 导出 `COMPOSER_GCS_BUCKET`、`PROJECT_HOME`、`DBT_*`、`OWNER_JOB_NO_DICT`、`ETL_ALTER_WEBHOOK_URL`、`GCP_ALTER_WEBHOOK_URL`、`QPON_GCP_PROJECT_ID`（默认 prod project）、`QPON_GCP_LOCATION`（默认 `asia-southeast2`）。活消费：`GCP_ALTER`+`QPON_GCP_*`（监控/同步/Datastream）；`OWNER_JOB_NO` 仅死 callback。`COMPOSER_GCS`/`DBT_*`/`ETL_ALTER`/`PROJECT_HOME`：**包内无引用**。

**关键决策点**：
- `create_common_teamtalk_alter_callback` — 按 `dag.tasks.owner`∈`OWNER_JOB_NO_DICT` @人 → **0 活调用**。
- 对照 `airflow_config.TtSend` — 硬编码 yzjtoken；失败常 print 吞（08a）。
- 本包 `TeamtalkRobot` — 失败打 error（优于业务 print），但监控路径仍可不 raise。

**失败模式**：「已配 `etl_alter_webhook_url`」≠业务可触达。治理须先接线再删硬编码（07 G-07-08）。

---

## I. 源元数据同步与幂等

**业务背景**：从 Airflow MySQL Connection（Datastream 源）抽 INFORMATION_SCHEMA，落地 BQ 供注释回写。

**实现方式**：`get_etl_connections` 过滤 `conn_id.startswith("datastream-")`。`META_MIXIN_DICT["mysql"]` only。`database_name` 先=conn_id，再 strip 前缀。分页 `LIMIT/OFFSET`。每连接：DELETE `sync_date`+`database_name` → `load_table_from_json` APPEND。表/列任务**无** `>>` 边，可并行。`retries=0`，`is_paused_upon_creation=True`。

**关键决策点**：
- 非 mysql conn_type — `warning`+`continue`。
- load 异常 — `error` **不 raise**（吞异常绿）。
- `TableMeta.sync_date` — `date.today()`；`etl_time` — `datetime.now()`（日历日，非 logical_date）。
- `id` — `{sync_date}_{database_name}_{schema}_{table}[_column]`。

**失败模式**：paused→不同步；load 失败→当日切片空洞；today 跨时区边界与 execution 错位。勿与标签 `MERGE tag_qpon_metadata.latest_dayno` 混淆。

---

## J. Schema 契约与 staging 描述回写

**业务背景**：注释权威在源 meta；回写 Datastream 落地的 BQ staging，依赖 pydantic 契约与 destination 模式分支。

**实现方式**：`schedule=None`（手动）。collect 跳过非 RUNNING；`displayName` split `schema.table`，`-`→`_`。`get_dataset_id_and_table_name_prefix`：`singleTargetDataset`→dataset+`{schema}_` 前缀；`sourceHierarchyDatasets`→prefix+schema；否则 ValueError。SQL 仅 `max(sync_date)` 且注释非空、表/列已存在、description 不一致时 ALTER；列批大小 1000。

**关键决策点**：
- `IncidentData(**data)` — 字段不符→进 §G continue。
- `Stream(**xcom)` — 缺 `bigqueryDestinationConfig` 合法键→ValueError（任务红）。
- `DatastreamApi.get_connection_profile` — 已实现无调用；勿当投产 API。
- ALTER 注释内嵌引号 — 依赖上游清洗；恶意/异常注释可致 SQL 脆断。

**失败模式**：meta 未先跑/非最新 sync_date→无可改行；stream 非 RUNNING→静默跳过；destination 模式未覆盖→硬失败。

---

> [!SUCCESS] 元数据与GCP监控 模块深潜闭环验证
> - 扫描范围：20 个 `qpon_metadata` 文件（DAG×3 + utils×4 + schema 模型×6 + 空 `__init__`×若干）
> - 提取结果：8 个入口方法、8 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：167 行（≤ 400 行）
> - 前序验证：Step 02 ✅ pydantic/Variable/Datastream / Step 03 ✅ PubSub·TT·BQ / Step 04 ✅ `qpon_meta.meta_source_*`
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 三 DAG 均 `is_paused_upon_creation=True`+`max_active_runs=1`+`retries=0`；监控=`PubSubPullSensor(ack=True)`→解析失败 continue→TT Variable；源 meta DELETE+load 失败吞异常绿；`variables.py` 为 Variable 集中点但 `etl_alter`/common callback/DBT/GCS 常量死接线；schemas 契约服务 Incident/Datastream/meta；与主链无 Sensor；≠`tag_qpon_metadata`。08k 出口债（alarm_h 日工厂等小时、ES raise/吞、2999 读写、不可信业务日、device_active 三方扇出）**未被本包消化**。
> - **推演约束 (Constraint)**: 收官/下一模块必须 (1) 核对生产 Unpause+`gcp_alter_webhook_url` 非空；(2) 告警治理优先接线 `etl_alter`+`TeamtalkRobot` 再删硬编码；(3) 区分本包「load/解析吞绿」与 data_server「ES raise 红」；(4) 对账 ADS/DAU **禁止**用 meta `date.today`/监控时钟/GenAI fallback/alarm `now()`；(5) device_active SLA 评估集仍为 **tag∪rpt-d∪analyst-serving**；(6) 勿假设 hour-Skip 军规已在出口层闭环（alarm_h 反例仍在）。
> - **物理锚点 (Anchors)**: `dags/qpon_metadata/gcp_monitoring_alert.py` L19–69；`dags/qpon_metadata/utils/variables.py` L6–24；`dags/qpon_metadata/utils/teamtalk.py` L14–83；`dags/qpon_metadata/sync_source_meta.py` L40–170；`dags/qpon_metadata/sync_bigquery_staging_description.py` L18–256；`dags/qpon_metadata/utils/datastream.py` L17–78；`dags/qpon_metadata/utils/meta_mixin.py` L30–188；`dags/qpon_metadata/schemas/meta/{table_meta,column_meta}.py`；`dags/qpon_metadata/schemas/gcp/monitoring/incident.py`
