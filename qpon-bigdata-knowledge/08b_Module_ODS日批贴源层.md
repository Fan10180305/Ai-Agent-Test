# 08b 模块深潜：ODS日批贴源层（ods-d）

> 模块 id=`ods-d`；权威范围=`dags/`（重点 `dags/qpon_ods_d/`）  
> 不重复 Step05 全量调用链；本步钻取 **MERGE vs DELETE+INSERT**、跨 DAG Sensor、Adjust/Spark/飞书旁路失败模式  
> Step08a 接力：Sensor 工厂默认（retries=1000/无 pool）、`failure_callback` 硬编码 TT token、ES print 凭据（本模块无活 ES，告警债仍继承）

> [!SUCCESS] ODS日批贴源层 模块深潜闭环验证
> - 扫描范围：1 入口 + 活工厂≈124 任务槽 + 5 门控 Sensor/TimeDelta + 代表 tasks（MERGE/DELETE/Adjust/Spark/飞书/结算）+ 下游对照 DAG 名
> - 提取结果：7 个入口方法、8 条衍生约束、4 个业务特性章节
> - 全文行数：191 行（≤ 400 行）
> - 前序验证：Step 02 契约=工厂导出名 / Step 03 下游=BQ·Adjust·Spark·飞书·TT / Step 04 实体=`qpon_ods_d.*`+飞书落地
> - EOF 状态：`qpon_ods_d.py` 与抽样 tasks 已读至 EOF；无静默截断

---

## A. 模块定位

`qpon_ods_d` 是日批（`0 18 * * *`）**贴源 ODS 层编排入口**：把 Datastream/源库 dataset、Adjust 外部表、Spark 落表、飞书多维表同步进 `qpon_ods_d`（及少量 `qpon_sync_from_feishu`），供 dim/dwd/rpt 等层 ExternalTaskSensor 等待；入口只做工厂注册与依赖扇出，SQL/Python 在 `tasks/`。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_ods_d` / `qpon_ods_d.py` | Orchestrator | DAG 默认参数、TT callback、TimeDelta/Sensor、工厂任务注册与 `>>` |
| `create_composer_bq_task` | Factory | 动态 import tasks → `BigQueryInsertJobOperator`（活≈109） |
| `create_composer_python_task` | Factory | 结算分表合并、Adjust API、飞书等 Python 任务（活≈15） |
| `create_external_sensor` | Factory | 仅活边：等 `Qpon_Adjust_Raw_Data.CREATE_EXTERNAL_TABLE_QponAdjust` |
| `ExternalTaskSensor`（直连） | Sensor | `wait_spark_ug_rch_send_record` → 整 DAG `spark_ug_rch_send_record_ephemeral`（无 `external_task_id`） |
| `TimeDeltaSensor` | Sensor | `wait_{1,2,12,14}_hours`；14h 用 retries=2000 / delay=60min |
| `ods_*` tasks（MERGE 族） | Executor | 分表/近窗增量 MERGE（订单/券/CRM/评论等） |
| `ods_*` tasks（DELETE+INSERT 族） | Executor | 日分区全量覆盖贴源（门店/活动/结算等主体） |
| `ReadFeiShuToBigQuery`（经飞书 task） | Service | 唯一活飞书：`ods_new_store_from_mkt_for_using` |
| `qpon_dim_d` / `qpon_dwd_d` / `qpon_dws_d` | Downstream Caller | 跨 DAG Sensor 消费本层 task（非本包实现） |
| `qpon_*_test` / `qpon_test_d` 等 | Mirror | Step05 清单对照；本步不展开 test 包 SQL |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_ods_d` parse | Composer 调度器 | 注册全部 ODS 日批任务与门控 |
| `create_composer_bq_task(...)` | `qpon_ods_d.py` | 绑定 warehouse + stem 同名函数返回 SQL |
| `create_composer_python_task(...)` | 同上 | 绑定 callable；结算类签名吃 `logical_date` |
| `create_external_sensor(..., Qpon_Adjust_Raw_Data, CREATE_EXTERNAL_TABLE_QponAdjust)` | Adjust 链 | 等外部表创建成功后再 DELETE+INSERT 原始明细 |
| `ExternalTaskSensor(wait_spark_ug_rch_send_record)` | Spark 链 | 等 ephemeral Spark DAG 成功后再写 `ods_ug_rch_send_record` |
| `TimeDeltaSensor(wait_*_hours)` | 订单 MERGE / Adjust API / 结算 PM | 用墙钟延时换源延迟窗口 |
| `send_failure_alert_factory(send_url)` | 多数任务 `on_failure_callback` | 硬编码 yzjtoken；Adjust 两日报 Python **未传** callback |

