# 08h 模块深潜：RPT报表日批（rpt-d）

> 模块 id=`rpt-d`；权威范围=`dags/`（重点 `dags/qpon_rpt_d/`；小时批留给 rpt-h）  
> 不重复 Step05 全量调用链；本步钻取 **报表分区重算**、**DWS/DWD/DIM Sensor**、**ES 写出旁路**、**daily_report 依赖边**  
> Step08g 接力：(1) 小时消费坚持 Skip；(2) 勿混日/时 voucher `order_status`；(3) 对账商户维日分区 vs `2999-12-31`；(4) 勿把空转/孤儿 Sensor 当就绪；(5) 评估 device_active 裸读与倒挂对 SLA  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以 `step-08-rpt-d_prompt.md` + 用户指令 id=`rpt-d`/suffix=`h` 为准

> [!SUCCESS] RPT报表日批 模块深潜闭环验证
> - 扫描范围：1 入口 DAG + Sensor 115（接线 101 / 孤儿 14）+ 活 BQ 156 + Python 13（ES 11）+ Marker×2 + `qpon_daily_report`/`alarm`/`risk` 下游边 + 代表 SQL（indicator/merchant/retention/ES）
> - 提取结果：9 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：174 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+跨 DAG wait/Marker / Step 03 下游=ES·daily_report·alarm·risk / Step 04 实体=`qpon_rpt_d.*`+ES index
> - EOF 状态：入口 `qpon_rpt_d.py`（2489 行）与代表 tasks/`daily_report`/`create_external_*` 关键路径已读；无静默截断

---

## A. 模块定位

`qpon_rpt_d`（`0 18 * * *`）是仓内 **最大报表日批汇聚层**：在 ODS/DWD/DIM/DWS（及少量 analyst/data_server）日工厂 Sensor 门控后，对经营指标、留存、商户/渠道看板等做分区重算写入 dataset `qpon_rpt_d`，再经 Python 旁路写阿里云 ES，并向 `qpon_analyst_alarm_d`（Marker）、`qpon_daily_report`（跨调度 Sensor）、`qpon_risk_d` 供数。本包 **零** 指向 `*_h` DAG 的 Sensor、**无** SkipSensor——小时报表留给 `qpon_rpt_h`。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_rpt_d` / `qpon_rpt_d.py` | Orchestrator | 日批入口；Sensor×115；BQ×156；Python×13；Marker×2；ShortCircuit 周/月末 |
| `create_composer_bq_task` / `create_composer_python_task` | Factory | 动态 import `qpon_rpt_d.tasks.<stem>` |
| `create_external_sensor` | Factory/Sensor | 日批等上游 SUCCESS；retries=1000 / timeout=64800 |
| `create_external_marker` | Factory | `ExternalTaskMarker`→`qpon_analyst_alarm_d` wait 任务 |
| `rpt_business_indicator_{detail,summary}_d` 等 | Executor | 经营指标明细/汇总分区重算（日报主链） |
| `rpt_*_es`（11） | Executor | BQ 读本层表 → Cloud Run ES 写 |
| `ShortCircuitOperator`（sunday / month_end / 组合） | Checker | 周末/月末报表门控 |
| `TimeDeltaSensor.wait_3_hours` | Sensor | 延时后跑留存类任务（非 Dummy 空转） |
| `qpon_ods_d`/`dwd_d`/`dim_d`/`dws_d` | Upstream | 被本包日工厂 Sensor 等待 |
| `qpon_daily_report` / `qpon_analyst_alarm_d` / `qpon_risk_d` | Downstream Caller | 等 summary / L0L1 / settlement |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_rpt_d` parse | Composer | 注册全量报表任务与跨层 Sensor |
| `create_composer_bq_task(..., stem)` | 入口 | 绑定 BQ SQL 任务 |
| `create_composer_python_task(..., stem_es)` | 入口 | 绑定 ES 写出 Python |
| `create_external_sensor(..., qpon_{ods,dwd,dim,dws}_d / analyst_d / data_server_d, …)` | 入口 | 日批上游门控 |
| `create_external_marker(..., qpon_analyst_alarm_d, wait_rpt_*)` | 入口 | 标记 alarm Sensor 目标 |
| `check_if_sunday` / `check_if_monthend` / `check_sunday_or_month_end` | ShortCircuit | 周/月末分支 |
| `rpt_business_indicator_detail_d()` / `*_summary_d()` | BQ | 明细 31 日窗 DELETE+INSERT；汇总周月 DELETE+INSERT(+MERGE) |
| `*_es()` | PythonOperator | `access_cloud_run_write_aliyun_es` |
| 下游 `ExternalTaskSensor` / `create_external_sensor(..., qpon_rpt_d, …)` | daily_report / alarm / risk | 跨 DAG 消费本层 |

