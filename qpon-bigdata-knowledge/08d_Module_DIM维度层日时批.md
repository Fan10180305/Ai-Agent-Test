# 08d 模块深潜：DIM维度层日时批（dim-d）

> 模块 id=`dim-d`；权威范围=`dags/`（重点 `dags/qpon_dim_d/` + `dags/qpon_dim_h/`）  
> 不重复 Step05 全量调用链；本步钻取 **维表全量/增量策略**、**ODS Sensor/SkipSensor**、**门店/商品维失败模式**  
> Step08c 接力：所 wait 的 ODS 小时 task 是否仍活注册；订单 MERGE 仅 ON `id` 不可当跨分表唯一；旁路/少表失败可能 TI 仍绿

> [!SUCCESS] DIM维度层日时批 模块深潜闭环验证
> - 扫描范围：2 入口 DAG（dim_d/dim_h）+ 活 BQ 22（日 20 接线+1 孤儿 `dim_date`；小时 2）+ Sensor 工厂 + 代表维表/结算变更 tasks + 上游 ODS 活注册核对
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节
> - 全文行数：187 行（≤ 400 行）
> - 前序验证：Step 02 契约=stem/task_id+跨 DAG wait / Step 03 下游=dwd/rpt 等 dim / Step 04 实体=`qpon_dim_d.*`（小时写同 dataset）
> - EOF 状态：`qpon_dim_d.py`/`qpon_dim_h.py` 与门店/商品/小时/结算代表 tasks 已读至关键终态；无静默截断

---

## A. 模块定位

`qpon_dim_d`（日批 `0 18 * * *`）与 `qpon_dim_h`（小时 `10 * * * *`）共同构成 **DIM 维度层日时批**：从 ODS（及少量 DWD）拼装门店/商户/商品等维表与日历/结算变更维，写入 dataset `qpon_dim_d`（小时表带 `_h`），供 DWD/RPT/TAG 等跨 DAG 等待；本包无 ES/飞书/Adjust 旁路。

---

## B. 核心类清单

| 类名 / 模块 | 类型 | 职责 |
|---|---|---|
| `qpon_dim_d` / `qpon_dim_d.py` | Orchestrator | 日批 DAG；`create_external_sensor`×36（接线 29）+ BQ 维表扇出 |
| `qpon_dim_h` / `qpon_dim_h.py` | Orchestrator | 小时 DAG；`create_external_task_skip_sensor_hour`×8→`qpon_ods_h`；BQ×2 |
| `create_composer_bq_task` | Factory | 动态 import stem→BQ SQL |
| `create_external_sensor` | Factory/Sensor | 日批等 ODS/DWD；`allowed_states=['success']`；retries=1000 |
| `create_external_task_skip_sensor_hour` / `ExternalTaskSkipSensor` | Factory/Sensor | 小时等 ODS；同 `run_id` 透传 SUCCESS/SKIPPED/FAILED |
| `dim_store_info` / `dim_store` / `dim_store_info_h` | Executor | 门店主维（全量 TRUNCATE / 分区日快照 / 小时分区） |
| `dim_product_basic_info` / `dim_merchant_basic_info(_h)` | Executor | 商品/商户分区日（+2999 当前分区）与小时商户维 |
| `dim_*_settlement_change_d` / `dim_daytime_info` | Executor | 结算变更维（依赖 DWD）+ 日历维 |
| `qpon_dwd_d` / `qpon_dwd_h` | Downstream Caller | Sensor 等本层 `dim_store_info`/`dim_product_*`/`dim_*_h` 等 |

---

## C. 入口方法

