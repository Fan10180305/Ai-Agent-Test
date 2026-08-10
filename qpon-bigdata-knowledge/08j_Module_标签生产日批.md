# 08j 模块深潜：标签生产日批（tag-d）

> 模块 id=`tag-d`；权威范围=`dags/`（重点 `dags/qpon_tag_d/`；`qpon_tag_d_test` 仅对照，不写为生产事实）  
> 不重复 Step05 全量调用链；本步钻取 **宽表写入**、**tag_qpon_metadata.latest_dayno**、**ODS/DWD/RPT(无)/DIM/DWS Sensor**、**多任务同表冲突**、**device_active 扇出**  
> Step08i 接力：(1) 小时上游坚持 Skip；(2) 日批 voucher RETURN ≠ 小时透传；(3) 商户/商品维日分区 vs `2999`；(4) 孤儿/ES 吞异常非就绪；(5) device_active 扇出主战场在 tag/日批 rpt  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以 `step-08-tag-d_prompt.md` + 用户指令 id=`tag-d`/suffix=`j` 为准

> [!SUCCESS] 标签生产日批 模块深潜闭环验证
> - 扫描范围：1 入口 DAG（862 行）+ 日工厂 Sensor 23（全接线 / 孤儿 0）+ 活 BQ 140 + 代表 SQL（active/orders/base/merchant/store/mapping）+ 小时表裸读抽检 26 + 仓内下游引用（仅 test）
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：171 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+日工厂 Sensor / Step 03 下游=仓内无生产消费方（仅 test） / Step 04 实体=`qpon_services_prod.tag_qpon_*`+metadata
> - EOF 状态：入口与代表 tasks 已读至终态；无静默截断

---

## A. 模块定位

`qpon_tag_d`（`0 18 * * *`）是 **标签生产日批**：在 ODS/DWD/DWS/DIM/analyst 日工厂 Sensor 门控后，按 `tag_name`（或 BASE/ID_MAPPING）向 dataset `qpon_services_prod` 的设备/用户/商户/门店宽表做 `DELETE(dayno[,tag_name])+INSERT`，并 `MERGE tag_qpon_metadata.latest_dayno` 水位。无 ES、无 Skip、无指向 `*_h` DAG 的 Sensor；但多条 SQL **裸读** 小时表——与「等小时须 Skip」是不同风险面。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_tag_d` / `qpon_tag_d.py` | Orchestrator | 日批入口；Sensor×23；BQ×140；Dummy `start`/`start_new_task` |
| `create_composer_bq_task` | Factory | 动态 import `qpon_tag_d.tasks[.app_tag\|app_order\|app_active].<stem>` |
| `create_external_sensor` | Factory/Sensor | 等 `qpon_ods_d`/`qpon_dwd_d`/`qpon_dws_d`/`qpon_dim_d`/`qpon_analyst_d` SUCCESS（retries=1000） |
| `tag_qpon_base_*_all_d` / `tag_qpon_qponid_userid_latest` | Executor | 实体底座 + 设备-用户映射；写 base/latest 表并 MERGE 元数据 |
| `app_*` / `h5_*` / `active_uid_*` / `DAY*` / `user_*` | Executor | 设备/用户标签扇出；主写 `tag_qpon_all_d` / `tag_qpon_userid_all_d` |
| `Merchant_*` / `store_*` / `Store_*` | Executor | 商户/门店标签；写 `tag_qpon_merchant_all_d` / `tag_qpon_store_all_d` |
| `app_tag` / `app_order` / `app_active` 子包 | Executor | 沉默/订单计数/末次版本等扩展标签 |
| `qpon_tag_d_test` | Test Orchestrator | 生产镜像子集；**非**生产权威 |
| （无仓内生产 Downstream Caller） | — | `dags/` 内仅 test 包自引用 `qpon_tag_d_test` |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_tag_d` parse | Composer | 注册标签日批与跨层 Sensor |
| `create_composer_bq_task(..., stem)` | 入口 | 绑定标签 SQL 为 BQ Insert Job |
| `create_external_sensor(..., qpon_{ods\|dwd\|dws\|dim\|analyst}_d, …)` | 入口 | 日上游 SUCCESS 门控 |
| `app_7_active_days()` 等 140 活函数 | BQ Operator | 按 tag 删写宽表 + MERGE metadata |
| `tag_qpon_base_*` / `tag_qpon_qponid_userid_latest()` | BQ Operator | 底座实体集与 ID 映射 |
| Dummy `start` / `start_new_task` | 入口 | 扇出锚点；`start_new_task` **无** BQ 下游 |
| （对照）`qpon_tag_d_test` | 测试 Composer | 不计入生产事实 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 主扇出：`start` → `wait_dws_qpon_device_active_info_*` / `wait_dwd_product_order_voucher_all` / `wait_ods_*` / `wait_dim_*` → 标签 BQ（`05` §A.10 / §app 摘录）。
- 设备活跃窗：`wait_…_inc_d` → app/h5 N 日活跃、active_uid、沉默相关；`wait_…_all_d` → Lastactive/first_act/inactive/version。
- 完单/销量：`wait_dwd_product_order_voucher_all` 高扇出（依赖边约 42 次引用）→ orders/Merchant_Sales/DAY*COMPLETED/user_*order*。
- 底座：`wait_ods_digital_food_device` → `tag_qpon_base_qponid_all_d`；`start` 直挂 `tag_qpon_base_userid_all_d`（**无** login Sensor）再扇出 DAY*；merchant/store base → Merchant_*/store_*。
- 下游：仓内生产 DAG **无** ExternalSensor 等本包；消费面在离线服务读 `qpon_services_prod` + `tag_qpon_metadata`（04）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；日批 Sensor | ✅；活 Sensor 全 `create_external_sensor`；**零** Skip / **零** wait `*_h` DAG |
| 03 下游 | tag ← ods/dwd/dws/dim | ✅；上游对齐全；仓内被等方≈0（仅 test） |
| 04 实体 | `qpon_services_prod.tag_qpon_*` + metadata | ✅；幂等键 `dayno`+`tag_name`（base 仅 `dayno`） |
| 06 异步 | 日工厂 retries=1000；BQ retries=3 | ✅；无 ES 旁路 |
| 07 配置 | TT 硬编码继承 08a | ✅ |

