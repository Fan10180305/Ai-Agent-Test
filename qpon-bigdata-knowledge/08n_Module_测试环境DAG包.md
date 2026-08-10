# 08n 模块深潜：测试环境DAG包（test-dags）

> 模块 id=`test-dags`；权威范围=`dags/`（`qpon_ods_d_test` / `qpon_dwd_d_test` / `qpon_tag_d_test` / `qpon_data_server_d_test` / `qpon_email_date_d_test` / `qpon_review_score_test` / `qpon_test_d`）  
> 不重复 Step05 全链；本步钻取 **Sensor 是否误连生产**、**命名漂移/空壳迁徙**、**与生产并行写读风险**  
> Step08m 接力：(1) Unpause+`gcp_alter`；(2) 先 `etl_alter`；(3) 吞绿 vs ES raise；(4) 禁止旁路时钟当 ADS 日；(5) device_active=tag∪rpt-d∪analyst-serving；(6) alarm_h 债仍开；(7) 测试 Sensor 勿连 ephemeral/Adjust  
> 注：`.tmp/next-prompt.md` / `current_module.json` 本轮缺失；以用户指令 id=`test-dags`/suffix=`n` + `step-08-test-dags_prompt.md` + 05 §A.14 为准  
> **本包为 Step08 最后一模块**；RELAY 面向收官 final-assembly

> [!SUCCESS] 测试环境DAG包 模块深潜闭环验证
> - 扫描范围：DAG 入口×7 + 活注册任务抽样（ODS 订单/评价、data_server 性能/优惠券卡、tag 三活任务、email 结算、dwd check、test_fanisy）+ Sensor 全量审计
> - 提取结果：10 个入口方法、9 条衍生约束、3 个业务特性章节
> - 全文行数：159 行（≤ 400 行）
> - 前序验证：Step 02 Sensor 契约 / Step 03 TT·BQ / Step 04 test 表后缀 / Step 05 A.14
> - EOF 状态：七入口已读至 EOF；无静默截断

---

## A. 模块定位

`test-dags` 是仓内**测试环境并行镜像子集**：从 `test_env*` / `test_env1_*` 贴源，落 `*_test*` 表（多数仍落在生产 dataset `qpon_ods_d`/`qpon_dwd_d`/`qpon_data_server`），供联调邮件市集与商户看板 SQL；**不参与**生产 device_active / ADS / 标签主扇出，也不接 Spark ephemeral / Adjust。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_ods_d_test` | Orchestrator | 日批 `0 18`；TimeDelta+2h 后门店/结算/评价 ODS 测表 |
| `qpon_dwd_d_test` | Orchestrator | 业务任务已迁出；仅留 `check_table_is_exists_test01`；Sensor 定义但未接线 |
| `qpon_data_server_d_test` | Orchestrator | 承接原 dwd_test + 评价明细；Sensor→ods_test；混读生产埋点 |
| `qpon_email_date_d_test` | Orchestrator | 邮件市集测库 `qpon_email_date_d_test`；Sensor→ods_test + 生产 dim |
| `qpon_tag_d_test` | Orchestrator | 仅注册 3 任务；Sensor→生产 `qpon_dim_d.dim_store`；37 孤儿 SQL |
| `qpon_review_score_test` | Orchestrator | 20260709 后**空壳**（任务迁至 ods_test / data_server_test） |
| `qpon_test_d` | Orchestrator | 小时 `10 * * * *` 沙盒；SkipSensor→生产 `qpon_dwd_h` |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_ods_d_test` parse | Composer | 注册 13 活 ODS 测任务（market_0_3/settle/review） |
| DAG `qpon_dwd_d_test` parse | Composer | 仅注册存在性检查；业务 create 已注释 |
| DAG `qpon_data_server_d_test` parse | Composer | 注册 9 活 BQ（含迁入的 dwd_*_test） |
| DAG `qpon_email_date_d_test` parse | Composer | 注册日/周/月邮件测表扇出 |
| DAG `qpon_tag_d_test` parse | Composer | 注册 storeid 基表 + facilities/categories |
| DAG `qpon_review_score_test` parse | Composer | 仅 `start`/`start_new_task` Dummy |
| DAG `qpon_test_d` parse | Composer | 注册 `test_fanisy_20251107` + 小时 Skip 实验链 |
| `ods_*_test_all_d` / settle / review | ods_test | MERGE/INSERT 测 ODS |
| `dwd_*_test` / `data_server_*_test` | data_server_test | DELETE+INSERT 测中间表 |
| `tag_qpon_base_storeid_all_d` 等 | tag_test | 写 `qpon_services_test` |