| 入口方法 | 调用方 | 一句话描述 |
|---|---|---|
| DAG `qpon_dim_d` parse | Composer | 注册日批维表与跨 DAG Sensor |
| DAG `qpon_dim_h` parse | Composer | 注册小时门店/商户维与 SkipSensor |
| `create_composer_bq_task(...)` | 两入口 | 绑定 `warehouse_layer` + stem SQL |
| `create_external_sensor(..., qpon_ods_d\|qpon_dwd_d\|…)` | `qpon_dim_d.py` | 日批门控；仅 SUCCESS |
| `create_external_task_skip_sensor_hour(..., qpon_ods_h, …)` | `qpon_dim_h.py` | 小时门控；透传 SKIPPED |
| `send_failure_alert_factory(send_url)` | 多数任务 callback | 硬编码 yzjtoken（继承 08a） |
| `create_external_sensor(..., qpon_dim_h, …)` | `qpon_dwd_h` | **下游**用日工厂等小时维（非本包实现；已知技术债） |

---

## D. 调用链（引用 Step05，不重复追踪）

- 日批：`start` → 多 `wait_ods_*`（及结算链 `wait_dwd_*`）→ `dim_store_info` / `dim_product_basic_info` / `dim_merchant_basic_info` / `dim_store` / 结算变更等（`05` §A.4）。
- 小时：`start` → SkipSensor×8→`qpon_ods_h` → `dim_store_info_h` / `dim_merchant_basic_info_h`。
- 下游：`qpon_dwd_d`/`qpon_rpt_d` 等等日维；`qpon_dwd_h` 等 `dim_*_h`（日工厂 Sensor，非 Skip）。

---

## E. 前序步骤验证

| Step | 与本模块相关的结论 | 本步核对 |
|---|---|---|
| 02 契约 | dim_d Sensor 边重；dim_h→ods_h×8；层倒挂 dim→dwd | ✅；结算三任务仍 `wait_dwd_*`；孤儿 Sensor×7 + 孤儿 BQ `dim_date` |
| 03 下游 | dwd/rpt/tag 读 `qpon_dim_d`；跨 DAG 等 dim | ✅ |
| 04 实体 | `dim_store_info`=TRUNCATE；小时写同 dataset `*_h` | ✅；商品另写 `2999-12-31` 当前分区 |
| 06 异步 | 日 Sensor retries=1000；小时 Skip retries=20 | ✅；dim_h **未**误用日工厂等小时（对比 dwd_h） |
| 07 配置 | TT 硬编码；Sensor timeout 日 64800 / 小时 Skip 7200 | ✅ 继承 |

**08c 接力三项**：
1. 活注册：`qpon_dim_h` 所 wait 的 8 个 `qpon_ods_h` task **全部仍活注册**（MISSING=0）。日批接线 29 个上游（ODS/DWD）活注册 MISSING=0。
2. MERGE 仅 ON `id`：本模块维表主路径为 TRUNCATE/DELETE+INSERT/MERGE 业务键；**读** ODS 订单分表贴源时仍不可假设跨分表 `id` 唯一（上游债，JOIN 前须知）。
3. TI 绿≠数对：孤儿 Sensor 可单独 SUCCESS；结算维只等 DWD TI 绿不够——须核对 DWD 分区行数/结算字段；`dim_store_grid` 现网 DELETE 被注释，INSERT 可叠行。

---

## F. 衍生约束清单

