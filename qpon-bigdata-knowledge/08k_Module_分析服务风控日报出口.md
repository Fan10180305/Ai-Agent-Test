# 08k 模块深潜：分析服务风控日报出口（analyst-serving）

> 模块 id=`analyst-serving`；权威范围=`dags/`（聚合包：`qpon_analyst_*`、`qpon_analyst_alarm_*`、`qpon_risk_d`、`qpon_daily_report`、`qpon_data_server_d`、`qpon_email_date_d`、`qpon_search_d`；`*_test` 非生产权威）  
> 不重复 Step05 全链；本步钻取 **daily_report execution_delta**、**data_server ES 写出**、**risk/analyst 告警与 GenAI 失败模式**  
> Step08j 接力：(1) 小时上游 Skip；(2) 日批 RETURN ≠ 小时透传；(3) 维表日分区 vs `2999`；(4) Dummy/裸 start/ES 吞异常非就绪；(5) 改 DWS device_active/traffic 须评估 tag∪rpt-d 扇出  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以 `05_module_manifest` id=`analyst-serving`/suffix=`k` + 用户指令为准

> [!SUCCESS] 分析服务风控日报出口 模块深潜闭环验证
> - 扫描范围：入口 DAG×9（analyst_d/h、alarm_d/h、risk、daily_report、data_server、email、search）+ 日工厂 Sensor 合计≈84 活接线 + Skip×3（仅 analyst_h）+ ES Python×6 活 + 告警 Python×2 + GenAI/飞书链 + 代表 SQL
> - 提取结果：10 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：179 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/直连 Sensor/Skip / Step 03 下游=ES·飞书·TT·GCS / Step 04 实体=ADS/data_server/email/risk/rpt 读侧
> - EOF 状态：各入口与代表 tasks（日报/ES/告警/analyst_h/risk feature）已读至终态；无静默截断

---

## A. 模块定位

本聚合模块是数仓 **分析/服务出口层**：日批 ADS 指标、商户看板 ES、邮件市集表、风控特征、L0L1/DAU 告警，以及跨调度 LLM 经营日报。它消费 ODS/DWD/DIM/DWS/RPT 日工厂（及少量小时 Skip），向飞书/TT/阿里云 ES/GCS 投递；**不是**标签宽表主战场，但放大 device_active 与 voucher 口径债。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_analyst_d` / `_h` | Orchestrator | 日 ADS BQ×49 + Sensor×35；时 ADS BQ×2 + Skip×3 |
| `qpon_analyst_alarm_d` / `_h` | Orchestrator | L0L1 分位告警；小时 DAU↔Adjust 对比告警 |
| `qpon_risk_d` | Orchestrator | 风控底座/特征 BQ×46；Sensor×10（含 rpt settlement、device_active） |
| `qpon_daily_report` | Orchestrator | 直连 Sensor→RPT summary；query→分析→GenAI→飞书 |
| `qpon_data_server_d` | Orchestrator | 服务中间表 BQ×10 + ES Python×6 活；Sensor×22 |
| `qpon_email_date_d` | Orchestrator | 邮件市集日/周/月汇总 BQ×21；Sensor×14→ods/dim |
| `qpon_search_store_fea_export` | Orchestrator | 读 `dwd_search_store_fea_inc_d` 导出 GCS 特征 |
| `create_external_sensor` / `create_external_task_skip_sensor_hour` | Factory | 日批 retries=1000；小时 Skip |
| `access_cloud_run_write_aliyun_es` | Downstream | data_server ES 写出 |
| `generate_narrative` / `send_to_feishu` / `TtSend` | Executor | GenAI 叙事、飞书卡片、TT 告警 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_analyst_d`/`_h` parse | Composer | 注册 ADS 日/时批与门控 |
| DAG `qpon_analyst_alarm_{d,h}` parse | Composer | 注册告警 Python + Sensor/延时 |
| DAG `qpon_risk_d` parse | Composer | 注册风控特征扇出 |
| DAG `qpon_daily_report` parse | Composer | 跨调度等 RPT 后出日报 |
| DAG `qpon_data_server_d` parse | Composer | BQ 中间表 + ES 旁路 |
| DAG `qpon_email_date_d` parse | Composer | 邮件市集分区表 |
| DAG `qpon_search_store_fea_export` parse | Composer | 搜索门店特征导出 GCS |
| `ExternalTaskSensor(execution_delta=+8h)` | daily_report | 对齐 `0 18` vs `0 2` |
| `generate_narrative` / `_fallback_narrative` | daily_report | LLM 失败降级模板 |
| `*_to_es` / `access_cloud_run_write_aliyun_es` | data_server | Cloud Run 写/删 ES |