---

## D. 调用链（引用 Step05，不重复追踪）

- 骨架：05 §A.14 — 生产镜像子集；Sensor **应**指向 test 上游。
- 实测活链：`qpon_ods_d_test`（TimeDelta）→ `qpon_data_server_d_test` / `qpon_email_date_d_test`（ExternalSensor→`qpon_ods_d_test`）。
- 旁路：`qpon_tag_d_test` / email / data_server 均 **额外** Sensor 生产 `qpon_dim_d`；`qpon_test_d` Skip→`qpon_dwd_h.check_allowed_hours_is_run`（与 05 悬空小时债同锚点）。
- **无** Sensor→`spark_ug_rch_send_record_ephemeral` / `Qpon_Adjust_Raw_Data`（08m 约束(7) 本包通过）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | ExternalTaskSensor / SkipSensor 工厂 | ✅；test 复用同一工厂；dim/dwd_h 指向生产 dag_id |
| 03 下游 | TT webhook、BQ；无 ES Cloud Run 于测试包 | ✅；七包 **0** ES/Cloud Run 写出；硬编码 TT 同生产轨 |
| 04 实体 | `*_test_all_d` / `*_test` / `qpon_services_test` / `qpon_email_date_d_test` | ✅；源=`test_env*`；目标 dataset 常为生产层名+表后缀 |
| 06 异步 | Sensor retries=1000；TimeDelta 延时 | ✅；ods/email 用 TimeDelta，非业务日时钟 |
| 07 配置 | 测试与生产同仓同 cron；硬编码 token | ✅；无 Unpause / 无 `etl_alter`/`gcp_alter` 消费 |

**08m 接力回执（本包消化情况）**：(7) **已核**——无 ephemeral/Adjust Sensor。**(1)(2)(3)(4)(5)(6) 未消化**——本包无 metadata Unpause、无 Variable 告警接线、无 ES 任务、无 ADS 日对账、无 device_active 生产扇出、无 alarm_h。收官须保留全部开放债。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08n-01 | 测试包 ExternalSensor 的 `external_dag_id` 须为 `*_test`（或明确无测维时文档化例外）；**禁止**新增对 `spark_*ephemeral` / `Qpon_Adjust_Raw_Data` / 生产 ODS 主任务的 Sensor | `qpon_*_test.py` Sensor 段；对照 08m C-08m-01 | 测链挂生产水位或等错链 |
| C-08n-02 | 已知技术债：`wait_dim_store`/`wait_dim_daytime_info` 指向生产 `qpon_dim_d`——新增同类禁止复制；改测维须先建测 dim DAG 再改 Sensor | `qpon_tag_d_test`；`qpon_email_date_d_test`；`qpon_data_server_d_test` | 测跑依赖生产维表 SLA；假隔离 |
| C-08n-03 | `qpon_test_d` SkipSensor→`qpon_dwd_h.check_allowed_hours_is_run` 仅为实验；禁止当测环境小时门禁模板；勿假设该上游稳定绿 | `qpon_test_d.wait_check_allowed_hours_is_run` | 沙盒与生产小时债耦合；长期 reschedule |
| C-08n-04 | 表隔离幂等键=目标表名后缀 `_test`/`_test_all_d`（同 dataset）；禁止把测 SQL 的 `insert_table_id` 改成无后缀生产表名 | `ods_*_test_all_d`；`dwd_*_test`；`data_server_*_test` | 覆盖生产分区 |
| C-08n-05 | 混读约束：测任务可读 `test_env*` + 测 ODS；**禁止**再扩大对生产 `ods_qpon_event_message` / `dwd_qpon_event_traffic_inc_d` / `qpon_services_prod` 的依赖（已知债，见 performance/coupon/orphan tag） | `dwd_merchant_daily_performance_test`；`dwd_merchant_daily_coupon_card_data_test`；orphan `active_uid_*` | 测指标被生产埋点污染；误判联调成功 |
| C-08n-06 | 空壳/迁徙：`qpon_review_score_test`、`qpon_dwd_d_test` 业务 create 已注释——新评价/商户测任务须挂 `ods_d_test`/`data_server_d_test`，禁止在空壳 DAG 复活双写 | 两入口 20260709 注释 | 双 DAG 同表竞态 |
| C-08n-07 | `qpon_tag_d_test` 仅 3 活任务；tasks 下 37 孤儿文件禁止静默 `create_composer_bq_task` 批量挂回（多文件读 `qpon_services_prod`+生产 device_active） | `qpon_tag_d_test.py` vs `tasks/*` | 测标签扇出撞生产标签源 |
| C-08n-08 | 告警仍硬编码 `TtSend`；治理服从 08l/08m：先接线 `etl_alter`+TeamtalkRobot 再删硬编码；测包不得新增第三条 webhook | 七入口 `send_url` | 多轨告警；Variable 假覆盖 |
| C-08n-09 | 本包无 ES：勿用测 data_server「BQ SUCCESS」推断生产 ES raise 红路径已验；吞绿对照仍以 meta/ops `task_write_es` vs 生产 data_server ES 为准 | 测包 0 ES 引用；对照 08k/08m | 假绿放行 ES 出口 |

