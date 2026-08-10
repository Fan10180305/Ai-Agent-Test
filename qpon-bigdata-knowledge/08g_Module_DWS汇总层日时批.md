# 08g 模块深潜：DWS汇总层日时批（dws-d）

> 模块 id=`dws-d`；权威范围=`dags/`（重点 `dags/qpon_dws_d/` + `dags/qpon_dws_h/`）  
> 不重复 Step05 全量调用链；本步钻取 **汇总增量策略**、**DWD/DIM Sensor 选型**、**设备活跃等代表失败模式**  
> Step08f 接力：(1) 消费小时上游须 Skip，禁止日工厂等小时；(2) 勿假设小时/日批 voucher `order_status` 同售后改写；(3) 日维商户新鲜度 vs `2999-12-31`；(4) `check_allowed_hours_is_run` 为空转 Dummy 边非业务门控  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以 `step-08-dws-d_prompt.md` + 用户指令 id=`dws-d`/suffix=`g` 为准

> [!SUCCESS] DWS汇总层日时批 模块深潜闭环验证
> - 扫描范围：2 入口 DAG（dws_d/dws_h）+ 日 Sensor 23（接线 14 / 孤儿 9）+ 小时 SkipSensor 7（接线 6 / 孤儿 1 / 空转 1）+ 活 BQ 15+3 + 设备活跃/用户订单/门店日特征/小时 feature 代表 SQL + 上游 ods/dim/dwd 活注册抽检
> - 提取结果：8 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：194 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+跨 DAG wait / Step 03 下游=rpt/tag/risk·dwd 倒挂等 device_active / Step 04 实体=`qpon_dws_d.*`（小时写同 dataset `*_h`）
> - EOF 状态：两入口与代表 tasks 关键路径已读至终态；无静默截断

---

## A. 模块定位

`qpon_dws_d`（日批 `0 18 * * *`）与 `qpon_dws_h`（小时 `10 * * * *`）共同构成 **DWS 汇总层日时批**：在 DWD/ODS/DIM 门控后，对设备活跃、用户订单、门店特征、模块活跃与小时特征等做分区重算，写入 dataset `qpon_dws_d`（小时表带 `_h`），供 RPT/TAG/Risk 及少量 DWD 倒挂消费。日批用日工厂 Sensor；小时批对本层上游 **全 Skip**（合规模板），与 `qpon_dwd_h` 反例对照。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_dws_d` / `qpon_dws_d.py` | Orchestrator | 日批 DAG；`create_external_sensor`×23→ods/dwd/dim；活 BQ×15 |
| `qpon_dws_h` / `qpon_dws_h.py` | Orchestrator | 小时 DAG；`create_external_task_skip_sensor_hour`×7→ods_h/dwd_h；BQ×3 feature |
| `create_composer_bq_task` | Factory | 动态 import `qpon_dws_{d\|h}.tasks.<stem>` → BQ SQL |
| `create_external_sensor` | Factory/Sensor | 日批等日上游；success only；retries=1000 |
| `create_external_task_skip_sensor_hour` | Factory/Sensor | 小时等小时上游；透传 SUCCESS/SKIPPED/FAILED |
| `dws_qpon_device_active_info_inc_d` / `*_all_d` | Executor | 设备日活增量 + 滚动全量（位图） |
| `dws_user_order_inc_d` / `dws_store_daily_feature_d` / `dws_store_merchant_cnt_inc_d` | Executor | 订单/门店汇总（读日批 voucher） |
| `dws_feature_*_{d\|h}` | Executor | 用户/门店/内容特征日批与小时批 |
| `qpon_dwd_d` / `qpon_ods_d` / `qpon_dim_d` | Upstream | 被日批 Sensor 等待 |
| `qpon_dwd_h` / `qpon_ods_h` | Upstream | 被小时 SkipSensor 等待 |
| `qpon_rpt_d` / `qpon_tag_d` / `qpon_dwd_d` | Downstream Caller | 等本层 device_active / store_feature 等 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_dws_d` parse | Composer | 注册日汇总与跨 DAG Sensor |
| DAG `qpon_dws_h` parse | Composer | 注册小时 feature 与 SkipSensor |
| `create_composer_bq_task(..., stem)` | 两入口 | 绑定 `warehouse_layer` + stem |
| `create_external_sensor(..., qpon_ods_d\|dwd_d\|dim_d, …)` | `qpon_dws_d.py` | 日批门控；仅 SUCCESS |
| `create_external_task_skip_sensor_hour(..., qpon_dwd_h\|ods_h, …)` | `qpon_dws_h.py` | 小时门控；透传 SKIPPED |
| `send_failure_alert_factory(send_url)` | 多数 callback | 硬编码 yzjtoken（继承 08a） |
| `dws_qpon_device_active_info_inc_d()` / `*_all_d()` | BQ Operator | 日活 DELETE+INSERT（+ADJUST UPDATE）/ 全量滚写真 |
| 下游 `create_external_sensor(..., qpon_dws_d, …)` | rpt/tag/dwd | 日工厂等本层汇总 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 设备活跃：`start` → `wait_dwd_qpon_adjust_raw_adid_all_d` → `dws_qpon_device_active_info_inc_d` →（+`wait_ods_digital_food_device`）→ `*_all_d`（`05` §A.7）。
- 订单/门店：`wait_dwd_product_order_voucher_all`（+dim/ods）→ `dws_user_order_inc_d` / `dws_store_merchant_cnt_inc_d` / `dws_store_daily_feature_d` / `dws_feature_*_d`。
- 小时特征：`start` → SkipSensor→`qpon_dwd_h`/`qpon_ods_h` → `dws_feature_{user,content,store}_info_h`；并行 `start_new_task >> wait_check_allowed_hours_is_run` 空转。
- 下游：`qpon_rpt_d`/`qpon_tag_d` 等 device_active；`qpon_dwd_d` 层倒挂等本层（C-05-05）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；跨 DAG wait | ✅；日孤儿 Sensor×9；小时孤儿×1 |
| 03 下游 | rpt/tag/risk 等 DWS；dwd 倒挂 device_active | ✅ |
| 04 实体 | `qpon_dws_d.*`；小时写同 dataset `*_h` | ✅ |
| 06 异步 | 日 Sensor retries=1000；小时 Skip；空转边 | ✅ 空转仍在 |
| 07 配置 | TT 硬编码；Sensor timeout 继承工厂 | ✅ |

