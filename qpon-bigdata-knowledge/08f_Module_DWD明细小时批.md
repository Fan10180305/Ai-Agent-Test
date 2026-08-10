# 08f 模块深潜：DWD明细小时批（dwd-h）

> 模块 id=`dwd-h`；权威范围=`dags/`（重点 `dags/qpon_dwd_h/`）  
> 不重复 Step05 全量调用链；本步钻取 **日工厂等小时反例**、**Skip vs Sensor 决策**、**小时 voucher 与日批枢纽差异**、**孤儿 wait / 日维裸读**  
> Step08e 接力：(1) 禁止日工厂等 `qpon_ods_h`/`qpon_dim_h`——以 `qpon_dim_h` Skip 为模板；(2) 订单 JOIN 勿假设 MERGE ON `id` 跨分表唯一；(3) 核对 wait 上游仍活接线；(4) 读日维须对账分区与 `2999-12-31`

> [!SUCCESS] DWD明细小时批 模块深潜闭环验证
> - 扫描范围：1 入口 DAG + 活 Sensor 30（接线 25 / 孤儿 5）+ 活 BQ 14（注释下线 10）+ 枢纽 `dwd_product_order_voucher_all_h` + dim_h Skip 对照 + ods_h/dim_h 上游活注册核对 + dws_h/rpt_h 下游 Skip 消费
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：181 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+跨 DAG wait / Step 03 下游=dws_h·rpt_h Skip / Step 04 实体=`qpon_dwd_d.*_h`
> - EOF 状态：`qpon_dwd_h.py` 与小时 voucher SQL 关键路径已读至终态；无静默截断

---

## A. 模块定位

`qpon_dwd_h`（`10 * * * *`）是 **DWD 明细小时批**：埋点流量扇出点击/下单归因，并以 `dwd_product_order_voucher_all_h` 为订单券小时枢纽，经 ODS/DIM 等待后写入日批 dataset `qpon_dwd_d` 的 `*_h` 表；下游 `qpon_dws_h`/`qpon_rpt_h` 用 SkipSensor 消费。本包对小时上游**仍全面使用日批工厂** `create_external_sensor`（retries=1000）——为仓内「日工厂等小时」主反例；合规模板见 `qpon_dim_h` Skip。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_dwd_h` / `qpon_dwd_h.py` | Orchestrator | DAG、TT callback、ShortCircuit 小时门控、Sensor×30、BQ×14 与 `>>` |
| `create_composer_bq_task` | Factory | 动态 import `qpon_dwd_h.tasks.<stem>` → BQ SQL |
| `create_external_sensor` | Factory/Sensor | **误用**：等 `qpon_ods_h`/`qpon_dim_h`；success only；retries=1000 |
| `create_external_task_skip_sensor_hour` | Factory（对照） | **本包未 import**；`dim_h`/`dws_h`/`rpt_h` 合规模板 |
| `ShortCircuitOperator` / `check_allowed_hours` | Checker | 允许小时列表门控 voucher 等 |
| `DummyOperator.check_allowed_hours_is_run` | Marker | 供 `qpon_dws_h` Skip 等待；**不门控**本包业务链 |
| `dwd_product_order_voucher_all_h` | Executor | 订单×券小时枢纽（tmp→目标分区） |
| `dwd_qpon_event_traffic_inc_d` 及 card/place/adtrace 等 | Executor | 埋点与衍生事实 |
| `dwd_product_unique_order_detail_h` / `dwd_settle_clear_detail` / 门店明细 | Executor | 唯一单、结算、门店商品小时明细 |
| `qpon_ods_h` / `qpon_dim_h` | Upstream | 被本包 Sensor 等待的贴源/维小时 |
| `qpon_dws_h` / `qpon_rpt_h` | Downstream Caller | SkipSensor 等本层 BQ |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_dwd_h` parse | Composer | 注册小时明细与跨 DAG Sensor |
| `create_composer_bq_task(..., stem)` | `qpon_dwd_h.py` | 绑定 `warehouse_layer=qpon_dwd_h.tasks` |
| `create_external_sensor(..., qpon_ods_h\|qpon_dim_h, …)` | 入口 | 日工厂等小时上游（反例） |
| `check_allowed_hours` / `ShortCircuitOperator` | voucher 依赖边 | 非允许小时 → Skip 下游 |
| `send_failure_alert_factory(send_url)` | 多数 callback | 硬编码 yzjtoken（继承 08a） |
| `dwd_product_order_voucher_all_h()` | BQ Operator | 返回 tmp DELETE+INSERT → 目标 DELETE+INSERT |
| 下游 `create_external_task_skip_sensor_hour(..., qpon_dwd_h, …)` | dws_h/rpt_h | 合规 Skip 消费本层 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 流量：`start` → `dwd_qpon_event_traffic_inc_d` → place_order_source / card_view_click / adtrace（`05` §A.6）。
- 枢纽：`start` → 多 `wait_ods_*` + `wait_check_allowed_hours` → `dwd_product_order_voucher_all_h` → `dwd_product_unique_order_detail_h`（及结算/门店并行链）。
- 下游：`qpon_dws_h`/`qpon_rpt_h` SkipSensor → 本层 voucher/traffic/unique 等；`wait_check_allowed_hours_is_run` 空转边（Step06）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；Sensor `external_dag_id/task_id` | ✅；孤儿 Sensor×5；注释 BQ×10 |
| 03 下游 | dws_h/rpt_h 等本层；Skip 为主 | ✅；本包对上游用日工厂 Sensor |
| 04 实体 | 写 `qpon_dwd_d.*_h`（18 目标族） | ✅；枢纽落 `dwd_product_order_voucher_all_h` |
| 06 异步 | ShortCircuit + Dummy `check_allowed_hours_is_run`；Sensor retries=1000 | ✅；dws 空转边仍在 |
| 07 配置 | TT 硬编码；小时门控非 Variable | ✅ |

