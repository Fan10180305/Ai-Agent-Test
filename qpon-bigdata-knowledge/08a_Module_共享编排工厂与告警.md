# 08a 模块深潜：共享编排工厂与告警（airflow-config）

> 模块 id=`airflow-config`；权威范围=`dags/`（重点 `dags/airflow_config/`）  
> 不重复 Step05 调用链全量追踪；本步钻取决策点 / 失败模式 / 扩展点  
> Step07 接力优先：Sensor 无 pool+retries=1000、TT 硬编码与 Variable 双轨、ES 超时不可配/凭据泄漏、`gcp_monitoring_alert` paused 静默

> [!SUCCESS] 共享编排工厂与告警 模块深潜闭环验证
> - 扫描范围：10 个 `airflow_config` 核心模块 + 5 个代表消费入口（ods/dwd/rpt/daily_report/dws_h）+ 关联 `gcp_monitoring_alert`
> - 提取结果：8 个入口方法、8 条衍生约束、4 个业务特性章节
> - 全文行数：195 行（≤ 400 行）
> - 前序验证：Step 02 契约面=工厂签名 / Step 03 下游=BQ·Sensor·ES·TT·飞书 / Step 04 实体=ES index+飞书落地（工厂不持表知识）
> - EOF 状态：`airflow_config/` 10 文件已读至 EOF；无静默截断

---

## A. 模块定位

`airflow_config` 是仓内**跨 DAG 共享的编排工厂与横切告警/ES/飞书适配层**：标准化 BQ/Python 任务构造、跨 DAG Sensor/Marker、TT `on_failure_callback`、Cloud Run ES 写删；本身不承载分层业务 SQL，也不反向 import 业务 `tasks/`。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `create_composer_bq_task` / `create_composer_python_task` | Factory | 动态 import `{warehouse}.{task}` → `BigQueryInsertJobOperator` / `PythonOperator` |
| `create_external_sensor` | Factory | 日批 `ExternalTaskSensor`（reschedule / retries=1000） |
| `create_external_sensor_hour` | Factory | 小时 ExternalTaskSensor（retries=20）；**仓内无活调用** |
| `ExternalTaskSkipSensor` + `create_external_task_skip_sensor_hour` | Sensor/Factory | 小时批 SUCCESS/SKIPPED/FAILED 透传 |
| `create_external_marker` | Factory | `ExternalTaskMarker`（rpt→alarm） |
| `Check_BQ_Data_IsExists_Operator` | Factory | `BigQueryCheckOperator`（retries=24 / 1h） |
| `TtSend` / `send_failure_alert_factory` | Handler/Factory | TT webhook 失败回调；`send_tt_alert_factory` 无活调用且语义异常 |
| `access_cloud_run_write_aliyun_es` | Executor | Cloud Run `/health` + `/api/write-to-es` |
| `delete_by_field_condition` / `get_es_client` | Executor | 直连 ES 按字段批量删 |
| `ElasticsearchWriteOperator` / `excuete_write_es` | Operator | ES 直写；**DAG 活调用=0**（含硬编码凭据样例） |
| `ReadFeiShuToBigQuery` | Service | 飞书 OpenAPI→BQ；凭证硬编码 |
| `util.extract_text_before_parentheses` | Util | 中英括号文本清洗（飞书字段辅助） |
| 消费入口（Step05 清单）：`qpon_ods_d` / `qpon_dwd_d` / `qpon_rpt_d` / `qpon_daily_report` / `qpon_dws_h` | Caller DAG | 工厂最大活消费面；日报用直连 Sensor 旁路 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| `create_composer_bq_task` | 几乎全部日/时批 DAG 入口 | 按模块名构造 BQ Insert Job |
| `create_composer_python_task` | ods/rpt/data_server 等 | 按模块名构造 PythonOperator |
| `create_external_sensor` | 日批入口（Step03≈407 活边） | 等上游 `success`，失败态即 failed |
| `create_external_task_skip_sensor_hour` | dws_h/rpt_h/dim_h 等（≈34） | 小时批 Skip 透传 |
| `create_external_marker` | `qpon_rpt_d`（×2） | 标记下游 alarm 任务 |
| `send_failure_alert_factory` | 各业务 DAG 入口 | 闭包绑定硬编码 `send_url` 作 failure callback |
| `access_cloud_run_write_aliyun_es` | rpt/dwd/data_server/data_options ES 任务（≈22） | BQ SELECT→Cloud Run→ES |
| `delete_by_field_condition` | data_server 删 ES 任务 | 按 term/terms 批量删文档 |
| `ReadFeiShuToBigQuery.*` | 飞书活 Python 任务 | token/bitable/write_to_bigquery |
| `Check_BQ_Data_IsExists_Operator` | 少数校验任务 | BQ Check 长重试门控 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 日批主链：DAG 入口 → `create_external_sensor` → `create_composer_bq_task` → tasks SQL（见 `05_Business_Orchestration.md` §2 分层图）。
- 小时批：入口 → `create_external_task_skip_sensor_hour` → BQ 任务（`qpon_dws_h` 等）。
- ES 旁路：Python 任务 → `access_cloud_run_write_aliyun_es` → Cloud Run → 阿里云 ES（05 §出口服务）。
- 告警横切：Operator 失败 → `send_failure_alert_factory` → `TtSend.sendTT`（与 metadata `TeamtalkRobot` 双轨，见 §H）。
- 日报旁路：`qpon_daily_report` **直连** ExternalTaskSensor（非本工厂）+8h delta（05/06 已证）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | 工厂函数签名即对外契约；Sensor `external_dag_id/task_id` 为跨 DAG RPC | ✅ 仍成立；Marker/SkipSensor 为扩展契约 |
| 03 下游 | BQ location 钉死 `asia-southeast2`；ES/飞书/TT/PubSub | ✅ ES 超时 10/30、飞书硬编码、TT 横切均落在本包或关联 DAG |
| 04 实体 | 工厂不声明表；ES 18 index / 飞书落地由调用方 SQL 决定 | ✅ `ElasticsearchWriteOperator` 活调用仍为 0 |
| 06 异步 | Sensor retries=1000；SkipSensor run_id 对齐；ES 无内重试 | ✅ 本步下钻 slot/失败暴露语义 |
| 07 配置 | 无 pool；硬编码 yzjtoken；ES print 凭据；gcp_monitoring paused | ✅ 见 §G–J |