**08f 接力四项（本步审计结论）**：
1. **Skip 合规**：`qpon_dws_h` 活 wait **全** `create_external_task_skip_sensor_hour`（×7）；**零**日工厂等 `qpon_ods_h`/`qpon_dwd_h`。`qpon_dws_d` Sensor **零**指向 `*_h` DAG。合规模板成立；禁止回退复制 `qpon_dwd_h` 反例。
2. **order_status**：日批消费 `dwd_product_order_voucher_all` 的完单链（`dws_user_order_inc_d`/`dws_store_merchant_cnt_inc_d`/`dws_store_daily_feature_d`）过滤 `COMPLETED`+`RETURN`——依赖日批售后改写。小时 `dws_feature_user_info_h` 对 `*_voucher_all_h` **同样**用 `COMPLETED`+`RETURN` 算完单差，但小时枢纽**无**售后→RETURN（08f）→ **同过滤字面量、不同上游语义**。
3. **商户维路径**：`dws_user_order_inc_d` 读 `dim_merchant_basic_info` **业务日分区**；`dws_store_daily_feature_d` 商户档位/`serving_tag` 读 **`2999-12-31`**。均有或可有 `wait_dim_merchant_basic_info`，**TI 绿≠已声明读哪条路径**。
4. **空转边**：`wait_check_allowed_hours_is_run` 仅 `start_new_task >> wait`，**未**接入三条 `dws_feature_*_h` → Dummy SUCCESS≠业务就绪（与 Step06 一致）。

