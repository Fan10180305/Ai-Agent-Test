# 08i 模块深潜：RPT报表小时批（rpt-h）

> 模块 id=`rpt-h`；权威范围=`dags/`（重点 `dags/qpon_rpt_h/`；日批见 08h）  
> 不重复 Step05 全量调用链；本步钻取 **Skip 合规**、**与日批 RPT 差异**、**voucher_h×RETURN**、**商户/商品维路径**、**空挂 Sensor / 无 ES**  
> Step08h 接力：(1) 小时消费坚持 Skip，禁止日工厂等小时；(2) 勿把日批 voucher 售后 RETURN 套到 voucher_h；(3) 对账商户维日分区 vs `2999`；(4) 勿把孤儿 Sensor / ES 吞异常 SUCCESS 当就绪；(5) 评估 device_active 扇出对小时/标签 SLA  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以 `step-08-rpt-h_prompt.md` + 用户指令 id=`rpt-h`/suffix=`i` 为准

> [!SUCCESS] RPT报表小时批 模块深潜闭环验证
> - 扫描范围：1 入口 DAG + SkipSensor 15（接线下游 14 / 空挂 1）+ ShortCircuit×1 + 活 BQ 4 + 注释下线 BQ≈16 + 代表 SQL（bd_trade/unique/coupon）+ 仓内下游引用抽检（0）
> - 提取结果：7 个入口方法、8 条衍生约束、4 个业务特性章节
> - 全文行数：178 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+Skip / Step 03 下游=本包无仓内 Sensor 消费方 / Step 04 实体=`qpon_rpt_d.*`（小时任务写日 dataset）
> - EOF 状态：入口 `qpon_rpt_h.py`（285 行）与 4 活 tasks 已读；无静默截断

---

## A. 模块定位

`qpon_rpt_h`（`10 * * * *`）是 **RPT 小时批精简汇聚层**：对 ODS/DWD 小时上游用 SkipSensor 门控后，产出优惠券活动/批次统计、地推交易经营、唯一订单明细等，写入 dataset `qpon_rpt_d`（与日批同库、表名常带 `_h` 或不带）。相对 `qpon_rpt_d`：无 ES、无 Marker、无 daily_report/alarm/risk 边；活 BQ 仅 4；**零**日工厂等小时活调用——与 `qpon_dwd_h` 反例对照为合规模板。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_rpt_h` / `qpon_rpt_h.py` | Orchestrator | 小时入口；Skip×15；ShortCircuit×1；活 BQ×4 |
| `create_composer_bq_task` | Factory | 动态 import `qpon_rpt_h.tasks.<stem>` |
| `create_external_task_skip_sensor_hour` | Factory/Sensor | 等 `qpon_ods_h`/`qpon_dwd_h`；Skip 透传 |
| `create_external_sensor` | Factory | **仅 import + 注释样例**；活调用=0 |
| `ShortCircuitOperator.wait_check_allowed_hours` | Checker | 仅门控 `rpt_coupon_batch_statistic_h`（`hour∈{20}` UTC） |
| `rpt_product_unique_order_detail` | Executor | TRUNCATE+INSERT 近 2 日唯一订单 |
| `rpt_coupon_activity_statistic_h` / `*_batch_*` | Executor | 活动/批次券指标 DELETE+INSERT |
| `rpt_bd_trade_operating_data_h` | Executor | 地推交易经营分区重算 + 商品维 UPDATE |
| `qpon_ods_h` / `qpon_dwd_h` | Upstream | 被 SkipSensor 等待 |
| （无仓内 Downstream Caller） | — | `dags/` 内无其他 DAG `wait` 本包 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_rpt_h` parse | Composer | 注册小时报表与 SkipSensor |
| `create_composer_bq_task(..., stem)` | 入口 | 绑定 BQ SQL |
| `create_external_task_skip_sensor_hour(..., qpon_ods_h\|qpon_dwd_h, …)` | 入口 | 小时上游 Skip 门控 |
| `check_allowed_hours` | ShortCircuit | 非 UTC20 → Skip 批次券报表 |
| `rpt_product_unique_order_detail()` 等 4 活函数 | BQ Operator | 分区/全表重算写 `qpon_rpt_d` |
| （注释）`create_external_sensor(..., qpon_dwd_h, saas…)` | 曾计划 | 日工厂等小时反例痕迹，已下线 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 主扇出：`start` → SkipSensor→`qpon_ods_h`/`qpon_dwd_h` → 活 `rpt_*`（`05` §A.9）。
- 唯一订单：`wait_dwd_product_unique_order_detail_h` → `rpt_product_unique_order_detail`。
- 券活动：多 ODS Skip → `rpt_coupon_activity_statistic_h`；批次另加 `wait_ods_user_info_c_all_h` + `wait_check_allowed_hours`。
- 地推：settle_rule + voucher_h + store/product detail Skip → `rpt_bd_trade_operating_data_h`。
- 空挂：`start` → `wait_dwd_qpon_event_traffic_inc_d`（无下游 BQ；原 app 留存/用户统计已注释）。
- 下游：仓内 **无** Sensor/Marker 消费本包（对比日批 daily_report/alarm/risk）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；小时 Skip | ✅；活 wait 全 Skip |
| 03 下游 | 小时层以 Skip 互等为主 | ✅；**本包无仓内被等方** |
| 04 实体 | 写 `qpon_rpt_d` | ✅；幂等键多为 `partition_date`，unique 为全表 TRUNCATE |
| 06 异步 | Skip retries=20；ShortCircuit | ✅；无 ES 旁路 |
| 07 配置 | TT 硬编码继承 08a | ✅ |