**08e 接力四项（本步审计结论）**：
1. **反例仍存在**：活 `create_external_sensor` **30** 全部指向 `qpon_ods_h`(28)+`qpon_dim_h`(2)；**零** SkipSensor；retries=1000/timeout=64800。合规模板=`qpon_dim_h` 的 `create_external_task_skip_sensor_hour`。
2. **订单 JOIN**：`m1.id=m2.order_id`、`m2.order_item_id=m7.order_item_id`；上游 ODS `*_all_h` MERGE 仅 ON `id`——**禁止**当跨分表全局唯一。
3. **wait 上游活接线**：30 个被 wait 的 task 在 `qpon_ods_h`/`qpon_dim_h` **create+`>>` 均仍活（MISSING=0）**。本包**内部**孤儿 Sensor×5（create 无 `>>`）：`wait_dim_merchant_basic_info_h`、`wait_ods_digital_food_order_all_h`、`wait_ods_digital_merchant_provider_h`、`wait_ods_t_act_activity_all_h`、`wait_ods_t_act_award_record_all_h`（随 saas/看板下线遗留）。
4. **日维分区 vs 2999**：小时 voucher **活读** `dim_merchant_basic_info`（日表）按 `create_time` 对齐日分区 / 锚定 `2025-04-17` / 近 5 日 max 分区（mp01–mp03）——**不读** `2999-12-31` 当前镜像，也**无**日批 dim Sensor；`wait_dim_merchant_basic_info_h` 孤儿≠已消费商户小时维。门店取 **无分区** `dim_store_info` 全表聚合。`dwd_store_info_detail_h` 内 `2999-12-31` 仅作门店截止日期哨兵，非维表当前分区读路径。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08f-01 | 等 `qpon_ods_h`/`qpon_dim_h`：必须用 `create_external_task_skip_sensor_hour`；**禁止新增** `create_external_sensor`(retries=1000) 套小时 DAG——现网本包为已知技术债，禁止复制；模板=`qpon_dim_h` | `qpon_dwd_h` L147–187 vs `qpon_dim_h` Skip | Skip 语义丢；重试风暴占槽 |
| C-08f-02 | `dwd_product_order_voucher_all_h` 幂等键=`partition_date`（UTC+7 业务日=`execution+7h`）；须先清 tmp/目标当日分区再 INSERT；禁止漏删叠写 | voucher_h DELETE+INSERT tmp/目标 | 分区重复/脏快照 |
| C-08f-03 | 小时订单 JOIN 须显式业务键（order_id/order_item_id/voucher_id）；**禁止**假设 ODS MERGE ON `id` 跨分表唯一（已知技术债） | voucher_h `m1.id=m2.order_id`；ods `*_all_h` ON id | 错绑行/金额翻倍 |
| C-08f-04 | 小时 voucher **无**日批 `COMPLETED+售后成功→RETURN` 改写；勿假设两表 `order_status` 同语义；改口径须双批同步 | voucher_h 透传 `m1.order_status` vs 日批 CASE | 小时/日批 GTV 口径分裂 |
| C-08f-05 | 读 `dim_merchant_basic_info`/`dim_product_basic_info` 须声明日分区还是 `2999-12-31`；勿只看 TI 绿；本枢纽读日分区路径且无对应日 Sensor 为已知耦合债 | voucher_h mp01–mp03 | 当前镜像/历史分区错读 |
| C-08f-06 | 下线须同时注释 create、`wait_*`、`>>`；现网孤儿 Sensor×5 禁止新增同类 | saas/看板注释块 vs 活 create | 空跑 Sensor 占槽 |
| C-08f-07 | `check_allowed_hours` 允许列表变更须评估 voucher 扇出与下游 Skip；Dummy `check_allowed_hours_is_run` **不得**当作业务就绪信号 | ShortCircuit L78–99；dws 空转 | 非窗口误跑或下游假门控 |
| C-08f-08 | 小时枢纽依赖采购价日表 `dwd_product_procurement_price_order_*` 为 SQL 裸读（无 wait）；改日批采购价调度须评估小时滞后 | voucher_h ov_price/oi_price | 佣金/采购价字段陈旧但 TI 绿 |
| C-08f-09 | 下游小时消费本层须用 SkipSensor；禁止对 `qpon_dwd_h` 新增日工厂 Sensor | dws_h/rpt_h Skip | 与上游反例叠加放大重试 |