| 约束 ID | 约束内容（可执行） | 代码证据 | 违反后果 |
|---|---|---|---|
| C-08d-01 | 小时维等 ODS：必须用 `create_external_task_skip_sensor_hour`；禁止新增 `create_external_sensor`（retries=1000）套 `qpon_ods_h`/`qpon_dim_h`——`qpon_dwd_h` 等 dim_h 为已知技术债，禁止复制 | `qpon_dim_h` Skip vs `qpon_dwd_h` ExternalTaskSensor→dim_h | 跳过语义丢失；重试风暴 |
| C-08d-02 | 日批维等 ODS：用 `create_external_sensor`；下线维任务须**同时**注释工厂注册、全部 `wait_*` 创建、全部 `>>` 边；禁止只注释 `>>` 而留下活 Sensor（现网孤儿×7 为已知技术债） | `qpon_dim_d` 活 create vs 注释依赖块 | 孤儿 Sensor 占槽/误等已下线上游 |
| C-08d-03 | `dim_store_info` 全量覆盖：保持 `TRUNCATE`+`INSERT`；禁止改成「仅 MERGE 增量」而不评估下游无分区读法 | `dim_store_info` | 脏行残留或下游读到半刷新 |
| C-08d-04 | 分区日维（商品/商户/门店宽表等）：幂等键=`partition_date`（业务日=`execution_date+1`）；须 `DELETE` 当日分区再 `INSERT`；商品另删写 `2999-12-31` 当前镜像须同事务语义保持 | `dim_product_basic_info`；`dim_merchant_basic_info`；`dim_store` | 分区重复或「当前分区」过期 |
| C-08d-05 | 小时维分区：`DELETE/INSERT` 的 `partition_date` 必须用 `execution_date.add(hours=7)` 对齐业务日；禁止照抄日批 `add(days=1)` 或 MERGE 近窗 −5h | `dim_store_info_h`；`dim_merchant_basic_info_h` | 错日分区或与 ODS `_h` 对不齐 |
| C-08d-06 | 禁止新增 dim→dwd / dim→dws 层倒挂 Sensor；现网结算三任务等 DWD、设备维读 DWD 无 Sensor 为已知技术债，新增禁止复制 | `wait_dwd_*`→settlement；`dim_device_latest_all_d` 读 `dwd_qpon_event_traffic_inc_d` | 调度环/竞态空窗 |
| C-08d-07 | 门店 `is_formal` 黑名单/测试名过滤变更须双改日表 `dim_store_info` 与小时 `dim_store_info_h`（硬编码 store_id/merchant_id 列表） | 两文件 `is_formal` CASE | 日时批正式标不一致 |
| C-08d-08 | `dim_store_grid`：禁止在 DELETE 注释状态下继续只 `INSERT` 扩字段而不恢复去重策略（已知技术债） | `dim_store_grid` 注释 `#delete` | 表膨胀、grid 重复 |
| C-08d-09 | 新增 `failure_callback` 的 `send_url` 必须走 Variable；禁止再硬编码 yzjtoken（已知技术债） | `qpon_dim_d/h.send_url` | Token 不可吊销；TT 失败可静默 |

---

## G. 维表全量 / 增量策略

**业务背景**：DIM 同时服务「无分区全量主维」「按业务日分区快照」「MERGE 缓变」「日历/结算多粒度重算」四类消费；策略选错会导致下游无分区读脏或分区空洞。

**实现方式**（按活接线任务归类）：

| 策略 | 代表任务 | 机制 |
|---|---|---|
| 全表覆盖 | `dim_store_info`；`dim_task_play_info`（`DELETE WHERE 1=1`） | TRUNCATE/全删 + INSERT |
| 日分区重刷 | `dim_product_basic_info`、`dim_merchant_basic_info`、`dim_store`、`dim_mall_basic_info`、`dim_lead_info_all_d`、小时 `*_h` | `DELETE partition_date=业务日` + INSERT；商品再刷 `2999-12-31` |
| MERGE 缓变 | `dim_coupon_template`、`dim_page`、`dim_unit_info`、`dim_position_info`、`dim_bd_*`、`dim_device_latest_all_d` | ON 业务键 UPSERT |
| 多 tag 重算 | `dim_*_settlement_change_d` | 按日/周/月末 `tag_type` 条件 DELETE + 重算 INSERT |
| 日历窗 | `dim_daytime_info` | 删未来窗 + 生成约 1 年日期属性 |

