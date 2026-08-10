# 01_Module_Skeleton_and_Stack — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）  
> 物理规模：33 个顶层包 · 1167 个 `.py`  
> Legacy：NO_DOCS（`Legacy_qpon-bigdata_Claims.md` 无声称可交叉验证）

---

### 1. 模块依赖关系图

N/A：本项目无 `pom.xml` / Maven 子模块。等价物为 **DAG 包 + 共享库包**，依赖关系由 Python `import` 与 `ExternalTaskSensor`（`create_external_sensor`）表达。

#### 1.1 物理包树（`dags/`）

```
dags/
├── __init__.py
├── airflow_config/          # 共享算子/工具库（被业务 DAG import，非独立调度 DAG）
├── qpon_metadata/           # 元数据/监控 DAG + schemas/utils
├── data_options/            # 运维类 DAG（清理/导出/写 ES）
├── task_kill/               # BQ Job 监控杀进程
├── Qpon_Adjust_Raw_Data/    # Adjust 原始数据外部表
├── qpon_search_d/           # 搜索特征导出（单文件 DAG）
├── qpon_staging_d/          # Dataproc/Spark 同步作业 DAG
├── qpon_ods_{d,h,d_test}/   # ODS 层
├── qpon_dim_{d,h}/          # DIM 层
├── qpon_dwd_{d,h,d_test}/   # DWD 层
├── qpon_dws_{d,h}/          # DWS 层
├── qpon_rpt_{d,h}/          # RPT/ADS 报表层
├── qpon_tag_{d,d_test}/     # 标签层
├── qpon_analyst_{d,h}/      # 分析师 ADS
├── qpon_analyst_alarm_{d,h}/# 分析告警
├── qpon_data_server_{d,d_test}/
├── qpon_email_date_{d,d_test}/
├── qpon_risk_d/             # 风控特征
├── qpon_daily_report/       # 日报 + LLM 叙事
├── qpon_review_score_test/
└── qpon_test_d/
```

#### 1.2 共享库依赖（compile 等价 = runtime import）

| 依赖方（scope） | 被依赖包 | 推测用途 |
|---|---|---|
| 几乎全部业务 DAG（runtime） | `airflow_config.*` | BQ/Python 任务工厂、跨 DAG Sensor、TT 告警、飞书→BQ、ES 写入 |
| `qpon_metadata` DAGs（runtime） | `qpon_metadata.utils` / `schemas` | Variable 封装、Datastream/MySQL 元数据、监控 Incident 模型 |
| `qpon_daily_report`（runtime） | `qpon_daily_report.tasks` / `config` | 日报计算与叙事 |
| 业务 task 模块（runtime） | `google.cloud.*` / `pandas` / `requests` | BQ/GCS/HTTP 侧车逻辑 |

`airflow_config` **不**被其他包反向依赖以外的形式声明版本；仓库内 **无** `requirements.txt` / `pyproject.toml` 锁定依赖版本。

#### 1.3 跨 DAG 等待边（ExternalTaskSensor，literal 调用 ≥504）

主链路（日批 `0 18 * * *`）：

```
qpon_ods_d
  ├──► qpon_dim_d
  ├──► qpon_dwd_d ──► qpon_dws_d ──► qpon_rpt_d
  ├──► qpon_tag_d / qpon_analyst_d / qpon_data_server_d / qpon_email_date_d / qpon_risk_d
  └──► Qpon_Adjust_Raw_Data（被 ods 等待）

小时批 `10 * * * *`：
qpon_ods_h ──► qpon_dim_h / qpon_dwd_h ──► qpon_dws_h / qpon_rpt_h / qpon_analyst_h
```

高频边（src → upstream_dag，次数）：

| 次数 | 边 |
|---:|---|
| 73 | `qpon_dwd_d` → `qpon_ods_d` |
| 62 | `qpon_rpt_d` → `qpon_ods_d` |
| 54 | `qpon_rpt_d` → `qpon_dwd_d` |
| 33 | `qpon_dim_d` → `qpon_ods_d` |
| 30 | `qpon_dwd_h` → `qpon_ods_h` |
| 20 | `qpon_rpt_d` → `qpon_dim_d` |
| 10 | `qpon_rpt_d` → `qpon_dws_d` |
| 10 | `qpon_rpt_d` → `qpon_rpt_d`（同 DAG 内任务互等） |