接线上游抽检：日批 wired ODS/DWD/DIM task 在对应入口仍 create+`>>`；小时 Skip 目标在 `qpon_dwd_h`/`qpon_ods_h` 仍活。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08g-01 | 等 `qpon_ods_h`/`qpon_dwd_h`/`qpon_dim_h`：必须用 `create_external_task_skip_sensor_hour`；**禁止**对本包新增日工厂 `create_external_sensor`(retries=1000) 套小时 DAG；现网 dws_h 已合规，禁止回退 | `qpon_dws_h` Skip×7 vs `qpon_dwd_h` 反例 | Skip 语义丢；重试风暴 |
| C-08g-02 | 日批 DWS 分区表幂等键=`partition_date`（业务日=`execution_date+1`，explore 例外见 C-08g-08）；须先 DELETE 目标分区再 INSERT；禁止漏删叠写 | 多数 `dws_*_inc_d` DELETE+INSERT | 分区重复/脏快照 |
| C-08g-03 | 小时 feature 幂等键=`partition_date`+`hour_no`（UTC+7=`execution+7h`）；须按日+小时双谓词 DELETE 再 INSERT | `dws_feature_*_h` DELETE | 同日多小时串写 |
| C-08g-04 | 消费 voucher 完单口径时：日批表可认售后改写后的 `RETURN`；小时表**勿**假设同语义；改过滤须双批对账（已知口径分裂债） | `dws_user_order_inc_d` vs `dws_feature_user_info_h` | 小时/日完单、毛收漂移 |
| C-08g-05 | 读 `dim_merchant_basic_info`/`dim_product_basic_info` 须声明日分区还是 `2999-12-31`；勿只看 Sensor TI 绿 | `dws_user_order_inc_d` 日分区；`dws_store_daily_feature_d` 2999 | 档位/佣金错读 |
| C-08g-06 | `check_allowed_hours_is_run` **不得**当业务门控；禁止新增仅挂 `start_new_task`、不接 feature 的同类空转边（已知技术债） | `qpon_dws_h` L127 vs L132–148 | 假就绪/空占槽 |
| C-08g-07 | `dws_qpon_device_active_info_inc_d` 主源为 `dwd_qpon_event_traffic_inc_d`（SQL 裸读）；新增/改调度须补 Sensor 或头注释「不挂依赖」；禁止假装 adjust wait=流量已就绪 | inc 仅 wait adjust；SQL 读 traffic | TI 绿但日活空/旧 |
| C-08g-08 | `dws_explore_page_device_first_visit_d` 分区锚=`execution_date`（非 +1）且无上游 Sensor；改日历偏移或补依赖须单独评估（已知特例债） | explore `add(days=-1)`；`start>>` 裸跑 | 错日窗/陈旧埋点 |
| C-08g-09 | 禁止新增 dwd→dws 层倒挂 Sensor；现网 `qpon_dwd_d.wait_dws_qpon_device_active_*` 为已知技术债，新增禁止复制 | `qpon_dwd_d` → `qpon_dws_d` | 调度环/竞态 |

---

## G. 汇总增量策略

**业务背景**：DWS 把明细压成「日活/全量滚动/订单日增/门店日特征/小时特征」，供标签与看板；策略以分区覆盖为主，少数带后置 UPDATE 或滑动清理。

**实现方式**：

| 模式 | 代表任务 | 键与写策略 |
|---|---|---|
| 日分区覆盖 | `dws_user_order_inc_d`、`dws_store_merchant_cnt_inc_d`、`dws_feature_*_d`、`dws_app_module_active_inc_d` | DELETE `partition_date=业务日(+1)` → INSERT |
| 日活+渠道回填 | `dws_qpon_device_active_info_inc_d` | DELETE+INSERT 当日；再 UPDATE 近 3 日 `last_adjust_id`←adjust 表 |
| 滚动全量 | `dws_qpon_device_active_info_all_d` | 读昨日全量 ∪ 今日增量；位图左移补 0/1；DELETE+INSERT 当日全量分区 |
| 滑动保留 | `dws_performance_monitoring_inc_d` | DELETE 当日 **或** ≤业务日−14 天 → INSERT |
| 小时切片 | `dws_feature_*_h` | DELETE 业务日+`hour_no` → INSERT；写 `qpon_dws_d.*_h` |
| 特例锚日 | `dws_explore_page_device_first_visit_d` | 经 tmp 聚合；锚 `execution_date`（非 +1） |