---

## D. 调用链（引用 Step05，不重复追踪）

- 主扇出：`start` → `wait_{ods\|dwd\|dim\|dws}_*` → `rpt_*`（`05` §A.5 / 编排图 RPT 节点）。
- 经营指标：`wait_dim_*` + `wait_dwd_product_order_voucher_all` + … → `rpt_business_indicator_detail_d` → `rpt_business_indicator_summary_d` / platform/client/customer/merchant 汇总扇出。
- ES：`rpt_{channe\|department\|trade}_*` BQ → 同名 `*_es`（旁路，不回写 BQ）。
- Marker：`rpt_bq_l0l1_*` → `marker_*` → `qpon_analyst_alarm_d`。
- 日报：`qpon_daily_report.wait_rpt_business_indicator_summary_d`（`execution_delta=+8h`）→ query → GenAI → 飞书。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；跨 DAG wait/Marker | ✅；孤儿 Sensor×14；自等 `qpon_rpt_d` Sensor 已注释下线 |
| 03 下游 | ES×11；daily_report；alarm；risk←settlement | ✅ |
| 04 实体 | `qpon_rpt_d.*` DELETE+INSERT；ES index+`id_field` | ✅；明细删近 31 日窗 |
| 06 异步 | Sensor1000；daily_report delta=8h；ES 靠 DAG retries | ✅；本包 ES **吞异常不 raise**（见 §I） |
| 07 配置 | TT 硬编码；ES Variable/超时继承 08a | ✅ |

**08g 接力五项（本步审计结论）**：
1. **Skip**：本包活 Sensor **零**指向 `qpon_*_h`；无 Skip 导入。合规章：小时消费留给 `qpon_rpt_h`，须 Skip，禁止复制日工厂等小时。
2. **order_status**：经营/商户报表过滤日批 `dwd_product_order_voucher_all` 的 `COMPLETED`+`RETURN`（依赖日批售后改写）；**勿**与小时 `*_voucher_all_h` 同字面量混用。
3. **商户维**：`rpt_business_indicator_detail_d` **双路径**——等级/规则等读业务日分区窗，部分维度读 `2999-12-31`；`rpt_merchant_daily_data_inc_d` 商户档位走 **2999**。`wait_dim_merchant_basic_info` 绿 ≠ 已声明读哪条。
4. **孤儿/空转**：孤儿 Sensor×14（含 `wait_dim_store_grid`、`wait_ads_checkin_inc_d`、多条搜索/消息 DWD wait）**无** `>>`，不得当就绪。本包无 `check_allowed_hours_is_run`；`wait_3_hours` 为真实 TimeDelta 门控（留存链），非 Dummy。
5. **device_active SLA**：约 **33** 个唯一 `rpt_*` 边依赖 `wait_dws_qpon_device_active_info_{inc,all}_d`。上游 DWS inc **裸读 traffic** + DWD→DWS 倒挂（08g）→ 本包 Sensor 绿仅保证 DWS TI，**放大**日活/留存/指标 SLA 风险（流量未挂依赖仍可绿）。