**关键决策点**：
- `dim_store_info` — 无 `partition_date` 删除键 → 只能全表 TRUNCATE，失败中断会空表窗口。
- `dim_product_basic_info` — 日分区成功后是否写 `2999-12-31` → 服务「当前商品」读路径。
- `dim_device_latest_all_d` — MERGE ON `device_id`，固定目标分区 `2999-12-31`；源窗=当日 DWD 事件。
- `dim_store_info_h` — 以 `ods_store_h` 小时增量 ∪ `ods_store_info` 近 2 日最大分区补缺（`t2.store_id is null`）→ 小时不全量扫日表。

**失败模式**：TRUNCATE 后 INSERT 失败→空维；只跑商品日分区未跑 2999→当前镜像旧；MERGE 键冲突/空源→静默不更新；结算 DELETE 条件含周月末，错日重跑可能漏删历史 tag。

---

## H. ODS Sensor / SkipSensor 用法

**业务背景**：日批要强等到 ODS SUCCESS；小时批须透传上游 SKIPPED，避免「上游跳过、下游硬等 timeout」。

**实现方式**：
- 日：`create_external_sensor` → `ExternalTaskSensor`，`allowed_states=['success']`，`failed_states=['failed']`，timeout=64800，retries=1000。
- 时：`create_external_task_skip_sensor_hour` → `ExternalTaskSkipSensor.poke`：SUCCESS→通过；SKIPPED→`AirflowSkipException`；FAILED→失败；同 `context['run_id']` 对齐。
- `qpon_dim_h` 导入了 `create_external_sensor` 但**业务 wait 全走 Skip**（合规模板）。

**关键决策点**：
- `ExternalTaskSkipSensor.poke` — `ti is None` → 继续等；非终态 → False。
- `qpon_dim_d` — 门店维扇入 13 个 ODS wait；商户维额外依赖 `dim_store_info`（DAG 内边）。
- 孤儿活 Sensor（注释掉下游维后未删 create）：`wait_ods_t_act_*`×3、`wait_ods_t_coupon_code*`×2、`wait_dwd_qpon_mkt_bargain_record_inc_d`、`wait_dws_qpon_device_active_info_inc_d`。

**失败模式**：日 Sensor 上游失败→retries 风暴；小时上游 SKIPPED 若误用日工厂→不识别 skip、占槽到 timeout；孤儿 Sensor SUCCESS≠任何维表已刷新；`dim_date` 已注册工厂但无 `>>` 边→任务游离。

---

## I. 门店维失败模式（日 + 小时）

**业务背景**：门店是订单/流量/结算的核心 JOIN 维；日表全量、小时表近实时，过滤规则必须一致。

**实现方式**：
- 日 `dim_store_info`：多 ODS JOIN + `is_formal` 硬编码黑名单/测试名；`TRUNCATE` 全刷。
- 日 `dim_store`：更宽字段（含 grid、渠道、AES 解密电话等）；`DELETE` 业务日 + INSERT；依赖 `dim_store_grid`。
- 小时 `dim_store_info_h`：等 5 个 ODS SkipSensor；写 `qpon_dim_d.dim_store_info_h`；`hours=+7` 分区；用日表 `ods_store_info` 补「本小时 `_h` 未出现」的门店。

**关键决策点**：
- `dim_store_info` / `dim_store_info_h` — `is_formal` 条件是否命中 → 0/1 正式标。
- `dim_store_info_h` — `ods_store_h` 有行 vs 仅日表补缺 → UNION 两支。
- `dim_store` — 依赖 `dim_store_grid` 是否先成功 → 网格字段空/任务阻塞。

**失败模式排查**：
1. 维表空或行数骤降 → 查当日 ODS wait 是否全 SUCCESS；再查 TRUNCATE/DELETE 后 INSERT 作业错误。
2. 小时有门店、日报 `is_formal` 不一致 → diff 两文件黑名单字面量。
3. 小时缺店 → 查 `ods_store_h` 分区（+7h）与 `ods_store_info` max(partition_date) 是否落后超过 2 日补缺窗。
4. `dim_store_grid` 行数单调涨 → 确认 DELETE 仍被注释。

---

## J. 商品维与结算变更失败模式