---

### 2. 核心中间件与第三方依赖雷达

N/A：无 Maven `groupId:artifactId`。下列为 `dags/` 内 import / Operator / Variable 实证的中间件与库（版本以 Composer 运行时为准，**仓库未钉死**）。

| 组件 | 证据锚点 | 推测用途 |
|---|---|---|
| Apache Airflow / Cloud Composer | `from airflow import DAG`；`BigQueryInsertJobOperator`；`providers.standard.sensors.*` | DAG 调度与编排 |
| Google BigQuery | `create_composer_bq_task` → `BigQueryInsertJobOperator`；FQN `` `oppo-gcp-prod-digfood-129869.*` `` 约 5989 处 | SQL ETL 主引擎；location=`asia-southeast2` |
| Google Cloud Storage | `google.cloud.storage`（搜索导出等）；`composer_gcs_bucket` Variable | 中间文件 / Composer bucket |
| Google Dataproc + PySpark | `dags/qpon_staging_d/spark_*.py`；`Dataproc*Operator`；`pyspark.sql.SparkSession` | MySQL→BQ / UG 触达记录 Spark 作业 |
| Google Datastream | `qpon_metadata/schemas/gcp/datastream/*`；Airflow Connection 前缀 `datastream-` | 源库元数据同步 |
| Google Pub/Sub | `PubSubPullSensor`（`gcp_monitoring_alert`）；SQL 引用 `pubsub_to_bq_qpon_events_collection` | 监控告警消费；事件数据集引用 |
| Google Secret Manager | `secretmanager.SecretManagerServiceClient`（`spark_mysql_to_bigquery.py`） | Spark 作业拉取 MySQL 密码 |
| Google GenAI | `google.genai`（`qpon_daily_report/tasks/generate_narrative.py`） | 日报 LLM 叙事 |
| MySQL | `airflow.providers.mysql` / SQLAlchemy MySQL dialect；Datastream 连接；Spark JDBC | 业务源库 / 元数据抽取 |
| Elasticsearch（阿里云 ES） | `elasticsearch`；`cloud_run_write_aliyun_es`；Variables `es_*` / `write_es_service_url` | BQ 结果写 ES；经 Cloud Run 服务代理 |
| 飞书 Open API | `read_feishu_to_bg.py`；`open.feishu.cn` | 审批/多维表/文档 → BQ |
| TeamTalk / MTP Webhook | `airflow_tt_send.TtSend`；Host `mtp.myoas.com` | 任务失败告警 |
| Adjust Reports API | `https://automate.adjust.com/reports-service/report` | 投放原始/日报数据 |
| pandas | 多处 task / 飞书读写 | 内存侧变换 |
| requests | TT / 飞书 / Cloud Run ES | HTTP 客户端 |
| pydantic | `qpon_metadata/schemas/**` | Datastream/Monitoring/Meta 模型 |
| dbt（配置坐标存在，作业未必在本仓） | Variables `dbt_profile_name` / `dbt_profile_target`；路径 `dags/dbt/{target}` | 元数据侧引用的 profile 坐标 |

**非 Spring Boot 重型依赖映射结论**：本系统重心是 **Composer + BigQuery SQL 仓**，旁路为 **Dataproc/Spark、ES 回写、飞书/Adjust 接入、TT 告警**。

---

### 3. 架构腐化预警（Red Flags）

