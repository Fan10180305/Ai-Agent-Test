# 07_Config_and_Observability — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）；禁止 `scripts/`  
> 语义映射：`*-start/resources` / `@Value` / JetCache / ErrorCode / `@Configuration` → **Airflow Variable/Connection、DAG `default_args`、Sensor 工厂参数、Composer 运行时常量、TT/飞书 webhook、`logging`/`print` 埋点**  
> BQ 锚点：`oppo-gcp-prod-digfood-129869` @ `asia-southeast2`  
> Legacy：NO_DOCS  
> 物理拦截：grep `Variable.get` / `Connection` / `default_args` / `max_active_runs` / `is_paused` / `pool` / `yzjtoken` / `write_es_service_url` / `es_*` / `logging.` / `print(`；关键文件读至 EOF；禁止虚构 Composer 控制台未入库的配置值

> [!SUCCESS] 配置与可观测性测绘闭环验证
> - 扫描范围：`dags/` Variable/Connection/DAG default_args + `airflow_config/` 共享运行时 + `qpon_metadata/utils` + 告警/ES/PubSub 入口（无 Java resources）
> - 提取结果：[28+] 个业务影响配置项、[0] 个缓存点（无 Redis/JetCache）、[0] 个错误码枚举（用 AirflowException 族）、[10] 个共享配置/工厂模块（`airflow_config`）+ [1] Variable 集中模块
> - 缓存覆盖：[0] 个业务场景使用缓存
> - 衍生约束：[12] 条（🔴 [7] 条强制 / 🟡 [5] 条建议）
> - 旧文档差异：N/A（NO_DOCS）
> - EOF 状态：已确认关键实现文件遍历至最后一行，无静默截断

---

### 1. 配置项决策清单

N/A：无 `application*.yml` / `heracles.properties`。配置权威 = **Airflow Variable + Connection + DAG/工厂字面量**。敏感值一律 `[REDACTED]`。

#### 1.A 业务开关 / 特性标志（含等价物）

| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
|---|---|---|---|
| `is_paused_upon_creation`（DAG 字面量） | `True`（仅 3 个 metadata DAG） | 新建/同步后默认暂停 | 业务 DAG **未设**（跟随 Composer 默认，通常 False） |
| `catchup` | 全仓业务 DAG 普遍 `False` | 禁止历史回补风暴 | 一致 |
| `depends_on_past` | 普遍 `False` | 无跨 run 串行锁 | 一致 |
| `dbt_profile_target` | default `"dev"` | dbt profile 目标名（路径 `dags/dbt/{target}`） | Variable 可改；作业是否存在待仓外确认 |
| `MONTHLY_TARGETS` / `DEFAULT_TARGET`（`qpon_daily_report/config.py`） | 按月硬编码 GTV/Revenue | 日报目标对照 | 代码发版变更，非 Variable |

#### 1.B 超时与容错（Sensor / HTTP / DAG retries）

| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
|---|---|---|---|
| `create_external_sensor.timeout` | **64800** s（18h） | 日批跨 DAG Sensor 单次 poke 超时 | 调用方可覆盖，仓内普遍用默认 |
| `create_external_sensor.poke_interval` | **600** s | 日批 poke 间隔 | 同上 |
| `create_external_sensor.retries` | **1000**（覆盖 DAG retries） | 日批 Sensor 任务级重试 | 硬编码工厂，非 Variable |
| `create_external_sensor.mode` | `reschedule` | 释放 worker slot，占调度队列 | 硬编码 |
| `create_external_sensor.priority_weight` | **100** | 调度优先级 | 可传参 |
| `create_external_sensor_hour.timeout/poke/retries` | 7200 / 300 / **20** | 小时 ExternalTaskSensor 工厂 | **仓内无活调用** |
| `create_external_task_skip_sensor_hour.*` | 7200 / 300 / **20** | 小时 SkipSensor | 活调用 ≈34 |
| `qpon_daily_report` 直连 Sensor | timeout=28800；poke=600；retries=100；`execution_delta=+8h` | 对齐 `0 18` vs `0 2` | 代码常量 |
| Cloud Run ES `GET /health` timeout | **10** s（字面量） | ES 写前探活 | **不可经 Variable 调整** |
| Cloud Run ES `POST /api/write-to-es` timeout | **30** s（字面量） | ES 写入 HTTP | **不可经 Variable 调整** |
| `ElasticsearchWriteOperator.timeout` | 默认 30 s | 直连 ES（仅 `__main__` 自测路径） | DAG 活调用=0 |
| `Check_BQ_Data_IsExists_Operator` | retries=24；delay=1h | BQ 数据存在性检查 | 工厂硬编码 |
| DAG `default_args.retries` | 多数 **3**；daily_report **2**；metadata/monitoring/task_kill/data_options/search **0**；spark ephemeral **1** | 任务失败重试 | 按 DAG 入口 |
| DAG `default_args.retry_delay` | 多数 **10 min**；daily_report **5 min** | 重试间隔 | TimeDelta 任务另有 2/30/60 min |