---

## G. 日工厂等小时反例与 Skip 决策

**业务背景**：小时上游可 ShortCircuit/Skip；下游应用 Skip 透传，避免把 SKIPPED 当失败并 retries=1000 长占槽。`dim_h`/`rpt_h`/`dws_h` 已合规；本包是仓内最大反例面。

**实现方式**：入口仅 import `create_external_sensor` → `ExternalTaskSensor(allowed_states=['success'], retries=1000, timeout=64800)`。对照：`create_external_task_skip_sensor_hour` → SUCCESS 通过 / SKIPPED→`AirflowSkipException` / FAILED 失败；retries=20、timeout=7200。

**关键决策点**：
- `qpon_dwd_h` 入口 — 30 活 Sensor 全走日工厂 → **反例仍存在（2026-07 审计时点）**。
- `qpon_dim_h` — 导入日工厂但业务 wait **全 Skip** → 合规模板。
- `wait_check_allowed_hours` — ShortCircuit 按 `execution_date.hour ∈ {19,23,2,5,7,9,12,14}` 门控 voucher；与 Sensor 工厂选型正交。
- 下游 dws/rpt — 对本层用 Skip → 本包若 Skip voucher，下游可透传；本包等 ODS 时**无** Skip 透传。

**失败模式**：
1. 上游 ODS SKIPPED：日工厂 Sensor 不按 Skip 结束 → 空等/失败重试至 1000。
2. 治理只注释 BQ/`>>` 留活 Sensor（孤儿×5）→ Composer 仍调度空转 wait。
3. 误把 `create_external_sensor_hour`(retries=20、仍无 Skip) 当「已修复」——仓内无活调用且仍缺 Skip 语义。

---

## H. 小时 voucher 枢纽 vs 日批差异

**业务背景**：日批 `dwd_product_order_voucher_all` 是全日快照枢纽；小时表供近实时看板/特征，写同 dataset `*_h`，口径与日批**不完全同构**。

**实现方式**：`DELETE` tmp（当日业务分区 **或** ≤execution−2 日）→ `INSERT` tmp 全宽表 → `DELETE`+`INSERT` 目标 `qpon_dwd_d.dwd_product_order_voucher_all_h` 当日分区。驱动源为小时 ODS 合并表 `ods_t_life_order*_all_h` 等。

| 维度 | 日批 voucher | 小时 voucher_h |
|---|---|---|
| 分区戳 | `execution_date+1` 业务日 | `execution+7h` 的 DATE |
| 状态改写 | `COMPLETED`∧售后成功→`RETURN` | **透传** ODS `order_status`（无售后 CASE） |
| 商户维 | JOIN 已注释；仍 wait 日维门控 | **活读**日表 `dim_merchant_basic_info` mp01–03；无日 Sensor |
| 门店维 | `dim_store_info` 全表 | 同（无分区） |
| 采购价 | 同 DAG 任务边等待 | SQL 裸读日表采购价 |
| Sensor | 日工厂等日 ODS/DIM（合规） | 日工厂等小时 ODS（反例）+ ShortCircuit |
| 扇出 | 财务/核销/首单等日批大扇出 | unique_order / rpt_h / dws_h 特征 |

**关键决策点**：
- 金额 — `pay_reality_amount` 优先；`create_time≤2025-12-01` 可回退支付表（与日批同思路）。
- 首单 — 正式单且状态∈{COMPLETED,RETURN}（即便小时未本地改写 RETURN，仍认 ODS 已有 RETURN）。
- JOIN — `m1.id=m2.order_id`；支付另加 `order_pay_id=pay_id`。