上游抽检：DWS 7 个 wait 全接线；DIM 17 中仅 `wait_dim_store_grid` 孤儿；`rpt_store_feature_training_info_h` BQ **已注释**（小时特征不在本包活跑）。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08h-01 | 本包等日上游用 `create_external_sensor`；**禁止**新增指向 `qpon_*_h` 的日工厂 Sensor；小时报表消费须在 `qpon_rpt_h` 用 Skip | 入口零 `*_h` Sensor | Skip 语义丢；重试风暴 |
| C-08h-02 | 分区报表幂等键=`partition_date`（业务日=`execution_date+1`）；须带分区（或明确日期窗）DELETE 再 INSERT；`summary` 周/月按聚合单元删写 | `rpt_business_indicator_detail_d` 31 日 DELETE；`*_summary_d` | 叠写/错窗 |
| C-08h-03 | 完单口径读日批 voucher 时认 `COMPLETED`+`RETURN`；**禁止**静默改用小时 voucher_h 或假设无售后改写同语义 | detail/merchant_daily 过滤 | GTV/完单与小时分裂 |
| C-08h-04 | 读 `dim_merchant_basic_info`/`dim_product_basic_info` 须声明日分区窗还是 `2999-12-31`；勿只看 `wait_dim_*` TI 绿 | detail 双路径；merchant_daily 2999 | 档位/结算错读 |
| C-08h-05 | 孤儿 Sensor（现网×14）不得当作上游就绪；恢复任务须同时 `create`+`>>`，禁止只复活 wait | 孤儿清单 §E | 假依赖/空占槽 |
| C-08h-06 | ES 旁路须 `id_field` 稳定；写失败必须 `raise`（禁止仅 `print`）；已知技术债：现网 11×`*_es` 吞异常，**新增禁止复制** | `rpt_*_es` except print | TI 绿但 ES 空/旧 |
| C-08h-07 | 改 `qpon_rpt_d` 或 `qpon_daily_report` 任一方 cron，必须重算并更新 `execution_delta`（现 `+8h`） | `qpon_daily_report` L143–156 | 日报永久空等 |
| C-08h-08 | 依赖 `dws_qpon_device_active_*` 的报表须知晓：DWS Sensor 绿 ≠ traffic 已挂依赖；重大口径变更须联动评估 DWS 裸读与 dwd 倒挂（已知放大债，禁止假装「等 DWS=流量齐」） | 本包×33 边；08g C-08g-07/09 | 留存/DAU 假绿 |
| C-08h-09 | Marker 目标 task_id 须与 `qpon_analyst_alarm_d` Sensor 一致；禁止只改一侧 | `create_external_marker` L552–553 + `>> marker` | alarm 空等/清错 |

---

## G. 报表分区重算与经营指标主链

**业务背景**：经营看板与飞书日报依赖 `rpt_business_indicator_*`；明细按业务日滚动回刷近窗，汇总再聚周/月。

**实现方式**：`detail`：`DELETE … WHERE partition_date BETWEEN 30ago AND 业务日` + `INSERT` 重算窗；读日批 voucher（`COMPLETED`+`RETURN`）+ dim 商户/商品（日分区与 2999 混用）。`summary`：按 `week`/`month` 条件 DELETE 后 INSERT，并含 MERGE 补核销指标。编排：`detail` → `summary`（及 platform/client/… 扇出）；`daily_report` 只等 `summary`。

**关键决策点**：
- `rpt_business_indicator_detail_d` — 删写范围=近 31 日 → 回刷成本高、保证近窗一致。
- `rpt_business_indicator_summary_d` — `agg_period∈{week,month}` → 不同 DELETE 谓词。
- 入口 L1518–1523 — `summary` 依赖 `detail`+`platform_indicator_summary_d` → 平台汇总未成则日报上游不齐。

**失败模式**：只改 summary 过滤不改 detail 窗；把 daily_report 改挂到 `detail` 却不同步 cron/delta；商户维只刷 2999 不刷日分区导致 detail 历史窗档位漂移。

---

## H. DWS/DWD/DIM Sensor 扇出与 device_active SLA

**业务背景**：报表是跨层 Sensor 最密消费方（ODS52/DWD36/DIM17/DWS7）；设备活跃是留存/增长/多项指标公共门控。

**实现方式**：日工厂 `create_external_sensor`；`wait_dws_qpon_device_active_info_{inc,all}_d` 被约 33 个 `rpt_*` 边复用。另有 `wait_dwd_product_order_voucher_all` 贯穿经营/商户链；DIM 商户/门店/商品门控经营明细。层外：`wait_ads_product_consume_detail`（analyst，已接线）、`wait_dwd_merchant_daily_performance`（data_server，已接线）；`wait_ads_checkin_inc_d` 孤儿。

**关键决策点**：
- 入口 — 等 DWS device_active → 仅绑定 DWS TI，不感知 traffic 裸读。
- `wait_3_hours` + device_active → `rpt_app_retention_statistic_v3` / `rpt_app_user_statistic_v3` → 额外推迟 SLA。
- ShortCircuit 周/月末 — 非允许日历 → Skip 周月报表（真门控，非 Dummy）。