**关键决策点**：
- `dws_qpon_device_active_info_all_d` — 有昨日设备且今日无活 → 位图末位补 0 滚入；今日新活 → 与昨日合并累计注册/登录。
- `dws_user_order_inc_d` — 下单窗=`date(create_time)=业务日`；完单窗=`order_status∈{COMPLETED,RETURN}` ∧ `date(order_pay_time)=业务日`。
- `dws_store_daily_feature_d` — 护栏（销量/品数/图数）触发则规格分归零；好店池按商户档位 topN。
- `dws_feature_*_h` — `prev_hour_partition=execution+7h` 对齐业务时区小时。

**失败模式**：漏 DELETE → 分区叠行；all 依赖 inc 失败则全量停；performance 误改 14 日谓词 → 历史被清或残留；小时漏 `hour_no` 谓词 → 同日他小时被删。

---

## H. DWD/DIM Sensor 选型

**业务背景**：日批上游无 Skip 语义，用日工厂 Sensor；小时上游可 ShortCircuit/Skip，须 SkipSensor 透传。本模块日/时选型正确，是对照 `qpon_dwd_h` 反例的正面样本。

**实现方式**：
- 日：`create_external_sensor`×23 → `qpon_ods_d`(9)+`qpon_dwd_d`(10)+`qpon_dim_d`(4)；接线 14 / 孤儿 9（随 evil/poi/红包/邀请链注释遗留）。
- 时：`create_external_task_skip_sensor_hour`×7 → `qpon_dwd_h`(6)+`qpon_ods_h`(1)；孤儿 `wait_dwd_product_place_order_source_inc_h`；空转 `wait_check_allowed_hours_is_run`。
- 入口 import 了日工厂但小时**未调用**。

**关键决策点**：
- `qpon_dws_d` — 仅等日 DAG → 允许日工厂 Sensor。
- `qpon_dws_h` — 等小时 DAG → **必须** Skip（已落实）。
- `wait_dim_merchant_basic_info` — 门控≠SQL 读日分区或 2999（见 §J）。
- 孤儿 Sensor SUCCESS ≠ 任何汇总已刷新。

**失败模式**：把 dws_h 改回日工厂等 dwd_h → 与上游反例叠加重试风暴；恢复已下线 BQ 却只复活孤儿 Sensor、未 `>>`；误把空转 Skip 当 voucher 窗口门控。

---

## I. 设备活跃与代表失败模式

**业务背景**：`dws_qpon_device_active_info_{inc,all}_d` 是标签/报表高读枢纽；inc 从埋点聚日活，all 滚 31 位日/周/月位图。编排与 SQL 依赖不对齐是主风险。

**查数口径（权威）**：APP / H5 等各环境「活跃设备数 / DAU」统一读 `qpon_dws_d.dws_qpon_device_active_info_inc_d`（`host_environment` + `COUNT(DISTINCT uni_device_id)` + `partition_date`）。派生报表（如 `rpt_dau_report_inc_d` / `rpt_app_user_statistic_v3`）仅可交叉核对，不作首选源；`*_all_d` 仅用于位图/留存窗，勿与日活设备数混口径。

**实现方式**：inc 入口仅 wait `dwd_qpon_adjust_raw_adid_all_d`；SQL 主读 `dwd_qpon_event_traffic_inc_d`（`data_type=clientele_h5`/`env=prod`），并裸读 `ods_user_info_c_all_h`、`dim_qpon_source_tag_all`；后置 UPDATE 用 adjust 回填近 3 日渠道。all wait inc + `ods_digital_food_device`；SQL 另裸读 `dim_daytime_info`（该 wait 仅接到 `dws_app_module_active_inc_d`）。

**关键决策点**：
- `dws_qpon_device_active_info_inc_d` — Sensor 绿仅保证 adjust；流量/注册小时表无 wait。
- `is_first_push_click` — 首事件与首 `push_click` 间隔 <3s → 1。
- `dws_qpon_review_event_inc_d` — `start >>` 无 Sensor，直接滤 traffic 评价事件（同类裸跑）。
- 下游 dwd 倒挂等 inc/all → DWS 延迟反压 DWD 用户链。

