# 08e 模块深潜：DWD明细日批（dwd-d）

> 模块 id=`dwd-d`；权威范围=`dags/`（重点 `dags/qpon_dwd_d/`；**本步仅日批**，小时批留给 dwd-h）  
> 不重复 Step05 全量调用链；本步钻取 **`dwd_product_order_voucher_all` 分区重算**、**状态字段决策**、**ODS/DIM Sensor**、**ES 旁路**  
> Step08d 接力：核对 wait 的 dim 是否仍活接线；禁止日工厂 Sensor 等小时维/贴源；结算/商品维须对账分区与 `2999-12-31`；订单 JOIN 勿假设 ODS MERGE ON `id` 跨分表唯一

> [!SUCCESS] DWD明细日批 模块深潜闭环验证
> - 扫描范围：1 入口 DAG + 活接线 Sensor 56 + 孤儿 Sensor 16 + 活 BQ 58（孤儿 BQ 1）+ 枢纽 `dwd_product_order_voucher_all` SQL + ES 注释旁路 + 上游 dim/ods/dws 活注册核对
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：176 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+跨 DAG wait / Step 03 下游=rpt/dws/tag 等 voucher / Step 04 实体=`qpon_dwd_d.dwd_product_order_voucher_all`
> - EOF 状态：`qpon_dwd_d.py` 与枢纽 voucher SQL 已读至关键终态；无静默截断

---

## A. 模块定位

`qpon_dwd_d`（日批 `0 18 * * *`）是 **DWD 明细日批枢纽**：以 `create_external_sensor` 门控 ODS/DIM（及少量 DWS）后，对订单券/门店商品/搜索/营销等事实做分区 DELETE+INSERT（或等价重算），写入 dataset `qpon_dwd_d`；枢纽任务 `dwd_product_order_voucher_all` 扇出至财务/核销/首单/结算等下游。本包日批**无**对 `qpon_ods_h`/`qpon_dim_h` 的 Sensor；ES 旁路已整链注释迁出。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_dwd_d` / `qpon_dwd_d.py` | Orchestrator | DAG 默认参数、TT callback、TimeDelta、Sensor×72（接线 56）、BQ 扇出与 `>>` |
| `create_composer_bq_task` | Factory | 动态 import `qpon_dwd_d.tasks.<stem>` → BQ SQL |
| `create_composer_python_task` | Factory | ES Python 旁路；**现网活注册=0**（20260709 注释） |
| `create_external_sensor` | Factory/Sensor | 日批等 ODS/DIM/DWS；`allowed_states=['success']`；retries=1000 |
| `TimeDeltaSensor`（`wait_2_hours` / `wait_12_hour_20_minute`） | Sensor | Adjust / 财务链延时门；retries=1000 |
| `dwd_product_order_voucher_all` | Executor | 订单×券明细全日快照分区重算（枢纽） |
| `dwd_product_*` / `dwd_store_info_detail_d` / `dwd_settle_*` 等 | Executor | 财务、门店明细、结算、搜索、设备活跃衍生等 |
| `*_to_es`（文件仍在 `tasks/`） | Bypass（失活） | Cloud Run 写阿里云 ES；入口与 `>>` 已注释，迁 `qpon_data_server_d` |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_dwd_d` parse | Composer | 注册日批明细与跨 DAG Sensor |
| `create_composer_bq_task(..., stem)` | `qpon_dwd_d.py` | 绑定 `warehouse_layer=qpon_dwd_d.tasks` |
| `create_external_sensor(..., qpon_ods_d\|qpon_dim_d\|qpon_dws_d, …)` | 入口 | 日批门控；仅 SUCCESS |
| `send_failure_alert_factory(send_url)` | 多数任务 callback | 硬编码 yzjtoken（继承 08a） |
| `dwd_product_order_voucher_all()` | BQ Operator | 返回 DELETE+INSERT SQL |
| `TimeDeltaSensor.wait_*` | 入口依赖边 | 延时后再等 ODS Adjust / 结算规则 |
| `create_composer_python_task(*_to_es)` | **已注释** | 历史 ES 旁路入口 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 枢纽：`start` → 多 `wait_ods_*` + `wait_dim_store_info`/`wait_dim_merchant_basic_info` + 采购价前置任务 → `dwd_product_order_voucher_all` → finance/consume/first_order/gtv/settle 等（`05` §A.3 / 入口 L710–728、L681+）。
- 层倒挂：`wait_dws_qpon_device_active_info_*` → 用户活跃/砍价/留存等（已知技术债，C-05-05）。
- 下游跨 DAG：`qpon_rpt_d` / `qpon_dws_d` / `qpon_tag_d` 等 wait 本层（尤其 voucher）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；Sensor `external_dag_id/task_id` | ✅；孤儿 Sensor×16 + 孤儿 BQ `dwd_app_search_query_qv_inc_d` |
| 03 下游 | rpt/tag/risk 读 `qpon_dwd_d`；ES 曾 4 条 to_es | ✅；入口 ES 链已注释，tasks 文件仍在 |
| 04 实体 | voucher 179 字段、`partition_date` 日覆盖 | ✅；全日快照写入当日分区（见 §G） |
| 06 异步 | 日 Sensor retries=1000；TimeDelta retries=1000 | ✅；**无**日工厂等小时 DAG |
| 07 配置 | TT 硬编码；Sensor timeout 64800 | ✅ 继承 |