**08h 接力五项（本步审计结论）**：
1. **Skip**：活 Sensor **15/15** 为 `create_external_task_skip_sensor_hour`；日工厂活调用 **0**（仅注释 saas 行曾用 `create_external_sensor`）。**合规**；禁止回退。
2. **RETURN×voucher_h**：`rpt_bd_trade_operating_data_h` 对 `dwd_product_order_voucher_all_h` 过滤 `COMPLETED`+`RETURN`——与日批字面相同，但小时枢纽**无**售后→RETURN 改写（08f C-08f-04）。属**已知口径套用债**；券链用 ODS `OK`/`COMPLETED`，不经 voucher_h。
3. **商户/商品维**：活链**无** `dim_merchant_basic_info`；`bd_trade` UPDATE 读 `dim_product_basic_info` **业务日分区**（`execution_date+1`），**非 2999**，且**无** `wait_dim_*`（裸读）。
4. **孤儿/ES**：无「create 未 `>>`」经典孤儿；有 **空挂** `wait_dwd_qpon_event_traffic_inc_d`（有上游无 BQ 下游）。本包 **零** `*_es`——ES 吞异常 SUCCESS **不适用本包**（日批债仍在 08h）。
5. **device_active SLA**：活报表**不等** `dws_qpon_device_active_*`；traffic Skip 空挂不放大 DWS 裸读。小时侧 SLA 主风险在 voucher_h/ODS Skip 与 dim 裸读，不在 device_active 扇出。标签层仍须单独评估日批 device_active 放大（交 tag）。