**08i 接力五项（本步审计结论）**：
1. **Skip×小时 DAG**：本包 **不** Sensor 等待任何 `qpon_*_h`——无「日工厂等小时」反例。但 ≥26 个 task SQL **裸读** `*_h` 表（login/user_info/voucher_h/traffic_h/product_h 等）→ 风险是「无依赖」而非「错误 Sensor 类型」。若未来补等小时，必须 Skip，禁止日工厂。
2. **RETURN×voucher**：读日批 `dwd_product_order_voucher_all` 的完单标签统一 `COMPLETED`+`RETURN`（依赖日批售后改写）——**合规**。读 `*_voucher_all_h` 仍套同过滤：`Store_Hot`、`DAY7/30_BARGAIN_ORDER_PAID_COUNT` 为**已知口径债**（小时透传无售后→RETURN）。
3. **维表分区**：门店标签读 `dim_store` **业务日** `partition_date=execution+1`（有 `wait_dim_store`）。映射任务 `tag_qpon_qponid_userid_latest` 读 `dim_device_latest_all_d` **`2999-12-31`**（有 `wait_dim_device_latest_all_d`）。商户活跃读小时 traffic，**无** dim_merchant/`2999` 双路径于本包主链。
4. **孤儿/ES**：Sensor **0 孤儿**（23/23 接线有 BQ 可达）。空挂：`start >> start_new_task`（无下游）。若干 `start >>` 裸跑 BQ（Explo_Channel*/Explore*/Qpon_Choice*/all_registeramount/Store_New_Operation/base_userid）。本包 **零** `*_es`——ES 吞异常 SUCCESS **不适用**；日批 ES 债仍在 08h。
5. **device_active**：`wait_…_inc_d` 下游 **19** 任务、`wait_…_all_d` 下游 **5**（并集 **24**）；另有 SQL 直读 DWS 活跃表。确认 **tag 为 device_active SLA 放大主战场之一**（对齐 rpt-d≈33 边量级叙事，本包并集 24）。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08j-01 | 标签宽表幂等键=`dayno`+`tag_name`：必须先 `DELETE` 再 `INSERT`；**禁止**漏删叠写；base/mapping 表幂等键仅=`dayno`（单任务独占） | `app_7_active_days` 等；`tag_qpon_base_*` | 同日同 tag 重复行/底座脏快照 |
| C-08j-02 | 每个活标签任务写完宽表后必须 `MERGE tag_qpon_metadata`（`data_type`+`data_id`→`latest_dayno`）；水位以表内 `max(dayno)`/`当日 dayno` 为准，禁止只插宽表不更水位 | 活 SQL 均含 MERGE；`device_app_last_version_code` | 服务读到旧 latest_dayno |
| C-08j-03 | 多任务可并行写同一宽表，但 **同一 `tag_name`（或同一 base 表）禁止双调度/双任务**；新增标签须新 `tag_name`，禁止复用已占用名 | 47 写 `tag_qpon_all_d` / 56 写 userid 宽表 | DELETE 互踩空窗 |
| C-08j-04 | 完单口径读日批 voucher 认 `COMPLETED`+`RETURN`；读 `dwd_product_order_voucher_all_h` **禁止**默认同语义（已知债：Store_Hot/DAY*_BARGAIN 已套用，新增禁止复制） | orders/Merchant_Sales vs Store_Hot | 小时/日标签假对齐 |
| C-08j-05 | 若新增对 `qpon_*_h` 的 ExternalSensor，必须用 Skip；**禁止**日工厂 `create_external_sensor`(retries=1000) 等小时；现网无 hour-DAG Sensor，禁止回退 | 入口零 Skip/零 `*_h` wait | 重试风暴/Skip 当失败 |
| C-08j-06 | SQL 裸读 `*_h` / `dwd_qpon_event_traffic_inc_d` 须头注释「不挂依赖」或补 Skip/日 Sensor；禁止把上游日 TI 绿当成小时表/流量已齐（已知技术债，新增禁止无说明裸读） | base_userid←login_h；Merchant_Active←traffic_h；Explo←traffic | TI 绿标签旧/空 |
| C-08j-07 | 读 `dim_store`/`dim_device_latest_all_d` 须声明业务日分区还是 `2999-12-31`；勿只看 `wait_dim_*` SUCCESS | store_categoies 日分区；qponid_userid_latest 2999 | 类目/映射错读 |
| C-08j-08 | 依赖 `dws_qpon_device_active_info_{inc,all}_d` 的标签须知晓：DWS Sensor 绿 ≠ traffic 已挂依赖（08g C-08g-07）；重大活跃口径变更须联动评估（已知放大债） | inc 下游 19 / all 下游 5 | 活跃类标签假绿 |
| C-08j-09 | 本包无 ES；**禁止**从 rpt 复制 `*_es` 吞异常；`start_new_task`/裸 `start>>` 不得当「上游已就绪」 | 入口零 ES；L425 空挂 | TI 假语义/空耗 |

