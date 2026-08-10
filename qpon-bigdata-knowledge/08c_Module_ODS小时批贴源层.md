# 08c 模块深潜：ODS小时批贴源层（ods-h）

> 模块 id=`ods-h`；权威范围=`dags/`（重点 `dags/qpon_ods_h/`）  
> 不重复 Step05 全量调用链；本步钻取 **小时批 vs 日批**、下游 SkipSensor / Sensor 消费语义、写入 `_h` 表决策与失败模式  
> Step08b 接力：所 wait 的 ODS task 是否仍活注册；订单 MERGE 仅 ON `id` 不可假设跨分表安全；旁路失败可能 Airflow 仍绿

> [!SUCCESS] ODS小时批贴源层 模块深潜闭环验证
> - 扫描范围：1 入口 DAG + 活工厂 42 任务 + SkipSensor 工厂 + 下游 dim_h/dwd_h/rpt_h 等待边对照 + 代表 MERGE/DELETE/结算/埋点 tasks
> - 提取结果：6 个入口方法、8 条衍生约束、4 个业务特性章节
> - 全文行数：194 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id / Step 03 下游=dim_h·dwd_h·rpt_h Skip/Sensor / Step 04 实体=`qpon_ods_d.*_h`
> - EOF 状态：`qpon_ods_h.py` 与抽样 tasks / 下游等待入口已读至关键终态；无静默截断

---

## A. 模块定位

`qpon_ods_h` 是小时批（`10 * * * *`）**贴源 ODS 编排入口**：近窗 MERGE / 小时分区 DELETE+INSERT / 结算 Python 分表合并，写入日批 dataset `qpon_ods_d` 下的 `*_h`（及埋点表 `ods_qpon_event_message`），供 `qpon_dim_h` / `qpon_dwd_h` / `qpon_rpt_h` 等跨 DAG 等待；本包**无出站**业务 Sensor、无 Adjust/Spark/飞书旁路。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_ods_h` / `qpon_ods_h.py` | Orchestrator | DAG 默认参数、TT callback、工厂任务注册与 `start >>` 扇出 |
| `create_composer_bq_task` | Factory | 动态 import → BQ SQL 任务（活≈36） |
| `create_composer_python_task` | Factory | 结算 6 表分表合并 Python（活=6） |
| `create_external_task_skip_sensor_hour` / `ExternalTaskSkipSensor` | Factory/Sensor | **本包不调用**；下游小时批等本层时的标准门控 |
| `create_external_sensor` | Factory | **本包不调用**；`qpon_dwd_h` 误用其等本层（retries=1000） |
| `ods_*_h` / `ods_qpon_event_message` tasks | Executor | MERGE 近窗贴源 / DELETE+INSERT 小时快照 / 埋点小时窗 |
| `qpon_dim_h` | Downstream Caller | SkipSensor×8→本层门店/商户维任务 |
| `qpon_dwd_h` | Downstream Caller | ExternalTaskSensor×≈30→本层（非 Skip）+ ShortCircuit 小时门控 |
| `qpon_rpt_h` | Downstream Caller | SkipSensor→本层订单/券/用户等 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_ods_h` parse | Composer | 注册 42 个活 ODS 小时任务与扇出 |
| `create_composer_bq_task(...)` | `qpon_ods_h.py` | 绑定 warehouse 常量 + stem 同名函数返回 SQL |
| `create_composer_python_task(...)` | 同上 | 结算类 callable 吃 `logical_date` |
| `send_failure_alert_factory(send_url)` | 多数任务 callback | 硬编码 yzjtoken（继承 08a/08b） |
| `create_external_task_skip_sensor_hour(..., qpon_ods_h, …)` | dim_h/rpt_h/dws_h/analyst_h | 同 `run_id` 透传 SUCCESS/SKIPPED/FAILED |
| `create_external_sensor(..., qpon_ods_h, …)` | `qpon_dwd_h` | 仅允许 SUCCESS；retries=1000（日批工厂套小时上游） |

---

## D. 调用链（引用 Step05，不重复追踪）