**失败模式**：把孤儿 wait 当「已保护」；DWS 绿但 traffic 未就绪导致大面积留存/DAU 空；复制 dwd→dws 倒挂到 rpt（禁止）。

---

## I. ES 写出旁路

**业务背景**：渠道/部门/交易看板需近实时检索；BQ 算完后旁路同步阿里云 ES，失败不应被当成 BQ 成功的等价物。

**实现方式**：`rpt_*` BQ `>>` `rpt_*_es`；Python 查本层表（DAY/WEEK/MONTH 近窗）→ `access_cloud_run_write_aliyun_es(sql, id_field, index)`。活 11 个；均 `id_field="id"`。

**关键决策点**：
- 编排 — ES 在 BQ 成功后串行 → BQ 失败不写 ES；**ES 失败现网不失败 TI**（吞异常）。
- `access_cloud_run_write_aliyun_es` — 函数内失败会 raise，但被 task `except: print` 吃掉 → Airflow SUCCESS。

**失败模式**：看板 BQ 有数、ES 无更新且无告警；新增 ES 任务复制吞异常模式；`id_field=None` 导致重复文档（08a/06 已禁）。

---

## J. daily_report / Marker / 跨调度依赖边

**业务背景**：飞书经营日报与 L0L1 告警挂在本包关键任务上，调度时刻与日批错开。

**实现方式**：
- `qpon_daily_report`（`0 2 * * *`）直连 `ExternalTaskSensor`→`rpt_business_indicator_summary_d`，`execution_delta=+8h`，retries=100，timeout=28800。
- Marker×2：`rpt_bq_l0l1_statistic_indicators_details_d` / `quantile_details_d` → alarm wait。
- `qpon_risk_d` 等 `rpt_store_settlement_detail_inc_d`。

**关键决策点**：
- daily_report — 只认 `summary` SUCCESS + 正确 delta → cron 任一侧漂移即空等。
- Marker — 清下游依赖时依赖 Marker 绑定 → task_id 改名须双改。

**失败模式**：把日报 Sensor 改挂未产出的注释任务；忽略 delta 只对齐「同名 logical date」；误把 Marker 当本包内部幂等手段。

---

> [!SUCCESS] RPT报表日批 模块深潜闭环验证
> - 扫描范围：1 入口 + Sensor 115（接线 101 / 孤儿 14）+ BQ 156 + PY 13（ES 11）+ Marker 2 + daily_report/alarm/risk 下游 + 代表 SQL
> - 提取结果：9 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：174 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：已确认入口与关键路径遍历至终态，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: `qpon_rpt_d` 日批最大汇聚：Sensor×115 全指向日 DAG（零 `*_h`、无 Skip）；孤儿×14。经营主链 `detail`(31 日 DELETE+INSERT，voucher `COMPLETED`+`RETURN`，商户维日分区+2999 双路径) → `summary` → `qpon_daily_report`(delta=+8h)。ES×11 旁路均吞异常致 TI 假绿。device_active 约 33 个下游边放大 DWS traffic 裸读与 dwd 倒挂的 SLA。`rpt_store_feature_training_info_h` 已下线注释。
> - **推演约束 (Constraint)**: 下一模块（rpt-h / tag 或收官）必须 (1) 小时消费坚持 Skip，禁止日工厂等 `qpon_*_h`；(2) 勿把日批 voucher 售后 `RETURN` 口径套到小时 voucher_h；(3) 读本层/上游商户维须对账日分区 vs `2999`；(4) 勿把孤儿 Sensor 或 ES 吞异常 SUCCESS 当数据就绪；(5) 评估 device_active 扇出对小时/标签 SLA 的继续放大。
> - **物理锚点 (Anchors)**: `dags/qpon_rpt_d/qpon_rpt_d.py` L166–359 Sensor / L552–553 Marker / L1487–1523 indicator / L2098–2106 wait_3_hours / L2331–2342 ES 边；`tasks/rpt_business_indicator_detail_d.py` DELETE 31 日窗+2999/日分区+COMPLETED/RETURN；`tasks/rpt_business_indicator_summary_d.py` 周月删写；`tasks/rpt_*_es.py` except print；`dags/qpon_daily_report/qpon_daily_report.py` L143–186；`dags/airflow_config/create_external_sensor.py` / `create_external_marker.py`