---

## G. Sensor 误连与隔离边界

**业务背景**：测链应自洽等待测上游，避免与生产 ephemeral/Adjust/ODS 主链抢水位；维表是否允许共用生产需显式决策。

**实现方式**：
- **合规**：email / data_server /（定义未用的）dwd_test → `external_dag_id=qpon_ods_d_test`。
- **ods_test**：无 ExternalSensor；`TimeDeltaSensor(hours=2)` 作 CDC 缓冲。
- **违规/债**：tag→`qpon_dim_d.dim_store`；email+data_server→`qpon_dim_d.dim_daytime_info`；test_d→`qpon_dwd_h` Skip。
- **通过 08m-(7)**：全包 grep 无 ephemeral/Adjust dag_id。

**关键决策点**：
- `create_external_sensor(..., "qpon_ods_d_test", ...)` — 测→测 → 隔离正确。
- `create_external_sensor(..., "qpon_dim_d", ...)` — 测→产维 → 调度耦合生产 dim 日批。
- `create_external_task_skip_sensor_hour(..., "qpon_dwd_h", "check_allowed_hours_is_run")` — 实验门禁 → 继承生产小时悬空风险。
- ods `wait_2_hours` — 墙钟延时 → **不是** ADS/业务日（禁止对账用）。

**失败模式**：生产 dim 失败/延迟→测 email/tag/data_server 跟着黄；ods_test 暂停→下游 Sensor retries=1000 占槽；误加 Adjust Sensor 会与 08m 活链缠死。排障：先看 `external_dag_id` 是否含 `_test`，再查目标表是否 `_test` 后缀。

---

## H. 命名漂移、空壳与任务迁徙

**业务背景**：20260709 将「数据服务」相关测任务合并进 `qpon_data_server_d_test`，评价 ODS 进 `qpon_ods_d_test`，留下空壳与孤儿文件。

**实现方式**：
- `qpon_review_score_test`：全部 create/依赖注释；磁盘仍留 4 份与 ods/data_server 重复的任务文件。
- `qpon_dwd_d_test`：五类 dwd_* create 注释；Sensor 仍定义但依赖边注释；活任务仅 `check_table_is_exists_test01`（查**生产** `dwd_product_voucher_finance_detail_inc_d`）。
- `qpon_tag_d_test`：注册 `tag_qpon_base_storeid_all_d` / `store_facilities` / `store_categoies`（拼写漂移 categories→categoies）；userid/活跃天数/DAY* 等 37 文件未注册。
- `ods_d_test/tasks/digital_food_market/` 下 product* 未在入口注册（仅 `digital_food_market_0_3` 活）。

**关键决策点**：
- 迁徙注释「合并 ADG」— 权威活链以 data_server_test + ods_test 为准。
- `store_categoies` — 文件名/task_id 拼写错误已固化；改名须同步 BQ 与 Composer。
- `check_table_is_exists_test01` — 存在性检查绑生产财务明细 → 测 DAG 绿≠测数据就绪。

**失败模式**：在空壳 DAG 恢复旧 create → 与 data_server_test 双跑同表；把 orphan tag 挂回 → 读 `qpon_services_prod` 污染测库。排障：以入口 `create_composer_*` 活调用为准，不以 tasks 目录文件数为准。

---

## I. 与生产并行风险

**业务背景**：测包与生产同 GCP 项目、多数同 `0 18 * * *`，靠表名后缀与 `test_env*` 源隔离，而非独立项目/独立 Composer。