关联（非本包但接力必审）：`dags/qpon_metadata/gcp_monitoring_alert.py` — `is_paused_upon_creation=True` + Variable `gcp_alter_webhook_url`，与业务 `TtSend` 硬编码双轨。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08a-01 | 禁止在无 Composer slot/`up_for_reschedule` 容量评估下提高日批 Sensor `retries` 或降低 `poke_interval`；新增 Sensor **不得**假设存在 `pool=`（仓内 0 处） | `create_external_sensor`；全仓无 `pool=` | 调度队列打满，层间等待假死 |
| C-08a-02 | 业务 DAG 新增/修改 failure URL **必须**走 Variable（目标接线 `etl_alter_webhook_url`/`TeamtalkRobot`）；禁止新增硬编码 `yzjtoken` | `send_failure_alert_factory`；各 DAG `send_url=` | Token 散落不可吊销；与监控 Variable 双轨失控 |
| C-08a-03 | `TtSend.sendTT`/`stream_upload` 失败必须记 error 级日志或改接 `TeamtalkRobot`；禁止仅 `print`+吞异常 | `TtSend.sendTT` / `stream_upload` | 「任务失败但无人收到告警」静默 |
| C-08a-04 | Cloud Run ES 的 GET/POST timeout 若需环境差异，须提升为参数/Variable；禁止声称「可配」却只改字面量 | `access_cloud_run_write_aliyun_es` | 大查询固定 30s 超时误杀可恢复任务 |
| C-08a-05 | 禁止在生产路径 `print` ES password/api_key/完整 `data` 载荷 | `access_cloud_run_write_aliyun_es`；`get_es_client` | Task Log 凭据泄漏 |
| C-08a-06 | 飞书凭证必须 `Variable.get`；禁止新增/恢复硬编码 `FEISHU_APP_SECRET`（已知技术债，新增同类禁止复制） | `read_feishu_to_bg` 模块常量 | 密钥入库与轮换失败 |
| C-08a-07 | ES 写幂等键=调用方传入的 `id_field`→文档 `_id`；同一 `select_sql` 重跑依赖 upsert/覆盖，禁止无 id 的盲 bulk 当幂等 | `access_cloud_run_write_aliyun_es`；调用方 `*_es.py` | 重复文档或丢覆盖语义 |
| C-08a-08 | 小时批必须用 SkipSensor 工厂；禁止对小时链路误用日批 `retries=1000`；`create_external_sensor_hour` 无活调用前勿当「已投产 API」 | `create_external_task_skip_sensor_hour` vs `create_external_sensor` | 小时失败语义错误或重试风暴 |

---

## G. Sensor 工厂决策与 Slot 压力