---

## D. 调用链（引用 Step05，不重复追踪）

- 主扇出：`start` →（多数）`create_composer_bq_task` → tasks DELETE+INSERT / MERGE（`05_Business_Orchestration.md` §2.1）。
- Adjust：`wait_1_hours` → Sensor(`Qpon_Adjust_Raw_Data`) → `ods_qpon_adjust_raw_data_inc_d`；`wait_12_hours` → Adjust Reports API Python（§2.2）。
- Spark：`wait_spark_ug_rch_send_record` → `ods_ug_rch_send_record` DELETE+INSERT（§2.3）。
- 下游：dim/dwd/rpt/… 对本 DAG 的 `wait_{ods_*}` 边（Step03：dwd×64 / rpt×52 / dim×32 等）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==导出名==task_id；Sensor 边 `external_dag_id/task_id` | ✅；注释模板仍把 `ods_t_act_award` 误作 dag_id（勿复活） |
| 03 下游 | 重度读 `qpon_ods_d`；Adjust/Spark/飞书/TT | ✅；本包 **无** Cloud Run ES 活调用 |
| 04 实体 | `ods_t_life_order_all_d` MERGE；飞书落地 `qpon_sync_from_feishu.*` | ✅；飞书活任务仍仅 new_store |
| 06 异步 | Sensor1000；TimeDelta1000/2000；分区 DELETE+INSERT 幂等 | ✅；见 §G–I |
| 07 配置 | 硬编码 TT；Sensor 无 pool | ✅ 继承 08a；另见 Adjust API token 硬编码 |

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08b-01 | 源库/Datastream 近窗变更跟踪必须用 MERGE（或同文件既有策略）；禁止把 `digital_food_*` / `qpon_staging` 当仓内可写目标 | `ods_t_life_order_all_d`；`ods_review_info` | 写穿源层或丢增量语义 |
| C-08b-02 | 日快照维/配置表必须 `DELETE WHERE partition_date=…` + `INSERT`；禁止无分区键全表盲写 | `ods_store_info`；`ods_t_act_award` | 分区污染、重跑不可幂等 |
| C-08b-03 | MERGE 幂等键必须与 QUALIFY 去重键一致；`ods_t_life_order_all_d` 源侧按 `table_name,id` 去重但 `ON target.id=source.id`——**已知技术债，新增同类禁止复制「仅 ON id」** | `ods_t_life_order_all_d` MERGE ON | 跨分表同 id 互相覆盖 |
| C-08b-04 | 等 Spark 必须声明明确终态任务或接受「整 DAG success」语义；改 ephemeral DAG 名须同步改 Sensor | `wait_spark_ug_rch_send_record` | 空等/误等，触达表空洞 |
| C-08b-05 | Adjust 外部表明细：Sensor 成功后再跑；DELETE 窗口须覆盖 `prev_1` 与当日分区两日 | `wait_CREATE_EXTERNAL_TABLE_QponAdjust`；`ods_qpon_adjust_raw_data_inc_d` | 读不存在的日表或漏补昨日 |
| C-08b-06 | Adjust Reports Python：API/BQ 失败必须 `raise`；禁止 `return False` 后由 `main_task` 吞掉（任务仍绿） | `ods_adjust_daily_report_dynamic.main_task` | 静默丢数且无 TT |
| C-08b-07 | 新增/修改 `failure_callback` 的 `send_url` 必须走 Variable；禁止新增硬编码 yzjtoken（已知技术债） | `qpon_ods_d.send_url`；Adjust 两任务甚至无 callback | Token 不可吊销；失败无告警 |
| C-08b-08 | 飞书写 BQ：`deleteCondation=""` ≡ `DELETE WHERE 1=1` 全表清空再 APPEND；禁止当「增量 append」理解 | `ods_new_store_from_mkt_for_using`；`ReadFeiShuToBigQuery.write_to_bigquery` | 误判幂等或并发双跑互删 |

---

## G. MERGE vs DELETE+INSERT 决策