**实现方式**：源 `test_env1_digital_food_market` / `test_env_digital_food_settle` / `test_env_qpon_review` 等 → 目标 `qpon_ods_d.ods_*_test_all_d`、`qpon_dwd_d.dwd_*_test`、`qpon_data_server.data_server_*_test`、`qpon_services_test`、`qpon_email_date_d_test.*`。并行风险点：同 dataset 扫描/权限；performance/coupon **读生产事件**；tag 活任务读生产 `dim_store` 写测库；硬编码 TT 与生产共告警通道。

**关键决策点**：
- `insert_dataset_id="qpon_ods_d"` + `*_test_all_d` — 后缀隔离 → 改名丢后缀即事故。
- `dwd_merchant_daily_performance_test` 读 `ods_qpon_event_message` — 测商户看板混生产流量 → 联调数字不可外推。
- 无 ES — 测包验不了生产 ES raise；`task_write_es` 吞绿仍属 ops（08m）。
- schedule 对齐生产 — 槽位/配额竞争，非逻辑覆盖。

**失败模式**：DELETE 条件写错表名；权限账号可写无后缀表；告警风暴与生产混淆。排障：核对 `insert_table_id` 后缀 + Sensor dag_id + 源是否 `test_env*`。

---

> [!SUCCESS] 测试环境DAG包 模块深潜闭环验证
> - 扫描范围：7 入口 DAG + Sensor 全量 + 代表 tasks（ODS/tag/data_server/email/dwd check/test_d）+ 孤儿计数（tag 37）
> - 提取结果：10 个入口方法、9 条衍生约束、3 个业务特性章节（G–I）
> - 全文行数：159 行（≤ 400 行）
> - 前序验证：Step 02 ✅ / Step 03 ✅ 无测 ES / Step 04 ✅ 表后缀 / Step 06 ✅ / Step 07 ✅ 硬编码 TT
> - EOF 状态：已确认七入口遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束（面向 final-assembly 收官）
> - **物理事实 (Context)**: Step08 模块链 a–n 已齐。测试包：**无** ephemeral/Adjust Sensor；**有**生产 dim Sensor（tag/email/data_server）与 dwd_h Skip（test_d）；隔离=表后缀非独立 dataset；review/dwd_test 空壳+tag 37 孤儿；测 data_server **无 ES**（不可替代生产 ES raise 审计）；硬编码 TT 未接 `etl_alter`。08l/08m/08k 开放债（Unpause+`gcp_alter`、etl 接线、meta/ops 吞绿 vs ES raise、不可信旁路时钟、device_active 三方、alarm_h 小时 Skip）**全程未被测试包消化**。
> - **推演约束 (Constraint)**: 收官 final-assembly 必须 (1) 核对生产 Unpause+`gcp_alter_webhook_url` 非空；(2) 告警治理优先接线 `etl_alter`+TeamtalkRobot 再删硬编码（含测包同源 token）；(3) 区分 meta/ops「吞绿」与生产 data_server「ES raise 红」——**禁止**用测包 BQ 绿代替；(4) 对账 ADS/DAU **禁止**用 meta/监控/GenAI/alarm/`data_options.current_date`/测包 TimeDelta 墙钟；(5) device_active SLA 评估集仍为 **tag∪rpt-d∪analyst-serving**（不含 test-dags）；(6) 勿假设 hour-Skip 已闭环（alarm_h + `qpon_test_d→dwd_h` 反例仍在）；(7) 汇总结论须单列：测包对生产 dim 的 Sensor 债与表后缀隔离红线。
> - **物理锚点 (Anchors)**: `dags/qpon_ods_d_test/qpon_ods_d_test.py` L86–175；`dags/qpon_data_server_d_test/qpon_data_server_d_test.py` L105–203；`dags/qpon_email_date_d_test/qpon_email_date_d_test.py` L157–168；`dags/qpon_tag_d_test/qpon_tag_d_test.py` L163–207；`dags/qpon_dwd_d_test/qpon_dwd_d_test.py` L107–173；`dags/qpon_review_score_test/qpon_review_score_test.py` L133–160；`dags/qpon_test_d/qpon_test_d.py` L112–149；`dags/qpon_ods_d_test/tasks/digital_food_market_0_3/ods_t_life_order_test_all_d.py` L10–19；`dags/qpon_data_server_d_test/tasks/dwd_merchant_daily_performance_test.py`（混读 `ods_qpon_event_message`）