#### 1.C Sensor / Slot / DAG Concurrency（Step06 接力 #1）

| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
|---|---|---|---|
| `max_active_runs` | 仅 metadata 三 DAG = **1**；其余业务 DAG **未声明** | 同 DAG 并发 run 上限 | 业务层依赖 Composer 全局默认（仓内不可见） |
| `max_active_tasks` / `concurrency` / `parallelism` / `pool=` | **仓内 0 处** | slot/池配额 | **无代码级 pool/slot 配置**；容量在 Composer 环境，本仓无法审计具体数值 |
| Sensor `mode=reschedule` + `retries=1000` | 工厂默认 | 上游失败/未就绪时长期 `up_for_retry`/`up_for_reschedule` | 高风险占调度容量（见 §5 / §8） |

**结论（代码事实）**：与 Sensor timeout/slot/concurrency 相关的**可审计配置全部在工厂字面量与少数 DAG 参数**；Composer worker slot / `parallelism` **未**出现在 `dags/`，禁止臆造数值。

#### 1.D MQ / Pub/Sub / 告警路由

| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
|---|---|---|---|
| Pub/Sub `subscription` | `qpon-data-gcp-component-monitoring-sub` | GCP Monitoring Incident 入站 | `gcp_monitoring_alert.py` 硬编码 |
| `PubSubPullSensor.max_messages` | 1 | 每次拉 1 条 | 硬编码 |
| `PubSubPullSensor.poke_interval` | 10 | 拉消息间隔 | 硬编码 |
| `PubSubPullSensor.ack_messages` | True | 拉取即 ack | 硬编码 |
| `gcp_conn_id` | `google_cloud_default` | GCP 连接 | 多处共用 |
| `etl_alter_webhook_url` | Variable，default `""` | 设计给 ETL TT 告警 | **仅定义，无活引用** |
| `gcp_alter_webhook_url` | Variable，default `""` | `gcp_monitoring_alert` → `TeamtalkRobot` | Variable 空则发送空 URL（可达性依赖部署时注入） |
| DAG 硬编码 `send_url` + `yzjtoken` | Host `mtp.myoas.com`；token=`[REDACTED]`（见 §7） | 多数业务 DAG `on_failure_callback` | **不走 Variable** |

#### 1.E ES / Cloud Run（Step06 接力 #3）

| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
|---|---|---|---|
| `write_es_service_url` | Variable（无 default） | Cloud Run ES 服务基址 | 未设则任务启动即失败 |
| `es_hosts` | Variable | ES 主机列表（传给 Cloud Run 或直连） | 敏感/环境相关 |
| `es_user_name` | Variable | ES 用户 | `[REDACTED]` |
| `es_password` | Variable | ES 密码 | `[REDACTED]`；写函数 `print` 会打出明文（可观测性泄漏） |
| `es_api_key` | Variable | ES API Key | `[REDACTED]`；同样被 print |
| 硬编码 ES（`elasticsearch_write_operator.__main__`） | `http://10.3.13.241:19527` + user/password | 本地自测路径 | **非生产 DAG 路径**；密码 `[REDACTED]` |