- 主扇出：`start` → 各 `ods_*_h` / `ods_qpon_event_message` 并行（`05_Business_Orchestration.md` §小时批 / A.3）。
- 下游：`dim_h` SkipSensor→维表；`dwd_h` Sensor→事实；`rpt_h` SkipSensor→报表；写入落点多为 `qpon_ods_d.*_h`（Step04）。
- 本包无 TimeDelta / Adjust / Spark / 飞书链（对比日批 §2.2–2.3）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==导出名==task_id；Sensor `external_dag_id/task_id` | ✅；治理注释失活 `ods_digital_food_mall*_h` / `ods_rank_detail_h`（tasks 文件可仍在） |
| 03 下游 | dim_h/dwd_h/rpt_h 等本层；SkipSensor 活边 | ✅；**接力**：仓内活 wait→`qpon_ods_h` 共 48 边、37 个唯一 task_id，**全部仍在入口活注册**（MISSING=0）；已注释等待的 mall/rank 与入口失活一致 |
| 04 实体 | 小时写入口落 `qpon_ods_d.*_h` / 埋点同 dataset | ✅ |
| 06 异步 | SkipSensor retries=20；`check_allowed_hours_is_run` 在 dwd_h | ✅；本包无空转 Sensor；dwd_h 对本层用日批 Sensor 工厂 |
| 07 配置 | TT 硬编码；小时 Skip 工厂 timeout=7200 | ✅ 继承 |

**08b 接力三项**：
1. 活注册：见上表，当前下游 wait 目标均活。
2. MERGE 仅 ON `id`：`ods_t_life_order*_h` / 券核销族 / 结算 6 表 — **不可**当跨分表安全（对照 `ods_digital_food_order_all_h` 的 `id+db_name+table_name`）。
3. 旁路绿：本包无 Adjust `return False`；但结算 `list_tables` 漏表、MERGE 互盖、TT 吞异常仍可「任务绿 / 数错 / 群静默」。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08c-01 | 小时贴源目标表名必须带 `_h`（埋点表例外），dataset 固定 `qpon_ods_d`；禁止另起 `qpon_ods_h` dataset 除非全仓同步改读方 | `ods_*_h.insert_dataset_id`；`ods_qpon_event_message` | 下游读空表或双写分裂 |
| C-08c-02 | 分表事务 MERGE：幂等键须含分表维；`ods_t_life_order_all_h` 等 **仅 ON id** 为已知技术债，新增禁止复制；安全对照=`ods_digital_food_order_all_h` / `ods_digital_pay_order_all_h` | `ods_t_life_order_all_h` MERGE ON；`ods_digital_food_order_all_h` ON 三键 | 跨分表同 id 互盖 |
| C-08c-03 | 近窗幂等：QUALIFY 去重键必须与 MERGE ON 一致；源窗默认 `execution−5h`（用户表 −3h）变更须评估漏数 | `ods_*_all_h` `prev_hour_partition`；`ods_user_info_c_all_h` | 漏变更或重复 upsert 语义错乱 |
| C-08c-04 | 小时快照维（门店/POI 等）必须 `DELETE partition_date=业务日` + `INSERT`；`prev_hour` 用 `hours=+7` 对齐业务日，禁止照抄 MERGE 的 −5h | `ods_store_h`；`ods_poi_info_h` | 分区错日或快照空洞 |
| C-08c-05 | 等本层小时上游：优先 `create_external_task_skip_sensor_hour`；禁止新增 `create_external_sensor`（retries=1000）套小时 DAG——`qpon_dwd_h` 现网模式为已知技术债，禁止复制 | `qpon_dim_h` Skip vs `qpon_dwd_h` ExternalTaskSensor | 跳过语义丢失；重试风暴占槽 |
| C-08c-06 | 结算 Python：`list_tables` 匹配分表正则 + 历史主表 UNION；漏新分表时 BQ 仍可能成功——必须在 log 核对 UNION 清单 | `ods_settle_*_all_h(logical_date)` | 静默少库且 Airflow 绿 |
| C-08c-07 | 下线任务须同时注释入口工厂与全部下游 `wait_*`；禁止只删一边（治理 mall/rank 已双侧注释可作模板） | `qpon_ods_h` 注释块；`qpon_dwd_h` 注释 wait | 悬空 Sensor 或空跑表 |
| C-08c-08 | 新增 `failure_callback` 的 `send_url` 必须走 Variable；禁止再硬编码 yzjtoken（已知技术债） | `qpon_ods_h.send_url` | Token 不可吊销；TT 失败可静默 |

---

## G. 小时批 vs 日批差异