1. **凭据硬编码**：`dags/airflow_config/read_feishu_to_bg.py` 明文 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`（Variable 读取被注释掉）。风险：密钥泄漏与无法按环境轮换。  
2. **告警 Webhook Token 硬编码**：多数 DAG 入口将 `yzjtoken=` 写死在 `send_url`（非 Variable）。风险：token 扩散、无法统一吊销。  
3. **数仓层依赖倒置/环状等待**：`qpon_dim_d`→`qpon_dwd_d`（3）、`qpon_dwd_d`→`qpon_dws_d`（2）、`qpon_rpt_d`→`qpon_rpt_d`（10）。风险：层语义被调度边打破，失败传播难排查。  
4. **Sensor 重试策略极端**：`create_external_sensor` 默认 `retries=1000`，覆盖 DAG `retries`。风险：失败任务长期占用 slot / 掩盖真实超时。  
5. **测试 DAG 与生产同仓同根**：`*_test` 包与生产包并列于 `dags/`，使用同类 cron。风险：误调度污染或争用 Composer 资源。  
6. **依赖版本未入库**：无 `requirements.txt`/`pyproject.toml`/`pom.xml`。风险：Composer 环境漂移导致「本地不可复现」。  
7. **废弃 API 大面积使用**：`airflow.operators.dummy.DummyOperator`、`provide_context=True`。风险：Airflow 大版本升级时批量破坏。  
8. **内网硬编码地址**：代码中出现 `http://10.3.13.241:19527`。风险：环境迁移后静默失效。  
9. **注释/残留错误的 external_dag_id**：扫描可见将任务名（如 `ods_t_act_award`）当作 `external_dag_id` 的注释或残留匹配。风险：复制粘贴导致错误等待边。

---

### 4. 配置文件坐标

N/A：无 `heracles.properties` / `application*.yml`。等价配置来源 = **Airflow Variable / Connection + 代码内常量 + BQ FQN**。敏感值一律 `[REDACTED]`。

#### 4.a 服务注册 / 调度身份

| 坐标 | 值 |
|---|---|
| 调度平台 | Google Cloud Composer（Airflow） |
| 主 DAG id 约定 | 包名 = `dag_name`（如 `qpon_ods_d`） |
| 特殊 DAG id | `qpon_search_store_fea_export`；`gcp_monitoring_alert`；`spark_ug_rch_send_record*` |
| 默认 owner | `airflow`（多数）；`huang.jw`（metadata/监控）；`data-team`（daily_report） |
| 主日批 cron | `0 18 * * *` |
| 小时批 cron | `10 * * * *` |
| 其他 | `0 2 * * *`（daily_report）；`20 16 * * 5`（data_options）；`*/1 * * * *`（gcp_monitoring_alert）；`*/2 0-12 * * *`（task_kill）；`@daily`（sync_source_meta） |

#### 4.b 数据仓库坐标（BigQuery）

| 项 | 值 |
|---|---|
| GCP Project（默认/FQN 主项目） | `oppo-gcp-prod-digfood-129869` |
| Location | `asia-southeast2` |
| Airflow gcp_conn_id | `google_cloud_default` |
| Variable | `qpon_gcp_project_id`、`qpon_gcp_location` |

高频 dataset（FQN 计数 Top）：`qpon_dwd_d`、`qpon_ods_d`、`qpon_rpt_d`、`qpon_dim_d`、`qpon_dws_d`、`digital_food_order`、`qpon_tmp`、`qpon_analyst_d`、`digital_food_market`、`pubsub_to_bq_qpon_events_collection`、`qpon_sync_from_feishu`、`qpon_data_server` 等。  
源业务库名在 ODS task 路径中可见：`digital_food_order`、`digital_food_market`、`digital_food_settle`、`digital_pay_order`、`market_db_user_growing`、`qpon_crm`、`qpon_operation`、`qpon_review` 等。

分库分表：N/A（无 ShardingSphere）；等价为 **BQ dataset 分层 + Datastream 多 MySQL 源（`datastream-*` Connection）**。

#### 4.c Redis

N/A：本项目 `dags/` 内无 Redis 连接配置或 import。

#### 4.d 消息队列

| 项 | 值 |
|---|---|
| RocketMQ | N/A：无 |
| Pub/Sub | `gcp_monitoring_alert` 使用 `PubSubPullSensor`；事件表 dataset `pubsub_to_bq_qpon_events_collection` |
| 告警 Webhook | `https://mtp.myoas.com/gateway/robot/webhook/send`（token=`[REDACTED]`） |
| Variable | `etl_alter_webhook_url`、`gcp_alter_webhook_url` |

#### 4.e RPC（Dubbo 等价）

N/A：无 Dubbo。等价 HTTP：飞书 OpenAPI、Adjust API、Cloud Run ES 服务（`write_es_service_url`）。

#### 4.f 其他中间件