**超时是否可配**：**否**。health=10 / write=30 写死在 `cloud_run_write_aliyun_es.py`，无对应 Variable。

#### 1.F 中间件连接（合并统计）

| 类别 | 合并结论 |
|---|---|
| BigQuery / GCP | 连接：`google_cloud_default`；Project Variable `qpon_gcp_project_id` default=`oppo-gcp-prod-digfood-129869`；Location Variable `qpon_gcp_location` default=`asia-southeast2`；BQ Operator location 另硬编码 `asia-southeast2` |
| MySQL / Datastream | Connection 前缀 `datastream-*`（`sync_source_meta.get_etl_connections` 动态枚举）；凭据在 Airflow Connection，仓内无明文 |
| Redis | N/A：`dags/` 无 Redis 连接/客户端（仅注释掉的 `store_score_redis_detail_test`） |
| Dubbo | N/A：无 |
| 日志框架 | Python `logging` + 大量 `print`；无 logback/xml；Composer 侧 Airflow task log |
| Secret Manager | `spark_mysql_to_bigquery.py` 拉取 MySQL 密码（secret 名在脚本内，值 `[REDACTED]`） |
| 飞书 App | `FEISHU_APP_ID` / `FEISHU_APP_SECRET` Variable 读取被注释；硬编码明文于 `read_feishu_to_bg.py`（值 `[REDACTED]`） |
| 日报旁路 | Variable `feishu_daily_report_webhook`、`daily_report_gemini_api_key` |
| Composer 路径 | `composer_gcs_bucket`、`project_home`（fallback `AIRFLOW_HOME`） |
| owner 映射 | `owner_job_no_dict` JSON Variable（供 `TeamtalkRobot` @工号；主路径业务 callback **未用**） |

---

### 2. 缓存策略全景

N/A：无 JetCache / RedisTemplate / `@Cached`。`dags/` 内唯一 “redis” 命中为注释任务名，非缓存实现。

| 缓存名/Key 模式 | 方式 | TTL | 更新策略 | 使用场景 |
|---|---|---|---|---|
| （无） | N/A | N/A | N/A | N/A |

等价「状态缓存」：Airflow 元库 TaskInstance 状态（Sensor 消费）；XCom（daily_report 等）；**非**业务 TTL 缓存。

旧文档缓存待确认项：NO_DOCS → 跳过。

---

### 3. 错误码字典

N/A：无 `ErrorCode` / `ResultCode` / `BizCode` 枚举体系。

**[Airflow 异常族] 错误码**（共 0 个码值；用异常类型表达语义）

| 错误码值 | 常量名/类型 | 使用场景（一句话） |
|---|---|---|
| N/A | `AirflowException` | SkipSensor 上游 FAILED；ES 任务伪分支「可重试」 |
| N/A | `AirflowFailException` | ES 任务伪分支「关键错误不重试」（见下） |
| N/A | `AirflowSkipException` | SkipSensor 上游 SKIPPED |
| N/A | `Exception` / `ConnectionError` / `ValueError` | Cloud Run ES / 飞书 / 日报 Variable 缺失等 |

**伪错误码分支（死逻辑）**：多个 `*_to_es.py` 判断 `result == "error"` / `"retry_error"` 再抛 `AirflowFailException` / `AirflowException`，但 `access_cloud_run_write_aliyun_es` **只返回 `"success"` 或 raise** → 分支不可达。⚠️疑似废弃模板。

共 **0** 个业务错误码，分布在 **0** 个 ErrorCode 类/枚举中；异常类型分散在 Sensor 工厂、ES 写、metadata、daily_report。

---

### 4. 异常处理体系

#### 4.a 自定义异常类清单

| 类名 | 继承链 | 使用场景 |
|---|---|---|
| （无项目自定义 Exception 类） | N/A | 直接使用 Airflow / 标准库异常 |

#### 4.b 全局异常处理器

N/A：无 `@ControllerAdvice` / `@ExceptionHandler`。等价物：

| 机制 | 行为 |
|---|---|
| `on_failure_callback` / `send_failure_alert_factory` | 任务失败后发 TT；**不**改变失败状态 |
| `create_common_teamtalk_alter_callback` | 含 exception 正文 + owner 工号；**仓内无活调用** |
| DAG `email_on_failure` / `email_on_retry` | 普遍 `False` |