**业务背景**：ODS 同时承接「会变的事务事实」与「日切快照维表」。前者需按主键 upsert；后者按业务日整分区重刷。

**实现方式**：
- MERGE：`qpon_staging`/`*_0_3` 分表 UNION + `QUALIFY` 后 `MERGE INTO qpon_ods_d.*`（订单/券/支付/CRM/近窗评论等）。
- DELETE+INSERT：源库单表或结算 Python 拼 UNION → 删当日 `partition_date` → INSERT（门店、活动奖品、结算清算等）。
- 结算 Python：`list_tables` 匹配 `{table}_\\d+`，历史主表 `create_time<=2025-10-31` UNION 分表，再 QUALIFY `id`。

**关键决策点**：
- `ods_t_life_order_all_d` — `order_status∈{COMPLETED,RETURN}` → 人为拨 `rn_update_time` +2s/+4s 再 QUALIFY → 同戳冲突时状态优先级偏向完成/退单
- 同函数 — `ON target.id = source.id`（不含 `table_name`/`db_name`）→ 跨分表 id 碰撞时 UPDATE 互盖
- `ods_review_info` — `ON (partition_date,id,table_name)` → 分表安全对照
- `ods_store_info` / `ods_t_act_award` — 仅当日分区 DELETE → 全量源表 INSERT（快照语义）
- `ods_ug_rch_send_record` — `DELETE partition_date >= day` + 源 `create_time>=day` → 向前滚动窗口（非整库）
- `ods_settle_*` vs `*_pm_update` — 同 SQL 骨架；后者挂 `wait_14_hours` → 午后补数窗

**失败模式**：
1. MERGE 源近窗 `prev_hour_partition`（execution−5h）过短 → 漏变更；排障对比源 `source_timestamp` 与 ODS `etl_time`。
2. DELETE 成功 INSERT 失败 → 当日分区空洞；依赖 DAG retries=3，无跨任务事务。
3. 结算 `list_tables` 漏新分表 → 静默少库；查 task log 的 UNION 表清单。

---

## H. 跨 DAG Sensor 与 TimeDelta 门控

**业务背景**：ODS 自身几乎不 Sensor 其他业务层；反而被下游大量等待。本包仅门控 Adjust 外部表与 Spark，并用 TimeDelta 对齐源延迟。

**实现方式**：工厂 Sensor（retries=1000, timeout=64800, poke=600, reschedule）一条；直连 Spark Sensor（retries=1000，**无** factory timeout 默认 unless 继承）；TimeDelta 1/2/12/14h。

**关键决策点**：
- `create_external_sensor` — 上游 `failed` → Sensor 失败并可 TT；仍可再试至 1000
- `wait_spark_ug_rch_send_record` — **未设** `external_task_id` → 等整 DAG success；注释残留旧 dag_id `spark_ug_rch_send_record`
- `wait_1_hours` — 门控 `_0_3` 订单/券 MERGE 与 Adjust 外部表链
- `wait_12_hours` — 门控 Adjust API 两日报（不经外部表 Sensor）
- `wait_14_hours` — retries=**2000**、retry_delay=60min → 结算 PM 更新
- `wait_2_hours` / `start_new_task` — **无下游 `>>`** → 空转门控/哑元
- `ods_t_user_subscribe_record_inc_d` / `ods_new_store_from_mkt_for_using` — 已工厂注册但 **未挂** `start_task >>` → 孤立根任务（仍会调度，脱离统一扇出）

**失败模式**：
1. Adjust 外部表任务失败：`wait_CREATE_*` 长占 reschedule（08a slot 债）→ 下游 dim/dwd 再叠 Sensor，级联排队。
2. Spark ephemeral 改名/未跑：触达 ODS 永不成功；查 Sensor 的 `external_dag_id`。
3. 误把注释模板 `create_external_sensor(dag,"ods_t_act_award",…)` 当活边 → 等错 DAG。

---

## I. Adjust / Spark / 飞书旁路失败模式

**业务背景**：三条旁路不走「源库 DELETE+INSERT」主模板：外部表日文件、HTTP Reports、飞书 bitable。