---

## D. 调用链（引用 Step05，不重复追踪）

- ADS 日：`start` → `wait_ods_*`/`wait_dwd_*`/`wait_dim_*`/`wait_dws_device_active_*` → `ads_*`（05 §A.11）。
- ADS 时：`create_external_task_skip_sensor_hour`→`qpon_ods_h`/`qpon_dwd_h` → DAU/trade 小时表。
- 告警日：`TimeDeltaSensor(6.5h)` → Marker 对齐的 `wait_rpt_bq_l0l1_*` → `l0l1_indicators_monitoring_alert_d`→TT。
- 告警时：`create_external_sensor`→`qpon_analyst_h.ads_qpon_analyst_dau_total_inc_h` → Adjust 对比→TT。
- 日报：`wait_rpt_business_indicator_summary_d`(+8h) → `query_metrics` → `compute_analysis` → `generate_narrative` → `send_feishu`。
- 服务：`wait_ods/dwd/dim_*` → BQ → `*_to_es`；另有后端直读 BQ 三表无 ES。
- 风控：`wait_*`（含 `rpt_store_settlement`、`device_active`）→ base/feature/dws_feature 扇出。
- 搜索：`wait_dwd_search_store_fea_inc_d` → Python 导出 `qpon_search` GCS。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | stem==task_id；日报直连 Sensor；Marker→alarm | ✅；alarm_h **误用**日工厂等小时 DAG |
| 03 下游 | ES/飞书/GenAI/TT/GCS | ✅；data_server ES 活×6；delete_es 入口已注释 |
| 04 实体 | ADS/email/data_server/risk；日报读 rpt+dws DAU | ✅；risk 最新特征写分区 `2999-12-31` |
| 06 异步 | daily_report delta=8h；ES retries 靠 DAG | ✅；GenAI 吞异常降级；飞书缺 Variable 硬失败 |
| 07 配置 | `daily_report_gemini_api_key` / `feishu_daily_report_webhook`；告警硬编码 token | ✅ |

**08j 接力五项（本步审计结论）**：
1. **Skip×小时**：`qpon_analyst_h` 上游 **合规** Skip×3。`qpon_analyst_alarm_h` 用 `create_external_sensor`（retries=1000）等 `qpon_analyst_h`——**违规**：日工厂等小时。其余日包 **零** hour-DAG Sensor。
2. **RETURN×voucher**：日批 ADS/`dwd_qpon_trade_order_statistic`/risk `dws_feature_*` 认 `COMPLETED`+`RETURN`（合规）。`analyst_h` 对 `voucher_all_h` **同套** RETURN——**小时透传口径债**。`risk.base_orders_30d` / `email.data_sales_details` 仅 `COMPLETED`（核销/销售语义，勿当「漏 RETURN」统一改）。
3. **维表分区**：`data_server` 读 `dim_product_basic_info`=`2999-12-31`；`dim_store_info` 无日分区过滤（聚合）。`analyst_h` 读 `dim_hour`=`2999`。`risk` **写出** feature 最新快照到 `2999-12-31`（与「读维表 2999」不同语义）。`analyst_d`/`email` **无** 2999。
4. **Dummy/裸 start/ES**：各日包普遍 `start>>start_new_task` **空挂**。`analyst_d` 裸 `start>>` 活任务：`ads_store_traffic`/`ads_module_hits`/`ads_module_list_percentage`/`ads_god_red_dialog_inc_d`/`ads_module_enter_uv_inc_d`。data_server ES：**print 后 `raise`**（TI 会红）——与 rpt-d「吞异常假绿」**相反**，勿混称。
5. **device_active 扇出**：本模块 `analyst_d` Sensor 下游并集 **7（inc）∪2（all）**；`risk`→1；日报 **裸读** `dws_qpon_device_active_info_inc_d`（无 Sensor，靠 RPT summary 间接）。改 DWS 活跃/traffic 须评估 **tag∪rpt-d∪analyst-serving**，勿只看 tag/rpt。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（一句话，可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08k-01 | 改 `qpon_rpt_d` 或 `qpon_daily_report` 任一方 cron，必须重算并更新 `execution_delta`（现 `+8h`） | `qpon_daily_report.wait_rpt_*` | 日报永久空等 |
| C-08k-02 | 等 `qpon_*_h` 必须用 Skip/`create_external_task_skip_sensor_hour`；**禁止**日工厂 `create_external_sensor`(retries=1000)；`alarm_h` 现网违规须改，禁止复制 | `qpon_analyst_alarm_h`；对照 `qpon_analyst_h` Skip | 重试风暴/Skip 当失败 |
| C-08k-03 | 日批完单口径认 `COMPLETED`+`RETURN`；读 `*_voucher_all_h` **禁止**默认同语义（已知债：`ads_qpon_analyst_{dau,trade}_total_inc_h`） | analyst_d vs analyst_h tasks | 小时/日指标假对齐 |
| C-08k-04 | 读维表须声明业务日分区还是 `2999`；risk **写** `2999` 最新快照 ≠ dim 读侧 2999；禁止混读混改 | data_server product 2999；risk dws_feature 写 2999 | 维/特征错代 |
| C-08k-05 | data_server `*_to_es` 失败必须失败 TI（现网 `raise`）；**禁止**从 rpt 复制吞异常 SUCCESS；`delete_es` 已注释禁止无评估恢复双路径 | `*_to_es` except→raise；入口 delete 注释 | ES/BQ 不一致或假绿 |
| C-08k-06 | GenAI：无 key/调用失败走 `_fallback_narrative` 仍 SUCCESS；飞书 Variable 缺失必须失败；禁止把「叙事降级」当成「日报未发送」 | `generate_narrative`；`_task_send_feishu` | 静默模板文案 / 误判投递 |
| C-08k-07 | `alarm_d` 统计日用 `datetime.now()` 非 logical_date——补数/重跑日期错；新增告警禁止复制；须改传 Airflow 日期 | `l0l1_indicators_monitoring_alert_d` | 告警看错天 |
| C-08k-08 | 改 `dws_qpon_device_active_info_*` / traffic 依赖须评估 analyst_d（≥7）+risk+日报裸读，并叠加 tag∪rpt-d（08j/08h） | analyst_d waits；daily_report `DAU_TABLE` | 出口假绿/漏评估 |
| C-08k-09 | `start_new_task`/裸 `start>>` 不得当上游就绪；`search` 的 `on_failure_callback=send_failure_alert_factory`（未调用工厂）禁止当已挂 TT 回调范本 | 各入口空挂；`qpon_search_store_fea_export` | 假语义/失败无 TT |