#### 4.c Dubbo 异常过滤器

N/A：无 Dubbo。

#### 4.d 异常处理模式

| 模式 | 证据 |
|---|---|
| 统一包装 | 无；各 Python 任务自行 `raise` / `print` |
| 吞异常 | `TtSend.sendTT`：`except Exception: print(e)`；`gcp_monitoring_alert.monitoring_alert`：解析失败 `logger.warning` + `continue`（消息已 ack） |
| 再抛 | ES 写任务 `except: print; raise`；Cloud Run 写失败一律 raise |
| 静默失败风险 | 告警通道失败不抬升任务失败；Pub/Sub 解析失败丢消息 |

---

### 5. 日志规范分析

#### 5.a 日志框架

- 标准库 `logging.getLogger` / Operator `self.log`
- **无** Logback/Log4j2 / PatternLayout 配置文件
- 主观测通道实际是 **Composer Task Log + `print` stdout**

#### 5.b 格式模式

- 无统一 Pattern；字符串拼接与 f-string 混用
- TT 正文模板：`{execution_date} 的 dag_id=...,task_id=... 任务执行失败!`（**不含** `exception`，尽管已读取）

#### 5.c MDC / TraceID

N/A：无 MDC / `trace_id` 注入。关联维度依赖 Airflow `dag_id` / `task_id` / `run_id` / `execution_date`。

#### 5.d 关键日志点采样（error/warn 与告警可达性）

| # | 场景 | 锚点 | 级别/方式 |
|---|---|---|---|
| 1 | TT 发送非 200 | `airflow_tt_send.stream_upload` | **print**（非 log.error） |
| 2 | TT 发送异常吞掉 | `TtSend.sendTT` | **print(e)** |
| 3 | metadata TT 告警失败 | `teamtalk.TeamtalkRobot._send` | `logger.error` |
| 4 | SkipSensor 上游失败 | `ExternalTaskSkipSensor.poke` | `self.log.error` + raise |
| 5 | SkipSensor 上游 UP_FOR_RETRY | 同文件 L116–118 | `self.log.info`（**无风暴计数**） |
| 6 | Pub/Sub 解析失败 | `gcp_monitoring_alert` | `logger.warning` + continue |
| 7 | ES 连接失败 | `elasticsearch_write_operator` | `self.log.error` |
| 8 | Cloud Run ES 超时/失败 | `cloud_run_write_aliyun_es` | **print** + raise |
| 9 | ES 凭据打印 | 同文件 L48/56 | **print 含 password/api_key** |
| 10 | 元数据 BQ 插入失败 | `sync_source_meta` | `logger.error` |

#### 5.e 日志级别分布（`dags/**/*.py` 字面调用计数）

| 级别/方式 | 约计次数 | 说明 |
|---|---:|---|
| `print(` | **319** | 主导「日志」形态 |
| `.info(` | **91** | 集中于 metadata / daily_report / SkipSensor / spark |
| `.warning(` | **19** | |
| `.error(` | **12** | |
| `.debug(` | **0** | |

#### 5.f Sensor up_for_retry 风暴与 callback 失败覆盖（Step06 接力 #5）

| 观测需求 | 代码事实 |
|---|---|
| Sensor `up_for_retry` 风暴指标 | **无** StatsD/Prometheus/自定义 counter；日批 Sensor 依赖 Airflow UI 状态；SkipSensor 将上游 `UP_FOR_RETRY` 记为 info「正在运行中」并继续等 |
| callback 发送失败 | `TtSend`：**print 吞异常**，无 log.error、无二次通道、无指标；`TeamtalkRobot`：有 `logger.error`，但主业务路径用的是 `TtSend` |
| 结论 | **未覆盖**：无法从应用埋点证明「重试风暴」或「告警未送达」；只能靠 Composer 平台日志/UI 事后排查 |

---

### 6. Spring 配置类清单

N/A：无 `@Configuration` / Spring Bean。等价「配置/工厂模块」：