| Variable Key | 用途 |
|---|---|
| `write_es_service_url` | Cloud Run ES 写入服务基址 |
| `es_hosts` / `es_user_name` / `es_password` / `es_api_key` | ES 连接（password/api_key=`[REDACTED]`） |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书应用凭证（代码中另有硬编码副本） |
| `composer_gcs_bucket` | Composer GCS bucket |
| `project_home` | 项目家目录（fallback `AIRFLOW_HOME`） |
| `dbt_profile_name` / `dbt_profile_target` | dbt profile 坐标（默认 `qpon`/`dev`） |
| `owner_job_no_dict` | owner→工号映射（JSON） |

---

### 5. 子模块物理职责定义

| 包 | .py 数 | 一句话职责 |
|---|---:|---|
| `airflow_config` | 11 | Composer 共享运行时：BQ/Python 任务工厂、跨 DAG Sensor/Marker、TT 告警、飞书→BQ、ES 写/删 |
| `qpon_metadata` | 20 | Datastream/MySQL 源表元数据同步、BQ staging 描述同步、GCP Monitoring→TT 告警 |
| `qpon_ods_d` | 168 | 日批 ODS：业务库/飞书/Adjust 等到 BQ 贴源层 |
| `qpon_ods_h` | 46 | 小时批 ODS |
| `qpon_ods_d_test` | 17 | ODS 日批测试镜像 |
| `qpon_dim_d` / `qpon_dim_h` | 33 / 3 | 维度层日/小时构建 |
| `qpon_dwd_d` / `qpon_dwd_h` / `qpon_dwd_d_test` | 110 / 26 / 7 | 明细事实层（含部分写 ES） |
| `qpon_dws_d` / `qpon_dws_h` | 27 / 4 | 汇总中间层 |
| `qpon_rpt_d` / `qpon_rpt_h` | 286 / 18 | 报表/看板层（体量最大；含 ES 榜单回写） |
| `qpon_tag_d` / `qpon_tag_d_test` | 144 / 41 | 用户/门店/券等标签生产 |
| `qpon_analyst_d` / `qpon_analyst_h` | 41 / 4 | 分析师 ADS 指标 |
| `qpon_analyst_alarm_d` / `_h` | 3 / 2 | 分析指标告警 |
| `qpon_data_server_d` / `_test` | 17 / 10 | 对数据服务/ES 的投递任务 |
| `qpon_email_date_d` / `_test` | 22 / 22 | 邮件/日期相关数据集市 |
| `qpon_risk_d` | 52 | 风控用户/商户特征与规则汇总 |
| `qpon_daily_report` | 9 | 业务日报计算 + GenAI 叙事推送 |
| `data_options` | 5 | 周批运维：staging 清理、事件导出 GCS、写 ES |
| `task_kill` | 2 | 高频监控并终止异常 BQ Job |
| `Qpon_Adjust_Raw_Data` | 2 | Adjust 原始外部表创建/维护 |
| `qpon_staging_d` | 4 | Dataproc/Spark：MySQL→BQ 与 UG 触达记录 |
| `qpon_search_d` | 1 | 搜索门店特征导出（GCS） |
| `qpon_review_score_test` | 6 | 评价分测试链路 |
| `qpon_test_d` | 3 | 临时/试验 DAG |

---

### 6. 构建与部署坐标

| 项 | 状态 / 值 |
|---|---|
| `pom.xml` / 父 POM / JDK | N/A：非 Maven/Java 项目 |
| `columbus_build.sh` | N/A：不存在 |
| `requirements.txt` / `pyproject.toml` / `setup.py` | N/A：工作区根与 `dags/` 均未发现 |
| 包管理器 | 隐式依赖 Composer 环境；代码侧使用 airflow providers、google-cloud-*、pandas、pydantic、elasticsearch、pyspark、requests |
| 构建命令 | N/A：无本地构建脚本；部署形态为 **将 `dags/` 同步至 Composer DAG 目录** |
| 打包方式 | 源码目录部署（非 jar/war） |
| 项目版本号 | N/A：无统一 version 文件 |
| 运行时锚点 | BQ location `asia-southeast2`；默认 project `oppo-gcp-prod-digfood-129869`；任务工厂见 `dags/airflow_config/create_composer_bq_task.py` |