---

## G. daily_report：execution_delta 与 GenAI/飞书失败模式

**业务背景**：每天 10:00 UTC+8 出经营日报；依赖前一日批 RPT summary（UTC 18:00 调度）。

**实现方式**：直连 `ExternalTaskSensor`：`external_dag_id=qpon_rpt_d`，`task=rpt_business_indicator_summary_d`，`execution_delta=+8h`，`timeout=28800`，`poke=600`，`retries=100`。`report_date=(execution_date-2h).date()`。指标读 `rpt_business_indicator_detail_d` + `dws_qpon_device_active_info_inc_d`（无独立 Sensor）。叙事：`google.genai` + Variable `daily_report_gemini_api_key`；失败/无 key→模板降级。投递：Variable `feishu_daily_report_webhook`，缺则 `ValueError`。

**关键决策点**：
- Sensor — logical_date 对齐靠 +8h → cron 任一侧变更必须改 delta。
- `generate_narrative` — API/JSON 失败 → fallback，任务仍成功。
- `send_to_feishu` — webhook 空 → 硬失败；飞书 `code!=0` → raise；无去重键。
- `EXCHANGE_RATE_OVERRIDE=16801` — 有覆盖时不查维表汇率。

**失败模式**：delta 配错空等 8h×100；RPT 绿但 DAU 表未齐导致日报 DAU 空/旧；LLM 降级被当成「分析正常」；飞书重复跑重复推。

---

## H. data_server ES 写出与维表 2999

**业务背景**：商户看板/券卡/招商/退款统计等 BQ 中间表经 Cloud Run 写入阿里云 ES；20260709 自 dwd 合并。

**实现方式**：BQ `DELETE+INSERT` 业务日后 `*_to_es`：`access_cloud_run_write_aliyun_es(sql, id_field, index)`；`result in {error,retry_error}` 映射 Fail/Exception；外层 `except` **print+raise**。活链：sell_well_rank、refund、merchant_performance、market_dashboard、recruit、coupon_card。`delete_es` 文件在、入口注释。`dim_product_basic_info` 读 `2999-12-31`；traffic 多处裸读日表（有对应 Sensor 的依赖不等价于 traffic 上游已挂满，见 08g）。

**关键决策点**：
- ES 失败 — raise → TI 红（与 rpt `*_es` 吞异常相反）。
- `id` 文档键 — upsert 假定在 Cloud Run 侧（仓内无服务端源码）。
- product 维 — 固定 2999；store 维 — 全表聚合无分区谓词。

**失败模式**：BQ 成功 ES 失败可见；恢复 delete_es 可致双路径；把 rpt 吞异常模式拷入本包会假绿。

---

## I. risk / analyst 告警失败模式