**业务背景**：商品维喂 DWD/券卡；结算变更维按日/周/月 tag 统计有效商品/门店，依赖 DWD 明细（层倒挂）。

**实现方式**：
- `dim_product_basic_info`：等 mall/product/poi_category；日分区 DELETE+INSERT，并复制到 `2999-12-31`；绑定 `ods_t_data_tag_bind`（tag_id='5'）serving 标签。
- `dim_*_settlement_change_d`：等 `dim_daytime_info` + `dwd_product_store_detail_d`（商户结算另等 `dwd_store_info_detail_d`、`dim_merchant_basic_info`；商品结算另等 `ods_t_life_sku`）。

**关键决策点**：
- `dim_product_basic_info` — 第二段是否写 2999 → 当前商品服务读。
- `dim_store_settlement_change_d` — DELETE 条件含日/周/月 `tag_type` 与对应期末日 → 重跑范围。
- 调度 — DWD 未绿 → Sensor 阻塞；DWD 绿但明细缺结算字段 → DIM 仍绿、指标偏低。

**失败模式排查**：
1. 商品日分区有、2999 旧 → 查同 SQL 第二段 DELETE/INSERT 是否执行失败。
2. 结算维「TI 全绿、报表仍错」→ **勿只看 Sensor/任务绿**：对账 DWD `dwd_product_store_detail_d` 当日行数与结算类型分布（呼应 08c 结算少表教训）。
3. 商户结算缺数 → 查 `dim_merchant_basic_info` 与两个 DWD wait 是否同日对齐。

---

> [!SUCCESS] DIM维度层日时批 模块深潜闭环验证
> - 扫描范围：2 入口 DAG + 活接线 Sensor 29 + 孤儿 Sensor 7 + 活接线 BQ 20 + 孤儿 BQ 1（`dim_date`）+ 小时 Skip×8 + 代表维/结算 SQL
> - 提取结果：7 个入口方法、9 条衍生约束、4 个业务特性章节（G~J）
> - 全文行数：187 行（≤ 400 行）
> - 前序验证：Step 02 倒挂/契约成立 / Step 03 下游等 dim 成立 / Step 04 TRUNCATE 与 `*_h` 同 dataset 成立
> - EOF 状态：已确认遍历入口与关键 tasks 终态，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: DIM 日批主路径=ODS Sensor→分区/全量维；小时=SkipSensor→`dim_*_h`（合规）。结算三任务 **dim→dwd 倒挂**；`dim_device_latest_all_d` **读 DWD 无 wait**；孤儿 Sensor×7 + `dim_date` 无边仍注册；`dim_store_grid` DELETE 注释仅 INSERT；`qpon_dwd_h` 用日工厂 Sensor 等 `dim_*_h`（非 Skip）。
> - **推演约束 (Constraint)**: 下一模块（dwd-d/h）必须 (1) 核对所 wait 的 dim task 是否仍活接线（含治理注释）；(2) **禁止复制**「日工厂 `create_external_sensor` 等小时 dim/ods」——以 `qpon_dim_h` Skip 为模板；(3) 消费结算/商品维时勿只看 TI 绿，须对账分区与 `2999-12-31` 当前镜像；(4) 订单类 JOIN 勿假设 ODS MERGE ON `id` 跨分表唯一。
> - **物理锚点 (Anchors)**: `dags/qpon_dim_d/qpon_dim_d.py` L119-174/L183-229/L241-421；`dags/qpon_dim_h/qpon_dim_h.py` L94-144；`dags/qpon_dim_d/tasks/dim_store_info.py` TRUNCATE；`dim_product_basic_info.py` 日+2999；`dim_store_info_h.py` hours=+7；`dim_store_grid.py` 注释 DELETE；`dags/airflow_config/create_external_sensor.py` ExternalTaskSkipSensor.poke；`dags/qpon_dwd_h/qpon_dwd_h.py` wait_dim_*_h