**业务背景**：同贴源域双调度——日批承接全量/旁路/长窗门控；小时批只做近实时近窗贴源与小时快照，供同小时下游。

**实现方式**：

| 维度 | `qpon_ods_h` | `qpon_ods_d`（08b） |
|---|---|---|
| cron | `10 * * * *` | `0 18 * * *` |
| 出站门控 | 无 | TimeDelta + Adjust/Spark Sensor |
| 旁路 | 无 Adjust/Spark/飞书 | 有 |
| 写目标 | `qpon_ods_d.*_h`（及埋点） | `qpon_ods_d.*`（日表/飞书 dataset） |
| 被等待 | Skip（dim/rpt…）+ 日工厂 Sensor（dwd_h） | 日批 ExternalTaskSensor 为主 |
| 活任务量 | 42 | ≈124 |

**关键决策点**：
- `qpon_ods_h` DAG — 无 `create_external_*` 调用 → 纯被等待方
- 订单小时窗 — `hours=-5` 近窗 MERGE（非日批 `wait_1_hours` 墙钟门控）
- 快照小时表 — `hours=+7` 定 `partition_date` → 与日批「自然日」偏移不同，禁止混用公式
- 数据治理注释 — 小时入口同样用「no downstream」失活 mall/rank

**失败模式**：
1. 误用日批表名读小时链 → 数据滞后或字段不一致；查 FQN 是否 `*_h`。
2. 把日批 TimeDelta 习惯搬进小时入口 → 每小时叠加延时，链路不可用。
3. 只改日批 MERGE ON 键、忘记小时同构文件 → 双调度行为分裂。

---

## H. 写入 `_h` 表决策（MERGE / DELETE+INSERT / 埋点）

**业务背景**：调度包名 `*_h` 与物理 dataset 分离；小时结果落在日批 dataset，用表后缀区分语义。

**实现方式**：
- **分表 MERGE**：`qpon_staging` 或源库 `*_0_3` 循环 UNION → QUALIFY → `MERGE INTO qpon_ods_d.ods_*_all_h`。
- **单表近窗 MERGE**：源库单表 + `db_name/table_name` 常量 → ON 三键（商品等）。
- **小时快照 DELETE+INSERT**：门店/POI/扩展信息等 → 删业务日分区再全量源表插入。
- **结算 Python MERGE**：`list_tables` 动态拼 UNION + 历史主表 → ON `id`。
- **埋点**：`ods_qpon_event_message` 按 publish 小时 DELETE+INSERT，再按 `(partition_date,message_id,eventGroup,eventId)` 去重 UPDATE。

**关键决策点**：
- `ods_digital_food_order_all_h` — `ON id + db_name + table_name` → 跨分表安全对照
- `ods_t_life_order_all_h` — QUALIFY `table_name,id` + 状态拨 `rn_update_time`，但 **MERGE 仅 ON id** → 分表碰撞互盖；MATCHED 时回写 `db_name/table_name`
- `ods_t_life_order_item/voucher/coupon*_h` — 同「仅 ON id」债
- `ods_settle_*_all_h` — QUALIFY `PARTITION BY id` + ON id → 分表 id 碰撞时只留一条
- `ods_user_info_c_all_h` — ON `(user_id,id)`；近窗 −3h；含 AES 解密 UDF
- `ods_store_h` — DELETE+INSERT；分区键 `hours=+7`
- `ods_qpon_event_message` — 无 `_h` 后缀；小时窗 `[prev_0, prev_1)` +7h 分区日

**失败模式**：
1. 仅 ON id 互盖 → Airflow 绿、明细串分表；对比源 `table_name` 与 ODS 行。
2. DELETE 成功 INSERT 失败 → 该小时/业务日分区空洞；依赖 retries=3，无跨语句事务。
3. 埋点去重 UPDATE 失败但 INSERT 已成功 → 可能短暂重复；查同小时 `etl_time` 分布。

---

## I. SkipSensor 消费语义与 dwd_h 异例

**业务背景**：小时上游可能 ShortCircuit/跳过；下游应用 Skip 透传，避免把 SKIPPED 当失败长重试。本层本身不 Skip 业务任务（无 ShortCircuit）。

**实现方式**：`ExternalTaskSkipSensor.poke` 同 `run_id` 查 TI：SUCCESS→通过；SKIPPED→`AirflowSkipException`；FAILED→`AirflowException`；工厂 retries=20、timeout=7200、poke=300。