**业务背景**：L0L1 指标分位/南天门一致性日告警；小时 DAU 与 Adjust 对比。

**实现方式**：
- `alarm_d`：延时 6.5h + 日工厂等 rpt L0L1 两表 → Python 查 BQ/NMT → `TtSend`（独立 token `f025661e...`）。查询异常多 `warning`+记入 `alert_messages`，不必然失败 TI。
- `alarm_h`：日工厂等 `analyst_h` DAU → Adjust API + BQ → TT（token `448a3f50...`）。Adjust/BQ 拉取失败常 `return None`，对比仍可能发告警体。
- `analyst_h` 自身 Skip 等小时上游；SQL 对 `voucher_all_h` 用 `COMPLETED`+`RETURN`，`dim_hour=2999`。

**关键决策点**：
- `alarm_d` — `datetime.now()` 定 `stats_date` → 重跑错天。
- `alarm_h` — 日工厂等小时 DAG → 违反 Skip 军规。
- Adjust token — 硬编码在 task；拉取失败降级为 None 而非 fail。

**失败模式**：Marker/Sensor task_id 与 rpt 不一致空等；查询失败仍发「表状态」类告警；小时 Sensor 类型错误导致 skip/失败语义错乱。

---

## J. 出口扇出与空挂（email / search / bare start）

**业务背景**：邮件市集与搜索特征为旁路出口；多包保留 `start_new_task` 空挂习惯。

**实现方式**：`email_date_d` 仅 ODS/DIM 日 Sensor + BQ，无 ES。`search` Sensor→`qpon_dwd_d.dwd_search_store_fea_inc_d`，Python 写 GCS；行数相对上次跌幅≥10% 只打 error 日志、不更新 index（人工门控）。`analyst_d`/`risk`/`data_server`/`email`/`alarm_*` 均有 `start>>start_new_task` 无下游。

**关键决策点**：
- email sales — 仅 `COMPLETED`（销售明细语义）。
- search — `on_failure_callback=send_failure_alert_factory` 未 `()`，与标准 `failure_callback` 不一致。
- 裸 start ADS — 无 Sensor 即跑，TI 绿≠上游齐。

**失败模式**：把空挂 Dummy 当扩展通道；search 回调形态被复制导致失败无 TT；裸跑 ADS 读到半新 traffic。

---

> [!SUCCESS] 分析服务风控日报出口 模块深潜闭环验证
> - 扫描范围：入口×9 + Sensor/Skip/ES/告警/GenAI 代表路径
> - 提取结果：10 个入口方法、9 条衍生约束、4 个业务特性章节（G–J）
> - 全文行数：179 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ / Step 04 ✅
> - EOF 状态：已确认入口与代表 tasks 遍历至终态，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 出口聚合层：日报直连 Sensor `execution_delta=+8h`（`0 18`↔`0 2`）；GenAI 失败降级仍 SUCCESS，飞书缺 Variable 硬失败。data_server ES×6 **raise**（非 rpt 吞异常）。`analyst_h` Skip 合规但对 `voucher_all_h` 套 RETURN；`alarm_h` **日工厂等小时**违规。risk 写特征最新分区 `2999`；data_server 读 product 维 `2999`。device_active 扇出扩展至 analyst_d∪risk∪日报裸读。空挂 `start_new_task` 普遍；search 回调工厂未调用。
> - **推演约束 (Constraint)**: 下一模块（metadata / 收官）必须 (1) 不假设出口层已消化 hour-Skip 军规（alarm_h 反例仍在）；(2) 区分 ES「raise 红」vs「吞异常绿」；(3) 维表/特征 `2999` 读写语义分开审计；(4) 监控/元数据若对账 ADS/DAU，勿把 GenAI fallback 或 alarm `datetime.now()` 当可信业务日；(5) device_active SLA 评估集=**tag∪rpt-d∪analyst-serving**。
> - **物理锚点 (Anchors)**: `dags/qpon_daily_report/qpon_daily_report.py` L143–186；`tasks/generate_narrative.py` L209–243；`dags/qpon_data_server_d/tasks/*_to_es.py` except→raise；`dags/qpon_analyst_alarm_h/qpon_analyst_alarm_h.py` L83；`dags/qpon_analyst_h/qpon_analyst_h.py` L116–121 Skip；`dags/qpon_analyst_h/tasks/ads_qpon_analyst_*_inc_h.py` voucher_h+RETURN；`dags/qpon_analyst_alarm_d/tasks/l0l1_indicators_monitoring_alert_d.py` now()；`dags/qpon_risk_d/tasks/dws_feature/*` 写 2999；`dags/qpon_search_d/qpon_search_store_fea_export.py` L288–299