---

## G. 宽表写入与 metadata 水位

**业务背景**：增长/运营服务按标签名拉取设备/用户/商户/门店特征值，并用元数据表判断「该标签最新业务日」。

**实现方式**：标准三步——`DELETE … dayno=业务日 [AND tag_name=…]` → `INSERT` 当日切片 → `MERGE tag_qpon_metadata`（`TAG`+tag_name / `BASE_*` / `ID_MAPPING`）更新 `latest_dayno`。业务日=`execution_date+1`。写目标：`tag_qpon_all_d`(≈47)、`tag_qpon_userid_all_d`(≈56)、`tag_qpon_merchant_all_d`(18)、`tag_qpon_store_all_d`(14)、4×base、1×mapping。

**关键决策点**：
- `app_7_active_days` — 按 `tag_name` 删写设备宽表 → 与其他 tag 并行安全。
- `tag_qpon_base_userid_all_d` — 仅按 `dayno` 删整分区 → 必须单写者。
- `device_app_last_version_code` — MERGE 源用**当日** `dayno` 而非历史 max → 水位与切片对齐更紧。
- metadata `data_type` — `TAG`/`BASE_*`/`ID_MAPPING` 分槽 → 同名 data_id 跨类型不撞。

**失败模式**：漏 MERGE 导致服务卡在旧 dayno；两任务同 `tag_name` 并发 DELETE；改 tag_name 字符串未同步消费方。

---

## H. Sensor 门控、小时表裸读与 voucher 口径

**业务背景**：标签依赖多层日仓就绪；部分任务为取全量/近实时又直读小时贴源或 voucher_h。

**实现方式**：活 Sensor 23= ODS9+DWD8+DWS3+DIM2+analyst1，全部日工厂。`wait_dwd_product_order_voucher_all` 贯穿完单/销量。小时表无 DAG 级 wait：login_h、user_info_c_all_h、voucher_all_h、business_event_traffic_inc_h、life_product_all_h 等由 SQL 直读。

**关键决策点**：
- 入口 — 选日工厂等日上游 → 对日批合规；**未**错误地对小时 DAG 用日工厂。
- `app_7_orders_num` — 日 voucher + `COMPLETED`+`RETURN` → 对齐售后改写。
- `Store_Hot` / `DAY*_BARGAIN_*` — voucher_h + 同过滤 → 透传表套 RETURN（债）。
- `tag_qpon_base_userid_all_d` — `start>>` 无 wait，读 login_h → 底座可先于小时登录就绪。
- `Merchant_Active_*` — 仅 wait merchant base，读 traffic_h → 商户活跃不绑小时 Sensor。

**失败模式**：把 tag TI 绿当 voucher_h/login_h 已出齐；把小时标签完单与日批 GTV 强对齐；未来用日工厂补等 `qpon_dwd_h`。