**失败模式**：用小时表直接当「迷你日批」对齐售后 RETURN → 口径漂移；tmp 清成功目标 INSERT 失败 → 当日小时分区空洞；ODS id 碰撞 → 行膨胀。

---

## I. 孤儿 Sensor、小时门控与下游空转

**业务背景**：治理下线 saas/看板/漏斗后易留「create 存活、边已删」；另设允许小时减少非高峰重算。

**实现方式**：活接线 Sensor **25**（含 voucher/settle/store/discount 边）；孤儿 **5**（见 §E）；`start_new_task >> ShortCircuit >> check_allowed_hours_is_run` 与主业务 `start >> …` 并行。

**关键决策点**：
- voucher 边显式依赖 `wait_check_allowed_hours` → 非允许小时 Skip voucher 扇出。
- `wait_ods_user_info_c_all_h` 另有 `start >> wait` 孤边，但仍接入 voucher 列表 → 非孤儿。
- 流量/点击链 **不**经 ShortCircuit → 每小时仍跑。
- dws `wait_check_allowed_hours_is_run` — Dummy SUCCESS≠本小时业务明细已刷新。

**失败模式**：只看 Dummy/孤儿 Sensor 绿误判就绪；允许小时变更未同步文档导致「缺数」工单；注释治理不彻底复制日批孤儿债。

---

## J. 日维商户裸读与 2999 对账

**业务背景**：服务商/provider 需按下单日对齐商户维历史；日批已注释该 JOIN，小时仍保留三段回退。

**实现方式**：mp01 按 `date(create_time)=partition_date`；mp02 锚定 `2025-04-17` 覆盖更早单；mp03 取近 5 日–业务日窗口内 **max(partition_date)** 覆盖「下单日晚于最新可用分区」的缺口。均读 `qpon_dim_d.dim_merchant_basic_info`，**不用** `2999-12-31`。

**关键决策点**：
- 无 `wait_dim_merchant_basic_info`（日）也无接线 `wait_dim_merchant_basic_info_h` → TI 与商户日分区新鲜度脱钩。
- `dim_store_info_h` 仅门店明细链等待；voucher 不用小时门店维。
- `2999-12-31` 出现在 `dwd_store_info_detail_h` 门店有效期哨兵，勿与商品/商户「当前镜像分区」混淆。

**失败模式**：日维当日分区未出齐 → provider 落 mp03 旧分区；误改读 `2999-12-31` 而不评估历史单对齐；恢复看板任务却只接线小时维 Sensor、SQL 仍读日表 → 假门控。

---

> [!SUCCESS] DWD明细小时批 模块深潜闭环验证
> - 扫描范围：1 入口 + Sensor 活 30/接线 25/孤儿 5 + BQ 活 14 + voucher_h SQL + dim_h Skip 对照 + 上游 30/30 仍活 + 下游 Skip
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：181 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：入口与枢纽 SQL 关键路径已确认；无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_dwd_h` **仍**用日工厂 `create_external_sensor`×30 等 `qpon_ods_h`/`qpon_dim_h`（反例未消）；零 Skip。小时 voucher=tmp→目标分区 DELETE+INSERT；**无**售后→RETURN；**活读**日维商户分区路径（非 2999）；订单 JOIN `id=order_id`。孤儿 Sensor×5；上游被 wait task 均仍活；ShortCircuit 仅门控 voucher 扇出；下游 dws/rpt 对本层 Skip。
> - **推演约束 (Constraint)**: 下一模块（dws-h / rpt-h 或收官）必须 (1) 消费本层时坚持 Skip，禁止复制「日工厂等小时」；(2) 勿假设小时/日批 voucher `order_status` 同售后改写语义；(3) 若读本层 SQL 内嵌的日维商户/采购价，须对账日分区新鲜度与 `2999-12-31` 读路径差异，勿只看 dwd_h TI 绿；(4) `check_allowed_hours_is_run` 空转边勿当业务门控。
> - **物理锚点 (Anchors)**: `dags/qpon_dwd_h/qpon_dwd_h.py` L78–99/L147–187/L258–293/L366–375；`tasks/dwd_product_order_voucher_all_h.py` DELETE+INSERT、`m1.id=m2.order_id`、mp01–mp03、order_status 透传；`dags/qpon_dim_h/qpon_dim_h.py` Skip 模板；`dags/airflow_config/create_external_sensor.py` create_external_sensor vs SkipSensor.poke；`dags/qpon_dws_h/qpon_dws_h.py` wait_check_allowed_hours_is_run