| 模块路径 | 注册的「Bean」等价 | 中间件/组件 | 条件注解等价 |
|---|---|---|---|
| `dags/qpon_metadata/utils/variables.py` | 模块级常量（Variable 热读） | GCS/BQ/dbt/webhook/owner | default_var |
| `dags/airflow_config/create_composer_bq_task.py` | BQ / Python Operator 工厂 | BigQueryInsertJobOperator / PythonOperator | 无 |
| `dags/airflow_config/create_external_sensor.py` | Sensor / SkipSensor 工厂 | ExternalTaskSensor 族 | 无 |
| `dags/airflow_config/create_external_marker.py` | ExternalTaskMarker 工厂 | Marker | 无 |
| `dags/airflow_config/create_check_table_data.py` | BigQueryCheckOperator 工厂 | BQ Check | retries=24 |
| `dags/airflow_config/airflow_tt_send.py` | `TtSend` / failure callback 工厂 | TT webhook | 无 |
| `dags/airflow_config/cloud_run_write_aliyun_es.py` | `access_cloud_run_write_aliyun_es` | Cloud Run + ES Variables | 无 |
| `dags/airflow_config/cloud_run_delete_aliyun_es.py` | `delete_by_field_condition` | ES 直删 | 无 |
| `dags/airflow_config/elasticsearch_write_operator.py` | `ElasticsearchWriteOperator` | ES 直写 | **DAG 活调用=0** |
| `dags/airflow_config/read_feishu_to_bg.py` | `ReadFeiShuToBigQuery` | 飞书 OpenAPI | 硬编码凭据 |
| `dags/qpon_metadata/utils/teamtalk.py` | `TeamtalkRobot` / common callback | TT Variable webhook | **common callback 无活调用** |
| `dags/qpon_metadata/utils/meta_mixin.py` | `MysqlMetaMixin` | MySQL Connection Hook | conn_type=`mysql` |
| `dags/qpon_daily_report/config.py` | 业务常量 + Variable 名 | BQ 表 / LLM / 飞书 | 无 |

---

### 7. 业务开关与特性标志

#### 7.a 功能开关

| 开关 | 形态 | 事实 |
|---|---|---|
| DAG 暂停创建 `is_paused_upon_creation=True` | **仅** `gcp_monitoring_alert` / `sync_source_meta` / `sync_bigquery_staging_description` |
| 小时门控 | `ShortCircuitOperator` + 允许小时列表（`qpon_dwd_h`） | 编排开关，非 Variable |
| 邮件告警 | `email_on_failure=False` | 全仓关闭邮件通道 |

#### 7.b 灰度 / 降级

- 无 `feature.xxx.enabled` Variable。
- 测试包 `*_test` 与生产同仓同 cron，靠包隔离而非开关。
- ES 写失败无降级开关；依赖 DAG retries。

#### 7.c TT webhook Token 与可达性（Step06 接力 #2）

| 通道 | Token/URL 来源 | 出现次数 | 可达性风险 |
|---|---|---:|---|
| 业务 DAG `send_url` | 硬编码 `yzjtoken=a1c0a692...` | **多数 DAG（约 32 文件）** | Token 散落源码；吊销需改代码发版；`TtSend` 失败静默 |
| `qpon_analyst_alarm_d` / task | 硬编码 `f025661e...` | 入口+task | 独立机器人 |
| `qpon_analyst_alarm_h` task | 硬编码 `448a3f50...` | 1 | 又一个独立 token |
| `gcp_alter_webhook_url` | Variable | 1 消费点 | Variable 空/`""` 时请求无效；依赖部署注入 |
| `etl_alter_webhook_url` | Variable | **0 消费点** | 配置存在但**不可达业务 callback** |
| `create_common_teamtalk_alter_callback` | 入参 webhook | **0 调用** | 更好实现未被接线 |

**全仓 `yzjtoken=` 字面命中：35**；不重复 token 前缀 **3** 个（正文均 `[REDACTED]`）。

#### 7.d Pub/Sub + `is_paused_upon_creation`（Step06 接力 #4）