---

## I. device_active 扇出与 SLA

**业务背景**：08g/08h/08i 指出 DWS device_active inc 裸读 traffic；rpt-d≈33 边放大。本包是标签侧主放大点。

**实现方式**：`wait_dws_qpon_device_active_info_inc_d` → 19 个下游（app/h5 活跃窗、active_uid、Churned/Second_order、user_first_act_*、USER_RECENT_INACTIVE_*）；`wait_…_all_d` → 5 个（Lastactive/first_act_days/inactive×2/version）。另 Explo_Channel* **不等** DWS，直接裸读 `dwd_qpon_event_traffic_inc_d`（与 DWS 同源债叠加）。

**关键决策点**：
- 活跃类标签 — 等 DWS TI → 不感知 traffic 未挂依赖。
- `app_30_inactive` / `device_app_last_version_code` — 等 all 表 → 依赖 inc→all 链与位图滚动正确性。
- vs rpt-h — 小时报表**不**等 device_active；本包+rpt-d 才是主战场（验证 08i 接力第 5 点）。

**失败模式**：traffic 滞后但 adjust/DWS 绿 → 活跃标签系统性偏低且 metadata 已推进；只修 rpt 不评估 tag 扇出。

---

## J. 同表并发、维表分区与空挂

**业务背景**：百级标签共享四张宽表；门店/设备维有日分区与 2999 两套快照语义。

**实现方式**：冲突隔离靠 `tag_name`（宽表）或单任务独占（base）。`dim_store` 标签链：业务日分区 + `wait_dim_store`。设备最新维映射：`2999-12-31` + `wait_dim_device_latest_all_d`。空挂/裸跑：`start_new_task`；Explo/Explore/Choice/all_registeramount/Store_New_Operation/base_userid。

**关键决策点**：
- 并行写 `tag_qpon_all_d` — 不同 tag_name → 允许；同名 → 禁止。
- `store_categoies` — `dim_store` 日分区 → 与 mapping 的 2999 设备维不可混用解读。
- `start_new_task` — 无 BQ → 不得解释为「新任务通道已就绪」。

**失败模式**：复制 base 表「只 DELETE dayno」模式到多标签任务；维表只刷 2999 不刷日分区导致门店类目标签漂移；把空挂 Dummy 当门控。

---

> [!SUCCESS] 标签生产日批 模块深潜闭环验证
> - 扫描范围：1 入口 + Sensor 23（孤儿 0）+ BQ 140 + 代表 SQL + 小时裸读 26 + 下游引用（仅 test）
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：171 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：已确认入口与代表 tasks 遍历至终态，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_tag_d` 写 `qpon_services_prod` 宽表+`tag_qpon_metadata.latest_dayno`；Sensor×23 全日 DAG、零 Skip、零 hour-DAG wait、零孤儿、零 ES。幂等=`dayno`+`tag_name`（base 仅 dayno）。日 voucher 完单 `COMPLETED`+`RETURN` 合规；voucher_h 同过滤为债（Store_Hot/DAY*_BARGAIN）。dim_store=业务日；dim_device_latest 映射=2999。≥26 SQL 裸读 `*_h`/traffic。device_active Sensor 下游并集 24——确认 tag 为 SLA 放大主战场（并列 rpt-d）。仓内无生产 DAG Sensor 消费本包。
> - **推演约束 (Constraint)**: 下一模块（analyst-serving / 收官）必须 (1) 若等小时上游坚持 Skip，禁止日工厂；(2) 读标签/报表完单时区分日批 RETURN 与小时透传，勿把 tag 对 voucher_h 的套用当权威；(3) 对账维表日分区 vs 2999；(4) 勿把空挂 Dummy、裸 `start>>`、或（他包）ES 吞异常 SUCCESS 当就绪；(5) 改 DWS device_active/traffic 依赖须同步评估 **tag∪rpt-d** 扇出，勿假设小时 rpt 已消化。
> - **物理锚点 (Anchors)**: `dags/qpon_tag_d/qpon_tag_d.py` L174–209 Sensor / L220–404 BQ / L425 空挂 start_new_task / L430–854 依赖边；`tasks/app_7_active_days.py` DELETE+INSERT+MERGE；`tasks/app_7_orders_num.py` COMPLETED+RETURN；`tasks/tag_qpon_base_userid_all_d.py` 裸读 login_h；`tasks/tag_qpon_qponid_userid_latest.py` dim 2999；`tasks/Store_Hot.py` voucher_h+RETURN；`tasks/Merchant_Active_7.py` traffic_h；`dags/airflow_config/create_external_sensor.py` 日工厂