**实现方式**：
- Adjust 明细：双端 dataset 日后缀表 UNION → 两日分区 DELETE+INSERT。
- Adjust 日报：硬编码 Bearer/`app_tokens` → `requests.get` → 按 `day` DELETE 分区 → `load_table_from_dataframe` APPEND。
- Spark：Sensor 后门控 `ods_ug_rch_send_record`。
- 飞书：`download_feishu_bitable_all` → 列映射/时间 +8h → `write_to_bigquery(..., "")` 全表删写；凭证在 `ReadFeiShuToBigQuery` 硬编码（08a C-08a-06）。

**关键决策点**：
- `ods_qpon_adjust_raw_data_inc_d` — 读 `{table}_{yyyyMMdd}` 字面日表 → 外部表未建则 BQ 失败
- `get_adjust_data` — 空 rows / HTTP 异常 → `return None`（不 raise）
- `adjust_to_bigquery_etl` — 任一步 False → `main_task` **忽略返回值** → Operator 成功
- `ods_adjust_daily_report_*` 工厂调用 — **省略** `failure_callback` → 即便 raise 也无本 DAG TT 闭包
- `ods_new_store_from_mkt_for_using` — except print 后 `raise` → 可失败；但依赖飞书 token/wiki 解析
- 费用类飞书任务 — 入口大面积注释「春节后认证」→ 失活，勿当活契约

**失败模式**：
1. Adjust API token 失效：日志「无法获取数据」但任务绿 → 报表分区停更（C-08b-06）。
2. 外部表日分区缺失：BQ job 失败 → Sensor 上游红或本任务红；先查 `Qpon_Adjust_Raw_Data`。
3. 飞书认证失败：任务红 + TT（若 callback 生效）；费用链注释失活导致业务以为「ODS 仍在同步」。
4. 继承 08a：`TtSend` 吞异常 → 「ODS 红了但群静默」；与 `gcp_monitoring_alert` paused 无关。

---

## J. 编排扩展与数据治理失活面

**业务背景**：入口用注释批量下线「no downstream」表，并用 `start_new_task` 预留扇出；扩展应复制「warehouse 常量 + 工厂一行 + `start`/`wait_*` 边」。

**实现方式**：`仓库目录常量` → `create_composer_*` → 依赖区 `start_task >>` 或 `wait_* >>`。

**关键决策点**：
- 注释块标注「数据治理 2026-03-30/31（no downstream）」→ 模块文件可仍在 `tasks/` 但入口失活
- 新 MERGE 分表 — 必须改 `_0_3` 循环/`list_tables` 正则，而非只加单表 DELETE 任务
- Python 结算 — 函数名=stem，且需 `logical_date`（工厂 `provide_context`）
- 禁止在入口写 SQL；禁止新增第三条硬编码 TT token

**失败模式**：
1. 只加 tasks 文件未改入口 → 永不调度。
2. 只注册工厂不写 `>>` → 孤立根，review 时易漏依赖门控。
3. 复活注释任务不评估下游 Sensor 契约 → 恢复空跑表。

---

> [!SUCCESS] ODS日批贴源层 模块深潜闭环验证
> - 扫描范围：入口+工厂+Sensor/TimeDelta+MERGE/DELETE/Adjust/Spark/飞书/结算代表类（对照 Step05 核心清单）
> - 提取结果：7 个入口方法、8 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：191 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅（飞书实体在 `qpon_sync_from_feishu`）
> - EOF 状态：已确认遍历关键文件至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: ODS 写策略二分（MERGE 近窗 vs DELETE+INSERT 日快照）；`ods_t_life_order_all_d` MERGE 仅 ON `id`；Adjust API Python `return False` 不失败；Spark Sensor 等整 DAG；飞书全表 DELETE+APPEND；TT/Adjust token 硬编码；大量治理注释失活
> - **推演约束 (Constraint)**: 下一模块（dim/dwd 等）必须核对：所 wait 的 ODS task 是否仍活注册；不得假设「仅 ON id」的订单 MERGE 跨分表安全；旁路失败勿只看 Airflow 绿态
> - **物理锚点 (Anchors)**: `dags/qpon_ods_d/qpon_ods_d.py` L27-29/L127-171/L184/L412-413/L508/L713-715；`tasks/digital_food_market_0_3/ods_t_life_order_all_d.py` MERGE ON；`tasks/adjust_data/ods_adjust_daily_report_dynamic.py` `main_task`；`tasks/qpon_feishu/ods_new_store_from_mkt_for_using.py`；`tasks/digital_food_order/ods_store_info.py` DELETE+INSERT