| 项 | 事实 |
|---|---|
| DAG | `gcp_monitoring_alert`，`schedule=*/1 * * * *`，`retries=0`，`max_active_runs=1` |
| `is_paused_upon_creation=True` | **是**：DAG 首次出现在 Composer 时默认 **paused** |
| 监控静默条件 | 若运维未手动 Unpause，则 Pub/Sub 消费与 TT 转发**整链不跑** → GCP 组件告警对 TT **静默** |
| 同标志其它 DAG | `sync_source_meta`、`sync_bigquery_staging_description`（元数据同步同样默认暂停） |
| subscription | `qpon-data-gcp-component-monitoring-sub`（硬编码）；消息 ack 后解析失败不重投 |

---

### 8. 衍生约束清单

| 约束编号 | 约束内容 | 来源事实 | 严重级别 |
|---|---|---|---|
| G-07-01 | 禁止在无容量评估的情况下继续提高日批 Sensor `retries`（当前 1000）或降低 `poke_interval`；变更须评估 Composer slot/`up_for_reschedule` 队列 | §1.B / §1.C | 🔴强制 |
| G-07-02 | 业务 DAG 告警 URL 必须改为 Variable（或统一引用 `etl_alter_webhook_url`）；禁止新增硬编码 `yzjtoken` | §1.D / §7.c | 🔴强制 |
| G-07-03 | `TtSend.sendTT` / `stream_upload` 失败必须 `logger.error`（或改接 `TeamtalkRobot`）；禁止仅 `print` 吞掉导致「无告警=无失败」误判 | §4.d / §5.f | 🔴强制 |
| G-07-04 | Cloud Run ES 的 HTTP timeout 若需按环境调整，必须提升为 Variable（或参数），禁止继续只改字面量却声称「可配」 | §1.E | 🔴强制 |
| G-07-05 | `gcp_monitoring_alert` 部署后必须有 Unpause 检查清单；或将 `is_paused_upon_creation` 改为 `False` 并文档化风险 | §7.d | 🔴强制 |
| G-07-06 | 禁止在生产路径 `print` ES `password` / `api_key`（`cloud_run_write_aliyun_es` L48/56） | §1.E / §5.d | 🔴强制 |
| G-07-07 | 飞书凭证必须改回 `Variable.get`；禁止恢复/新增硬编码 `FEISHU_APP_SECRET` | §1.F / `read_feishu_to_bg.py` | 🔴强制 |
| G-07-08 | `etl_alter_webhook_url` 与 `create_common_teamtalk_alter_callback` 要么接线到业务 DAG，要么删除死配置，避免「Variable 已配但未生效」 | §7.c | 🟡建议 |
| G-07-09 | 新增跨 DAG Sensor 必须显式传入 `timeout`/`poke_interval`/`on_failure_callback`，并在 PR 说明 concurrency 影响；禁止依赖隐式工厂默认而不自知 | §1.B | 🟡建议 |
| G-07-10 | 需要观测 Sensor 重试风暴时，应接入 Composer/Airflow 指标或自定义计数；禁止仅依赖 SkipSensor info 日志 | §5.f | 🟡建议 |
| G-07-11 | ES 任务删除不可达的 `result=="error"` 分支或让写函数返回约定码，避免伪错误码误导排障 | §3 | 🟡建议 |
| G-07-12 | 业务 DAG 若需限制并发，应显式设置 `max_active_runs`/`pool`；当前仅 metadata 三 DAG 有 `max_active_runs=1` | §1.C | 🟡建议 |

---

### 9. 旧文档交叉验证摘要

NO_DOCS：`Legacy_qpon-bigdata_Claims.md` LEGACY_COUNT=0，本节跳过声称级交叉验证。

🆕新发现（相对空旧文档）：
- 配置中心等价物为 Variable/Connection + 工厂字面量，非 Spring resources
- 告警主路径硬编码 TT token；Variable webhook 几乎只服务 Pub/Sub 监控 DAG
- Cloud Run ES 超时不可配；ES 凭据会被 print
- `is_paused_upon_creation=True` 可使监控 DAG 默认静默
- 无可观测埋点覆盖 Sensor 重试风暴与 TT callback 发送失败