**业务背景**：跨 DAG 依赖是分层管道的「RPC」。工厂用超长重试换「上游晚到也能等到」，但未配置 pool，容量完全吃 Composer 默认 slot。

**实现方式**：`create_external_sensor` → `ExternalTaskSensor(mode=reschedule, timeout=64800, poke_interval=600, retries=1000, allowed_states=['success'], failed_states=['failed'])`。小时：`ExternalTaskSkipSensor.poke` 查同 `run_id` 的上游 TI。

**关键决策点**：
- `create_external_sensor` — 上游 `failed` ∈ failed_states → Sensor 失败（可挂 TT callback）；随后仍可被 retries=1000 再次调度
- `create_external_sensor` — `mode=reschedule` → poke 间隙释放 worker，但占调度器 reschedule 队列
- `ExternalTaskSkipSensor.poke` — `ti is None` → return False（继续等）
- `ExternalTaskSkipSensor.poke` — SUCCESS → True；SKIPPED → `AirflowSkipException`；FAILED → `AirflowException`
- `ExternalTaskSkipSensor.poke` — RUNNING/QUEUED/SCHEDULED/**UP_FOR_RETRY** → 一律 info「正在运行中」+ False（无风暴计数）
- `create_external_sensor_hour` — 已定义但无活调用 → 死扩展点
- 全仓无 `pool=` → Sensor 与计算任务争用同一默认容量面

**失败模式**：
1. 上游长期 failed/未跑：Sensor `up_for_retry`/`up_for_reschedule` 堆积 → Composer 调度变慢；排障看 UI 中 `wait_*` 数量与状态，而非仅看业务 task。
2. SkipSensor 与日批 logical date 不一致：同 `run_id` 查不到 TI → 一直 False 直到 timeout。
3. `qpon_dws_h` 等悬空 `check_allowed_hours_is_run`（Step06）：SkipSensor 空转，不门控业务链。

---

## H. TT 告警双轨与 Callback 静默

**业务背景**：业务 DAG 用工厂 `TtSend`；GCP 组件监控用 metadata `TeamtalkRobot`+Variable。两条通道 token/可达性不一致。

**实现方式**：`send_failure_alert_factory(send_url)` 返回 callback → 拼短文案（**不含** exception 正文，尽管已读取）→ `TtSend.sendTT` → chunked POST `mtp.myoas.com`。监控 DAG：`PubSubPullSensor` → `monitoring_alert` → `TeamtalkRobot(GCP_ALTER_WEBHOOK_URL)`。

**关键决策点**：
- `send_failure_alert_factory` — 闭包捕获调用方硬编码 `send_url`（约 3 类 yzjtoken）→ 与 Variable 无关
- `TtSend.sendTT` — `len(sendStr)>=5000` → 截断加后缀
- `TtSend.sendTT` — 任意 Exception → `print(e)` 后吞掉（callback 不二次抛）
- `TtSend.stream_upload` — status≠200 → 仅 print，不 raise
- `send_tt_alert_factory` — **定义时立即 sendTT**，返回值非标准 callback；仓内无调用（陷阱 API）
- `etl_alter_webhook_url` / `create_common_teamtalk_alter_callback` — Variable/更好实现 **0 业务消费**
- `gcp_monitoring_alert` DAG — `is_paused_upon_creation=True` → 未 Unpause 则整链不跑（与业务硬编码告警无关的第二条静默面）

**失败模式**：
1. 任务红了但 TT 无消息：查 task log 是否只有 print「请求接口失败」；Airflow 仍显示 failed。
2. 监控无 TT：先查 DAG 是否 paused，再查 `gcp_alter_webhook_url` 是否空串。
3. 吊销 token：须改数十处源码发版，Variable 通道帮不上业务主路径。

---

## I. Cloud Run ES：超时、幂等与凭据泄漏

**业务背景**：RPT/DWD/data_server 将 BQ 近窗指标推阿里云 ES；工厂封装心跳+写；删除走直连 client。

**实现方式**：Variable 取 `write_es_service_url`/`es_*` → GET `/health`(timeout=10) → 组装 payload → POST `/api/write-to-es`(timeout=30)。删：`get_es_client` + search_after 批量 delete。

**关键决策点**：
- `access_cloud_run_write_aliyun_es` — health≠200 / Timeout / ConnectionError → raise（触发外层 DAG retries，函数内无循环）
- 同函数 — `es_user` 非空 → 附加 user/password；`es_api_key` 非空 → 覆盖 `api_key`（默认字面 `"None"`）
- 同函数 — **print 变量信息含 password/api_key；print 完整 data** → 日志泄漏
- POST 响应 — status≠200 或 JSON.`error` → raise；非 JSON 则 pass 当成功路径继续
- `delete_by_field_condition` — list→terms / 标量→term；batch 失败仅 print 计数，不中断整批策略取决于 helpers.bulk
- `ElasticsearchWriteOperator` / `excuete_write_es` — 硬编码 host/密码样例；**无 DAG 引用**（已知技术债，禁止复制为生产路径）

**失败模式**：
1. 固定 30s：大数据量写在 Cloud Run 侧未完成即 Timeout → 外层重试可能重复写（依赖 `id_field` 幂等）。
2. Task Log 出现 `es_password`/`api_key`：即 L48/56/60 泄漏，需立刻轮换密钥并改日志。
3. 误用 `ElasticsearchWriteOperator` 样例凭据：直连内网 IP，绕过 Cloud Run 审计。

**幂等**：文档 `_id` = 调用方 `id_field`；无 id 时 Cloud Run/ES 行为由服务端决定——约束见 C-08a-07。

---

## J. BQ/Python 工厂扩展点与 Marker

**业务背景**：几乎所有分层任务经统一工厂创建，保证 location/回调一致；Marker 用于 rpt 完成通知 alarm。

**实现方式**：`importlib.import_module(f"{warehouse_path}.{task_module_name}")` → `getattr(module, task_module_name)` 零参取 SQL 或 callable。`create_external_marker` 默认 `task_id={external_task_id}_marker`。

**关键决策点**：
- `create_composer_bq_task` — location **硬编码** `asia-southeast2`；无 retries 覆盖（继承 DAG default_args）
- `create_composer_python_task` — `provide_context=True`；函数名必须与模块名同名
- `Check_BQ_Data_IsExists_Operator` — retries=24、retry_delay=1h → 最长约日级数据到达等待
- `create_external_marker` — 可选 `execution_date_fn`；活用量仅 rpt×2
- 扩展新任务：**只加 tasks 模块 + 入口一行工厂调用**；禁止在工厂内写表名

**失败模式**：
1. 模块缺少与文件名同名的可调用对象 → import/getattr 在 DAG parse 期失败。
2. 绕过工厂手写 Operator 导致 location/callback 不一致（与 05 分层审计同类腐化）。
3. Marker 与 Sensor 互等配置错误 → 告警 DAG 永不触发（查 rpt 入口 Marker 边）。

---

> [!SUCCESS] 共享编排工厂与告警 模块深潜闭环验证
> - 扫描范围：10 个核心类（`airflow_config/` EOF）+ 代表消费 DAG + `gcp_monitoring_alert`
> - 提取结果：8 个入口方法、8 条衍生约束、4 个业务特性章节（G/H/I/J）
> - 全文行数：195 行（≤ 400 行）
> - 前序验证：Step 02 通过 / Step 03 通过 / Step 04 通过（工厂无表知识；ES/飞书实体在调用方）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 日批 Sensor 工厂固定 retries=1000/timeout=64800/reschedule 且全仓无 pool；业务 TT 硬编码 token + `TtSend` 失败可静默，与 `gcp_alter_webhook_url`/`TeamtalkRobot` 双轨；`gcp_monitoring_alert` 默认 paused 可致监控静默；Cloud Run ES timeout 10/30 不可配且 print 凭据；`ElasticsearchWriteOperator` 与 `create_external_sensor_hour`/`send_tt_alert_factory`/`etl_alter_webhook_url` 为死或陷阱扩展点。
> - **推演约束 (Constraint)**: 下一模块深潜须核对 (1) 该模块 Sensor 是否全走工厂默认且有无局部 timeout 覆盖；(2) failure_callback 是否仍硬编码 yzjtoken；(3) 若含 ES 写，日志是否仍 print 密钥；(4) 收官阶段配置治理优先：接线 Variable webhook → 删硬编码 → 再评估 Sensor retries/pool。
> - **物理锚点 (Anchors)**: `dags/airflow_config/create_external_sensor.py` L10–24 / L45–136；`dags/airflow_config/airflow_tt_send.py` L8–76；`dags/airflow_config/cloud_run_write_aliyun_es.py` L5–100；`dags/airflow_config/cloud_run_delete_aliyun_es.py` L6–138；`dags/airflow_config/create_composer_bq_task.py` L7–45；`dags/airflow_config/read_feishu_to_bg.py` L15–19；`dags/qpon_metadata/gcp_monitoring_alert.py` L42–69