**失败模式**：
1. traffic 未出齐但 adjust 已成功 → inc TI 绿、日活偏少；标签/RPT 连锁偏低。
2. UPDATE 段失败而 INSERT 成功 → 渠道字段空、活跃行在。
3. all 昨日分区缺失 → 位图断裂/设备丢失。
4. 误删 inc→all 边或并行化 → 全量读到半新增量。

---

## J. 商户维路径、voucher 状态与空转边

**业务背景**：接力要求显式区分商户「日分区新鲜度」与「2999 当前镜像」，以及小时/日 voucher 状态语义；小时 Dummy 边不得冒充业务门控。

**实现方式**：
- 佣金：`dws_user_order_inc_d` ← `dim_merchant_basic_info` **where partition_date=业务日**（平台扣点）。
- 档位/用餐标签：`dws_store_daily_feature_d` ← 同表 **`2999-12-31`**（+商品维 2999）。
- 完单过滤：日汇总与小时 feature 字面量皆含 `RETURN`，上游语义见 08e/08f。
- 空转：`DummyOperator.check_allowed_hours_is_run` ← dws_h Skip 等待；feature 链不依赖。

**关键决策点**：
- `wait_dim_merchant_basic_info` SUCCESS — 仅表示维任务跑完，不绑定 SQL 分区谓词。
- 小时 feature 读无分区 `dim_store_info` 全表 — 无对应日维 Sensor。
- ShortCircuit 在 **dwd_h** 门控 voucher；dws_h 不重复门控。

**失败模式**：改商户维只刷 2999 不刷日分区 → 用户订单毛收错、好店档位仍「绿」；用小时 voucher 的 `COMPLETED` 对售后成功单当完单；运维以为等 `check_allowed_hours_is_run` 即可认为特征已按窗口产出。

---

> [!SUCCESS] DWS汇总层日时批 模块深潜闭环验证
> - 扫描范围：2 入口 + 日 Sensor 23/接线 14/孤儿 9 + 小时 Skip 7/接线 6/孤儿 1/空转 1 + BQ 活 15+3 + 代表 SQL（device_active/user_order/store_feature/feature_h）+ 上游抽检
> - 提取结果：8 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：194 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：两入口与代表 SQL 关键路径已确认；无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_dws_h` **已**全量 Skip 等 `qpon_dwd_h`/`qpon_ods_h`（正面样本）；`qpon_dws_d` 无日工厂等小时。设备活跃 inc **仅** wait adjust、主读 traffic 裸读；all=昨日全量∪今日增量位图。日汇总完单认 `COMPLETED`+`RETURN`（依赖日批售后改写）；小时 feature 对 voucher_h 用同过滤但上游无 RETURN 改写。商户维：`user_order`=日分区、`store_daily_feature`=2999。`wait_check_allowed_hours_is_run` 仍空转。孤儿：日×9、小时 place_order_source×1。下游 rpt/tag 等 device_active；dwd→dws 倒挂仍在。
> - **推演约束 (Constraint)**: 下一模块（rpt-d / rpt-h / tag 或收官）必须 (1) 消费小时上游坚持 Skip，禁止复制 dwd_h「日工厂等小时」；(2) 读 DWS/日 voucher 完单时勿与小时 voucher_h `order_status` 混口径；(3) 读本层或上游 SQL 内嵌的商户/商品维须对账日分区 vs `2999-12-31`；(4) 勿把 `check_allowed_hours_is_run` 或孤儿 Sensor 当业务就绪；(5) 评估 device_active 裸读 traffic 与 dwd→dws 倒挂对报表/标签 SLA 的放大效应。
> - **物理锚点 (Anchors)**: `dags/qpon_dws_d/qpon_dws_d.py` L118–156/L233–343；`dags/qpon_dws_h/qpon_dws_h.py` L90–148；`tasks/dws_qpon_device_active_info_inc_d.py` DELETE+INSERT+UPDATE、裸读 traffic；`tasks/dws_qpon_device_active_info_all_d.py` 位图滚动；`tasks/dws_user_order_inc_d.py` 日分区商户+COMPLETED/RETURN；`tasks/dws_store_daily_feature_d.py` 2999 档位；`tasks/dws_feature_user_info_h.py` voucher_h+COMPLETED/RETURN；`dags/qpon_dwd_d/qpon_dwd_d.py` wait_dws_device_active 倒挂