---

### 7. 旧文档交叉验证摘要

NO_DOCS：`Legacy_qpon-bigdata_Claims.md` 声明 LEGACY_COUNT=0，本节跳过声称级交叉验证。

🆕新发现（相对「空旧文档」的代码事实）：
- 真实骨架为 33 包 Airflow DAG 仓，而非 Java 6 模块
- 主技术栈 = Composer + BigQuery（asia-southeast2）+ ExternalTaskSensor 层间编排
- 旁路：Dataproc/Spark、Aliyun ES via Cloud Run、飞书、Adjust、TT、GenAI 日报

---

> [!SUCCESS] 骨架测绘闭环验证
> - 扫描范围：父 POM(N/A) + 0 个子模块 POM + 33 个 DAG 包（1167 `.py`）+ 共享库 `airflow_config`(11) / `qpon_metadata` + Variable/Connection 配置坐标 + 构建脚本(N/A)
> - 提取结果：识别了 18 项中间件/第三方依赖，22 项配置坐标（Variable/Project/Location/Conn/Webhook/ES/Feishu）
> - 架构预警：捕获了 9 项潜在问题（Red Flags）
> - 旧文档验证：0 项已验证 / 0 项不符 / 0 项部分符合 / 0 项无法验证（NO_DOCS）
> - EOF 状态：已确认遍历至最后一行,无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: NON_JAVA Airflow/Composer 仓；权威代码在 `dags/`；共享契约入口为 `airflow_config.create_composer_bq_task` / `create_external_sensor` / `airflow_tt_send`；主数据面为 BigQuery project `oppo-gcp-prod-digfood-129869` @ `asia-southeast2`；跨 DAG 边由 `ExternalTaskSensor` 表达（ods→dim/dwd→dws→rpt）；旁路含 Dataproc/Spark（`qpon_staging_d`）、ES 回写（`cloud_run_write_aliyun_es`）、飞书（`read_feishu_to_bg`）、Pub/Sub 监控告警、GenAI 日报。
> - **推演约束 (Constraint)**: Step 02 契约提取必须扫描：① 全部 `dags/*/qpon_*.py` 与 `data_options.py`/`task_kill.py`/`Qpon_Adjust_Raw_Data.py` 的 `create_composer_bq_task`/`create_composer_python_task` 调用清单；② `create_external_sensor(dag, upstream_dag, task)` 全量边表；③ `airflow_config/*.py` 对外函数签名；④ task 模块导出名约定（函数名=模块名）；禁止从 `scripts/` 或 `ai-knowledge-knowledge/` 取业务契约。
> - **物理锚点 (Anchors)**: `dags/airflow_config/create_composer_bq_task.py`；`dags/airflow_config/create_external_sensor.py`；`dags/airflow_config/cloud_run_write_aliyun_es.py`；`dags/airflow_config/read_feishu_to_bg.py`；`dags/qpon_metadata/utils/variables.py`；`dags/qpon_ods_d/qpon_ods_d.py`；`dags/qpon_dwd_d/qpon_dwd_d.py`；`dags/qpon_rpt_d/qpon_rpt_d.py`；`dags/qpon_staging_d/spark_mysql_to_bigquery.py`
> - **技术栈清单 (Stack)**: Airflow/Composer；google-cloud-bigquery/storage/dataproc/pubsub/secretmanager；PySpark；elasticsearch；pandas；requests；pydantic；google.genai；飞书 OpenAPI；Adjust API；TeamTalk webhook；MySQL（Datastream/JDBC）；dbt profile 坐标（Variable，作业路径 `dags/dbt/{target}` 待后续确认是否存在）
> - **目录职责 (Dirs)**: 见 §1.1 / §5；聚焦 `dags/` 分层包 + `airflow_config` 共享库
> - **后续扫描路径建议**: 契约→`airflow_config`+各 DAG 入口；数据模型→各 `tasks/**/*.py` 内 BQ FQN/SQL；异步→`ExternalTaskSensor`/`PubSubPullSensor`/`TimeSensor`；风控旁路→`qpon_risk_d`；服务投递→`qpon_data_server_d`+ES helpers