**08d 接力四项**：
1. **dim 活接线**：接线 wait 的 dim=`dim_daytime_info` / `dim_store_info` / `dim_merchant_basic_info` / `dim_store` / `dim_coupon_template` —— 在 `qpon_dim_d` **均仍 create+`>>` 活接线**（MISSING=0）。`wait_dim_product_basic_info` **仍 create 但无 `>>`（孤儿）**，随 ES 商户看板注释遗留。
2. **禁止日工厂等小时**：本包 Sensor **零**指向 `qpon_ods_h`/`qpon_dim_h`；合规模板对照 `qpon_dim_h` Skip。小时表被 SQL **裸读**（无 Sensor）：`ods_user_info_c_all_h`、`ods_settle_clear_detail_info_all_h`、`dwd_product_place_order_source_inc_h`、`rpt` 折扣小时表。
3. **分区 vs 2999**：voucher **不读** `dim_product_basic_info`/`dim_merchant_basic_info` 分区或 `2999-12-31`（商户维 JOIN 已注释）；门店取自 **无分区** `dim_store_info` TRUNCATE 全表。仍 `wait_dim_merchant_basic_info` 仅作调度门控——**TI 绿≠本 SQL 已消费商户分区/2999**。结算佣金优先 `ods_settle_clear_detail_info_all_h`（裸读小时）。
4. **订单 JOIN**：`ods_t_life_order_all_d`/`item`/`voucher` 等 ODS MERGE **仅 ON `id`**；voucher 用 `m1.id=m2.order_id`、`m2.order_item_id=m7.order_item_id`——**禁止**把跨分表 `id` 当全局唯一业务前提。

接线 ODS/DWS 上游活注册：**56/56 MISSING=0**（ods stems 含单双引号注册共 124）。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08e-01 | 日批等 ODS/DIM：用 `create_external_sensor`；**禁止**对本包新增 `create_external_sensor` 指向 `qpon_ods_h`/`qpon_dim_h`——以 `qpon_dim_h` Skip 为小时模板；`qpon_dwd_h` 日工厂等小时为已知技术债，禁止复制 | `qpon_dwd_d` 无 `_h` Sensor vs `qpon_dwd_h` | Skip 语义丢失；重试风暴 |
| C-08e-02 | `dwd_product_order_voucher_all` 幂等键=`partition_date`（业务日=`execution_date+1`）；必须先 `DELETE` 当日分区再 `INSERT`；禁止改成无分区全表覆盖或漏删叠写 | `dwd_product_order_voucher_all` DELETE+INSERT | 分区重复/脏快照 |
| C-08e-03 | 订单券 JOIN 须显式业务键（order_id/order_item_id/voucher_id）；**禁止**假设 ODS `MERGE ON id` 跨分表唯一；新增同类 JOIN 须评估分表碰撞（已知技术债） | `ods_t_life_order*_all_d` ON id；voucher `m1.id=m2.order_id` | 错绑订单行/金额翻倍 |
| C-08e-04 | `order_status`：`COMPLETED` 且售后 `AFTER_SALE_SUCCESS` → 写成 `RETURN`；首单完单统计只认 `COMPLETED`/`RETURN`+`is_formal=1`；禁止静默改映射而不改下游过滤 | voucher CASE + first_finish QUALIFY | GTV/首单口径漂移 |
| C-08e-05 | 下线任务须同时注释工厂 create、全部 `wait_*`、全部 `>>`；禁止只注释 BQ/`>>` 留下活 Sensor（现网孤儿×16 为已知技术债，含 `wait_dim_product_basic_info`） | ES/售后/线索等注释块 vs 活 create | 空跑 Sensor、误等已下线依赖 |
| C-08e-06 | 禁止新增 dwd→dws 层倒挂 Sensor；现网 `wait_dws_qpon_device_active_info_*` 为已知技术债，新增禁止复制 | `qpon_dwd_d` → `qpon_dws_d` | 调度环/竞态 |
| C-08e-07 | SQL 裸读小时表（`*_h`）必须在任务头注释「不挂依赖」并评估新鲜度；禁止假装已有日批 Sensor 门控 | voucher 依赖注释块 L1221–1229 | TI 绿但归因/结算字段陈旧 |
| C-08e-08 | 消费 `dim_merchant_basic_info`/`dim_product_basic_info` 时须明确读日分区还是 `2999-12-31`；勿只看 Sensor TI 绿；本枢纽 wait 商户但不读其表属已知耦合债 | 08d C-08d-04；voucher 注释 mp01–mp03 | 当前镜像/历史分区错读 |
| C-08e-09 | ES 旁路已迁 `qpon_data_server_d`：禁止在本 DAG 恢复 `*_to_es` 而不同步删除 data_server 双写；tasks 残留文件不可当活入口 | 入口 L417–427 / L1019–1031 注释 | 双写冲突或漏写 ES |