与日批 RPT 差异摘要：规模 4 vs 156；Skip vs 日工厂；无 ES/Marker/日报；写同 dataset；unique **TRUNCATE** vs 日批分区窗；bd_trade 显式套 RETURN 到 voucher_h。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08i-01 | 等 `qpon_ods_h`/`qpon_dwd_h` 必须用 Skip；**禁止**对本包新增日工厂 `create_external_sensor`(retries=1000)；现网已合规，禁止回退注释 saas 模式 | 入口 Skip×15；注释 saas 日工厂 | Skip 语义丢；重试风暴 |
| C-08i-02 | 分区报表幂等：`bd_trade`/券活动按 `partition_date` DELETE 再 INSERT；`coupon_batch` 现网 `DELETE WHERE 1=1`、`unique_order` 为 **TRUNCATE 全表**——改并发/多调度须先改幂等策略（已知技术债，新增禁止复制 TRUNCATE） | 三任务删写形态 | 并发互踩/空窗 |
| C-08i-03 | 读 `dwd_product_order_voucher_all_h` **禁止**默认套用日批「售后成功→RETURN 计入完单」语义；现网 `bd_trade` 已 `COMPLETED`+`RETURN` 为已知债，口径变更须对照 08f 透传事实并双批说明 | `rpt_bd_trade_operating_data_h` 过滤 | 小时/日 GTV 假对齐 |
| C-08i-04 | 读 `dim_product_basic_info`/`dim_merchant_*` 须声明日分区还是 `2999-12-31`；本包 bd_trade=业务日分区且无 dim Sensor——改维调度须评估裸读滞后 | UPDATE←dim 日分区 | 类目/档位陈旧但 TI 绿 |
| C-08i-05 | 空挂 Sensor（现 `wait_dwd_qpon_event_traffic_inc_d`）不得当「流量/留存已就绪」；恢复 app 留存类 BQ 须同时接线 `>>`，禁止只留 wait | `start >> wait_traffic` 无 BQ | 假依赖/空耗 Skip |
| C-08i-06 | `wait_check_allowed_hours` 仅真实门控批次券（UTC hour=20）；**禁止**当成全 DAG 或 Dummy 空转边；改窗口须同步改 `allowed_hours`（注释 UTC8 列表未生效） | `check_allowed_hours`→batch | 批次漏跑/误跑 |
| C-08i-07 | 本包无 ES；**禁止**从 `qpon_rpt_d` 复制 `*_es` 吞异常模式到小时批；若新增 ES 必须 raise 失败 | 入口零 Python ES | TI 假绿 |
| C-08i-08 | 仓内暂无下游等本包；若 tag/分析新增跨 DAG wait，小时侧须 Skip，禁止日工厂等 `qpon_rpt_h` | 下游引用=0 | 重试风暴/错对齐 |

---

## G. Skip 合规与日工厂反例痕迹

**业务背景**：小时上游可 ShortCircuit/Skip，日工厂 retries=1000 会把 Skip 当失败风暴；rpt-h 应是正面样本。

**实现方式**：活 wait 全 `create_external_task_skip_sensor_hour`→`qpon_ods_h`/`qpon_dwd_h`。`create_external_sensor` 仍 import，仅注释 saas 行曾指向 `qpon_dwd_h`。

**关键决策点**：
- 入口活边 — 选 Skip → 合规模板（对齐 dim_h/dws_h）。
- 注释 saas — 曾日工厂等小时 → 反例痕迹，复活禁止照抄。
- vs `qpon_dwd_h` — 上游反例仍在；本包消费侧已正确。

**失败模式**：解注释 saas 并用日工厂；把 `create_external_sensor_hour`（仓内无活调用）误当 Skip 等价物。

---

## H. voucher_h×RETURN 与地推经营链

**业务背景**：地推看板要支付/核销 GMV；日批用售后改写后的 RETURN 当完单；小时 voucher **透传** ODS 状态。

**实现方式**：Skip 齐 settle/voucher/store/product → DELETE 当日分区 + INSERT；订单/核销 CTE 均 `order_status in ('COMPLETED','RETURN')`；再 UPDATE 商品一二级类目←`dim_product_basic_info` 业务日分区。

**关键决策点**：
- `rpt_bd_trade_operating_data_h` — 过滤含 RETURN → 与日批字面同、语义不等价（无本地售后 CASE）。
- 同函数 UPDATE dim — 日分区路径、无 wait_dim → TI 绿≠维表当日已刷。
- 券活动/批次 — 完单认 ODS food `OK|COMPLETED`、life `COMPLETED`，**不**读 voucher_h。

**失败模式**：用 bd_trade 小时数对账日批经营指标并假设 RETURN 集合相同；只刷 2999 商品维却期望本 UPDATE 命中。

---

## I. 幂等形态与 ShortCircuit 窗口

**业务背景**：小时多次调度；删写策略决定是否互踩。