---

## 附录 A：Step06 接力五项审计回执

| # | 审计项 | 结论（代码事实） |
|---|---|---|
| 1 | Sensor timeout / slot / DAG concurrency | timeout/poke/retries/priority 在工厂；`pool`/`parallelism`/`max_active_tasks`=0；`max_active_runs=1` 仅 3 个 metadata DAG；slot 压力来自 `reschedule`+高 retries |
| 2 | TT webhook Variable / 硬编码 token | 业务主路径硬编码 3 类 token（35 处）；`gcp_alter_webhook_url` 仅监控 DAG；`etl_alter_webhook_url` 无消费者；`TtSend` 失败静默 |
| 3 | `write_es_service_url` / `es_*` 与 Cloud Run 超时 | Variable 控制 URL/凭据；timeout **10/30 硬编码不可配** |
| 4 | Pub/Sub subscription + `is_paused_upon_creation` | sub=`qpon-data-gcp-component-monitoring-sub`；`is_paused_upon_creation=True` → **可导致监控静默**直至 Unpause |
| 5 | 日志/指标覆盖 Sensor 风暴与 callback 失败 | **未覆盖**：无 metrics；SkipSensor 对 UP_FOR_RETRY 仅 info；TT callback 失败靠 print |

## 附录 B：物理锚点

| 锚点 | 路径 |
|---|---|
| Variable 集中定义 | `dags/qpon_metadata/utils/variables.py` L6–24 |
| Sensor 工厂 | `dags/airflow_config/create_external_sensor.py` L10–136 |
| TT callback | `dags/airflow_config/airflow_tt_send.py` L8–76 |
| TeamtalkRobot | `dags/qpon_metadata/utils/teamtalk.py` L14–83 |
| Cloud Run ES | `dags/airflow_config/cloud_run_write_aliyun_es.py` L5–100 |
| ES 删除 | `dags/airflow_config/cloud_run_delete_aliyun_es.py` L22–138 |
| Pub/Sub 监控 DAG | `dags/qpon_metadata/gcp_monitoring_alert.py` L42–69 |
| paused metadata | `sync_source_meta.py` L145–158；`sync_bigquery_staging_description.py` L221–234 |
| 飞书硬编码 | `dags/airflow_config/read_feishu_to_bg.py` L15–19 |
| 日报 Variable 名 | `dags/qpon_daily_report/config.py` L30–31 |
| 典型业务 default_args | `dags/qpon_ods_d/qpon_ods_d.py` L90–108 |

---

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 配置面=Variable(`write_es_service_url`/`es_*`/`gcp_alter_webhook_url`/GCP project·location 等)+DAG 字面量；无 Redis 缓存与 ErrorCode 字典；日批 Sensor retries=1000/timeout=64800/mode=reschedule 且无 pool 配置；业务 TT token 硬编码且发送失败可静默；Cloud Run ES 超时 10/30 不可配；`gcp_monitoring_alert` 默认 paused 可致 Pub/Sub→TT 静默；日志以 print 为主，无 up_for_retry/callback 失败指标。
> - **推演约束 (Constraint)**: Step 08 深潜须优先打开 (1) Composer 环境实际 parallelism/slot 与 Sensor 队列是否打满；(2) 生产是否已 Unpause `gcp_monitoring_alert` 且 `gcp_alter_webhook_url` 非空；(3) 业务 DAG 硬编码 token 与 Variable webhook 是否双轨并行；(4) ES 写任务日志是否已泄漏凭据到 task log；(5) 若做配置治理，先接线 `etl_alter_webhook_url`+`TeamtalkRobot` 再删硬编码。
> - **物理锚点 (Anchors)**: `dags/qpon_metadata/utils/variables.py` L16-17；`dags/airflow_config/create_external_sensor.py` L10-24；`dags/airflow_config/airflow_tt_send.py` L42-66；`dags/airflow_config/cloud_run_write_aliyun_es.py` L8-66；`dags/qpon_metadata/gcp_monitoring_alert.py` L42-65；`dags/airflow_config/read_feishu_to_bg.py` L15-19。