---

## G. 枢纽分区重算：`dwd_product_order_voucher_all`

**业务背景**：订单券宽表是仓内最高读写事实之一（Step04）；日批把「全量订单×商品×支付×券×核销×归因」落成 **按业务日分区的全日快照**，供 RPT/TAG/财务扇出。

**实现方式**：
1. `DELETE … WHERE partition_date = 业务日`；`INSERT` 全结果集且 `partition_date` 恒打业务日戳。
2. 驱动源 `ods_t_life_order_all_d` **无**源分区过滤（读合并全表）→ 每跑重算「截至当前 ODS 全量」写入**当日分区**（非「仅当日下单增量」）。
3. 商品/SKU/库存侧用 ODS **当日分区**；门店维 `dim_store_info` 全表聚合；采购价来自同 DAG 前置 `dwd_product_procurement_price_order_*`。

**关键决策点**：
- `dwd_product_order_voucher_all` — 删写目标分区 = `execution_date+1` → 与 ODS/DIM 业务日对齐。
- 入口依赖 — 须等采购价两项完成再跑 voucher → 佣金/采购价链路。
- 金额 — `pay_reality_amount` 优先；`create_time≤2025-12-01` 可回退支付表 `pay_price`/`pay_fee_amount`。
- 佣金激励 — 结算清分小时表 > 采购价比例推算 > 券表字段。

**失败模式**：
1. DELETE 成功 INSERT 失败 → 当日分区空洞，下游扫空。
2. ODS 订单 MERGE 碰撞 / item 重复 → 宽表行膨胀，财务偏高。
3. 未等采购价任务 → voucher 仍可能跑（若改边）导致采购价空、佣金回退错误。
4. 只看任务绿：裸读小时归因/清分未就绪 → 渠道/佣金字段陈旧但 TI SUCCESS。

---

## H. 状态与正式单字段决策

**业务背景**：下游用 `order_status` / `is_formal` / `is_first_*` / `is_pay` / `is_voucher_id` / `is_consume` 过滤正式 GMV 与漏斗；售后成功须从完单改写为退单口径。

**实现方式**：在 `order_voucher_all` CTE 内 CASE/IF 派生，外层再算首单标记。

**关键决策点**：
- `order_status` — `COMPLETED` ∧ 售后表 `status='AFTER_SALE_SUCCESS'` → `'RETURN'`；否则保留 ODS 原状态（SUBMIT/COMPLETED/CANCEL/…）。
- `is_formal`（订单）— 排除测试 user_id 名单、`shadow_flag<>'MOCK'`、且商品侧 `is_formal=1`。
- 商品 `is_formal` — 名称非测试/验证、商户不在测试名单、`dim_store` 商户正式、且不在 `dim_test_product_id`。
- `is_first_finish_order` — 正式单且状态∈{COMPLETED,RETURN}，按 `user_id`+`order_pay_time` 首次。
- `is_first_place_order` — 正式单按 `create_time` 首次（整数 0/1）。
- `is_pay` / `is_voucher_id` / `is_consume` — 支付/券/核销行是否命中。

**失败模式**：售后源表 `digital_food_market.t_life_after_sale_order` **无 Sensor**（直连源库）→ 延迟或空导致完单未改 RETURN；测试名单硬编码漏更 → 正式口径污染；下游仍过滤 `COMPLETED` 不含 `RETURN` → 退单后指标断裂。

---

## I. ODS/DIM Sensor 与孤儿边