**关键决策点**：
- `create_external_task_skip_sensor_hour` — dim_h×8 / rpt_h 多条 / dws_h·analyst_h → 合规小时等待
- `qpon_dwd_h` — 对本层几乎全部用 `create_external_sensor`（allowed_states=success only, retries=**1000**）→ 无 Skip 透传；上游若 SKIPPED 不会按 Skip 语义结束
- `qpon_dwd_h.check_allowed_hours` — ShortCircuit 门控本 DAG 部分链；Dummy `check_allowed_hours_is_run` 供 dws_h 空转等待（Step06），与本层无关
- 本包入口 — **零** SkipSensor 实例

**失败模式**：
1. 上游 ODS 任务失败：Skip 下游红并可 TT；dwd_h Sensor 同失败但可重试至 1000 → Composer 槽位压力（08a）。
2. 误复活已治理 task：下游若未同步注释 wait → 空等超时。
3. 用日批 Sensor 等小时 DAG：上游跳过时行为依赖 TI 状态机，排查勿假设「与 dim_h 相同」。

---

## J. 失败模式与「任务绿」陷阱

**业务背景**：08b 旁路「绿但仍错」在小时包无 Adjust API；等价陷阱转为 **静默少库、键冲突互盖、告警静默**。

**实现方式 / 决策点**：
- 结算 `list_tables` 无匹配 → UNION 空或仅历史表 → MERGE 影响 0 行仍成功
- 订单仅 ON id → 错数不改 TI 状态
- `TtSend` 失败可静默（08a）→ DAG 红但群无消息，或反过来只看到绿
- `start_new_task` — 无下游边 → 空转绿根
- 工厂未挂 `start_task >>` 的任务不会出现在当前活集（本包活任务均已挂边）

**失败模式排查**：
1. 结算少分表：读 Python task log 打印/拼出的表清单 vs BQ `INFORMATION_SCHEMA`。
2. 跨分表互盖：抽同 `id` 多 `table_name` 的源行，看 ODS 是否只剩一行且 `db_name` 被后写覆盖。
3. 近窗漏数：对比 `source_timestamp` 与 `prev_hour_partition`（−5h/−3h）。
4. 「Airflow 全绿但报表空」：先确认读的是 `*_h` 且对应小时分区/近窗已跑，再查 TT/监控是否静默。

---

> [!SUCCESS] ODS小时批贴源层 模块深潜闭环验证
> - 扫描范围：入口+42 活任务+SkipSensor 工厂+dim_h/dwd_h/rpt_h 等待边+MERGE/DELETE/结算/埋点代表
> - 提取结果：6 个入口方法、8 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：194 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅（48 wait 边全部活注册）/ Step 04 ✅
> - EOF 状态：已确认遍历关键文件至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 小时 ODS 写 `qpon_ods_d.*_h`；无出站 Sensor/旁路；`ods_t_life_order*_h`/结算 MERGE 仅 ON `id`；`ods_digital_food_order_all_h` 为三键安全对照；下游 dim/rpt 用 SkipSensor，**dwd_h 用日批 ExternalTaskSensor(retries=1000)**；当前 37 个被 wait 的 task 均仍活注册；治理失活 mall/rank 双侧已注释
> - **推演约束 (Constraint)**: 下一模块（dim-h/dwd-h）必须核对：不得复制 dwd_h「日工厂等小时」模式；消费订单小时表不得假设仅 ON id 跨分表唯一；结算少表勿只看 TI 成功
> - **物理锚点 (Anchors)**: `dags/qpon_ods_h/qpon_ods_h.py` L95-100/L135-220/L234-323；`tasks/digital_food_market_0_3/ods_t_life_order_all_h.py` MERGE ON id；`tasks/digital_food_order_0_3/ods_digital_food_order_all_h.py` ON 三键；`tasks/digital_food_settle/ods_settle_clear_detail_info_all_h.py` list_tables+ON id；`tasks/digital_food_order/ods_store_h.py` DELETE+INSERT +7h；`dags/qpon_dim_h/qpon_dim_h.py` SkipSensor；`dags/qpon_dwd_h/qpon_dwd_h.py` create_external_sensor→ods_h；`dags/airflow_config/create_external_sensor.py` ExternalTaskSkipSensor.poke