**实现方式**：
| 任务 | 清理策略 |
|---|---|
| `rpt_bd_trade_operating_data_h` | DELETE `partition_date=业务日` |
| `rpt_coupon_activity_statistic_h` | DELETE 当日分区 |
| `rpt_coupon_batch_statistic_h` | `DELETE WHERE 1=1` 全表 |
| `rpt_product_unique_order_detail` | **TRUNCATE** 全表后插近 2 日 |

ShortCircuit：仅 batch 依赖；`allowed_hours=[20]`（UTC），注释中的 UTC8/`allowed_hours_UTC` 未参与判断。

**关键决策点**：
- unique TRUNCATE — 任意小时成功即清空全表再写 → 并发/失败半截风险高。
- batch 全删 — 非允许小时被 ShortCircuit Skip，表保留上次全量快照。
- activity 每小时重算当日分区 — 无 hour 门控。

**失败模式**：并行补数跑两个 unique TI；误以为注释小时列表已生效导致「非 20 点也该出批次」。

---

## J. 空挂 traffic、device_active 与下游真空

**业务背景**：08h 强调 device_active 扇出放大 DWS traffic 裸读；需确认小时报表是否继续放大。

**实现方式**：`start >> wait_dwd_qpon_event_traffic_inc_d` 后无 `rpt_*`；原 `rpt_app_user_statistic`/`retention` 已注释。活 4 任务均不等 DWS device_active。`dags/` 内无 DAG 引用 `qpon_rpt_h`。

**关键决策点**：
- traffic 空挂 — Sensor 绿≠任何小时报表已消费流量。
- device_active — **不**经本包放大到小时活链；标签/日批风险仍在 tag/rpt-d。
- 下游真空 — 本包产出偏「直连取数/看板」，改表名无仓内 Sensor 双改点，但有离线消费未知面。

**失败模式**：把 traffic wait SUCCESS 当留存小时表已更新；在 tag 用日工厂等未来小时 rpt 任务。

---

> [!SUCCESS] RPT报表小时批 模块深潜闭环验证
> - 扫描范围：1 入口 + Skip 15（下游接线 14 / 空挂 1）+ ShortCircuit 1 + 活 BQ 4 + 注释 BQ≈16 + 代表 SQL + 下游引用 0
> - 提取结果：7 个入口方法、8 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：178 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：已确认入口与 4 活 tasks 遍历至终态，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_rpt_h` **已**全量 Skip 等 ods_h/dwd_h（正面样本）；日工厂活调用 0。活 BQ×4 写 `qpon_rpt_d`；无 ES/Marker/仓内下游。`bd_trade` 对 voucher_h 套 `COMPLETED`+`RETURN`（小时无售后改写，口径债）。商品维 UPDATE=业务日分区裸读（非 2999、无 wait_dim）。`wait_dwd_qpon_event_traffic_inc_d` 空挂；活链**不等** device_active，不放大 08h SLA。unique=TRUNCATE、batch=`DELETE 1=1` 为重幂等债。ShortCircuit 仅 UTC20 门控 batch。
> - **推演约束 (Constraint)**: 下一模块（tag / 收官）必须 (1) 若消费小时上游坚持 Skip，禁止日工厂等 `*_h`；(2) 标签/报表读 voucher 完单时区分日批售后 RETURN 与小时透传，勿用 rpt-h bd_trade 当日批等价；(3) 读商户/商品维对账日分区 vs `2999`，勿只看 TI；(4) 勿把空挂 Sensor 或（日批）ES 吞异常 SUCCESS 当就绪；(5) device_active 扇出风险主战场在 **tag/日批 rpt**，勿假设小时 rpt 已消化该债。
> - **物理锚点 (Anchors)**: `dags/qpon_rpt_h/qpon_rpt_h.py` L112–140 Skip / L172–184 活 BQ / L210 空挂 traffic / L234–280 边 / L81–95 ShortCircuit；`tasks/rpt_bd_trade_operating_data_h.py` COMPLETED+RETURN + dim 日分区 UPDATE；`tasks/rpt_product_unique_order_detail.py` TRUNCATE；`tasks/rpt_coupon_batch_statistic_h.py` DELETE 1=1；`dags/airflow_config/create_external_sensor.py` Skip 工厂