**业务背景**：日批用统一工厂挂上游就绪；治理下线大量任务后易留下「create 存活、`>>` 已删」的空转 Sensor。

**实现方式**：`create_external_sensor` → `ExternalTaskSensor`（success only，retries=1000，timeout=64800）。TimeDelta 用于 Adjust（+2h）与财务明细（+10h20m，task_id 名 `wait_12_hour_20_minute`）。

**关键决策点**：
- 活接线 Sensor **56**；孤儿 **16**（售后×5、品牌页×3、评价×2、线索×3、招商×2、`wait_dim_product_basic_info`×1）。
- 孤儿 BQ：`dwd_app_search_query_qv_inc_d` create 无 `>>`。
- 治理已双侧注释的示例：`wait_ods_t_act_award_record`、`wait_dim_search_id_text_inc_d`、`wait_dim_activity_basic_info`（create 亦注释）——可作下线模板。
- **无**对小时 DAG 的日工厂 wait（本步合规）；小时数据靠 SQL 裸读。

**失败模式**：孤儿 Sensor 单独 SUCCESS ≠ 任何明细已刷新；dwd→dws Sensor 在 DWS 延迟时阻塞用户活跃链；上游 ODS failed → Sensor 重试风暴占槽（08a/06）。

---

## J. ES 旁路（迁出态）

**业务背景**：商户看板/券卡/招商活动等曾 BQ→Cloud Run→阿里云 ES；20260709 注释称合并入 `qpon_data_server_d`。

**实现方式（现网）**：入口内 `dwd_market_activity_dashboard_data_inc_d(_to_es)`、`dwd_recruit_*_to_es`、`dwd_merchant_daily_performance(_to_es)`、`dwd_merchant_daily_coupon_card_data(_to_es)` **整链注释**；`tasks/*_to_es.py` 文件仍实现 `access_cloud_run_write_aliyun_es`（失败分 `AirflowFailException` / 可重试）。

**关键决策点**：
- 入口 — 活 `create_composer_python_task` **=0** → Composer 本 DAG 不再写 ES。
- 历史依赖 — performance 链曾 wait `dim_store_info`+`dim_product_basic_info`+voucher；coupon 链仅 wait `dim_product_basic_info`（故遗留孤儿 Sensor）。

**失败模式**：误以为 `tasks/*_to_es.py` 仍被调度；在 data_server 与本 DAG 同时恢复 → ES 双写；Cloud Run/`print` 凭据债仍继承 08a（文件级）。

---

> [!SUCCESS] DWD明细日批 模块深潜闭环验证
> - 扫描范围：1 入口 + Sensor 活 56/孤儿 16 + BQ 活 58/孤儿 1 + voucher 枢纽 SQL + ES 注释旁路 + dim/ods/dws 上游核对
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：176 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅（ES 迁出） / Step 04 ✅
> - EOF 状态：入口与枢纽 SQL 关键路径已确认；无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_dwd_d` 日批枢纽=ODS/DIM Sensor→BQ；**无**日工厂等小时 DAG。voucher=`DELETE+INSERT` 全日快照入业务日分区；`COMPLETED+售后成功→RETURN`；订单 ODS MERGE 仅 ON `id`。接线 dim×5 仍活；`wait_dim_product_basic_info` 孤儿；孤儿 Sensor×16；ES 四链已注释迁 data_server；仍 dwd→dws×2；SQL 裸读多张 `*_h`。
> - **推演约束 (Constraint)**: 下一模块（dwd-h）必须 (1) **禁止复制**「日工厂 `create_external_sensor` 等 `qpon_ods_h`/`qpon_dim_h`」——以 `qpon_dim_h` Skip 为模板；(2) 小时订单 JOIN 同样勿假设 MERGE ON `id` 跨分表唯一；(3) 核对所 wait 的上游 task 是否仍活接线（对照本包孤儿治理）；(4) 若读日维商品/商户，须对账分区与 `2999-12-31`，勿只看 TI 绿。
> - **物理锚点 (Anchors)**: `dags/qpon_dwd_d/qpon_dwd_d.py` L126–241/L282/L417–427/L710–728/L1019–1031；`tasks/dwd_product_order_voucher_all.py` DELETE+INSERT、order_status CASE、L1221–1229 裸读小时注释；`dags/qpon_ods_d/tasks/digital_food_market_0_3/ods_t_life_order_all_d.py` MERGE ON id；`dags/qpon_dim_h/qpon_dim_h.py` Skip 模板；`dags/qpon_dwd_h/qpon_dwd_h.py` 反例（日工厂等小时）
