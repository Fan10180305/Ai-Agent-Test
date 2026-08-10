# 00_Master_Catalog — qpon-bigdata 知识库总目录

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）  
> Legacy：NO_DOCS  
> 模块清单权威：`05_module_manifest.json`（14 模块 = 08a–08n）

---

## 1. 项目概览

`qpon-bigdata` 是 Qpon（digital food）在 GCP Composer 上的 **数仓 ETL / 标签 / 报表 / 服务出口编排仓**：以 `dags/` 内分层 DAG（ODS→DIM→DWD→DWS→RPT/TAG/Analyst）驱动 BigQuery SQL，旁路含 Dataproc/Spark、Cloud Run→阿里云 ES、飞书/Adjust 接入、TeamTalk 告警与元数据/GCP 监控。业务事实权威仅在 `dags/`，不以 `scripts/` 或其它知识目录作契约来源。

---

## 2. 知识库文件清单

### 技术维度（横向切片）

- **Legacy_qpon-bigdata_Claims.md** — 旧文档声称
  - 用途：交叉验证基线；当前 `LEGACY_STATUS=NO_DOCS`（无 old-readme）
  - 适用场景：验证「文档是否曾声称某能力」；本仓一律以代码为准

- **01_Module_Skeleton_and_Stack.md** — 模块骨架与技术栈
  - 用途：`dags/` 包树、共享库依赖、中间件雷达、9 项 Red Flags
  - 适用场景：新人上手、Composer/依赖升级、架构腐化排查

- **02_External_Contracts.md** — 对外契约
  - 用途：`airflow_config` 工厂签名、DAG 调度契约、Sensor 边、pydantic Schema
  - 适用场景：新增工厂 API、跨 DAG 等待边、元数据 DTO 变更

- **03_Downstream_Dependencies.md** — 下游依赖
  - 用途：BQ/Sensor/ES/飞书/Datastroc/PubSub/TT/Adjust/GenAI 拓扑与幽灵依赖
  - 适用场景：新增外部服务、超时审计、幽灵调用清理

- **04_Data_Model_and_Lifecycle.md** — 数据模型与生命周期
  - 用途：BQ FQN/dataset、分区 DELETE+INSERT / MERGE、ES index、标签元数据水位
  - 适用场景：改表/分区、贴源 MERGE、标签宽表、ES 字段映射

- **05_Business_Orchestration.md** — 业务编排
  - 用途：36+ DAG 入口、主链路、分层违规、设计模式；产出 `05_module_manifest.json`
  - 适用场景：改调度依赖、理解日/时批主链、模块分册入口

- **05_module_manifest.json** — Step08 模块清单
  - 用途：14 个深潜模块 id/name/complexity（airflow-config … test-dags）
  - 适用场景：核对 08x 覆盖是否齐全、复杂度排序

- **06_Async_Jobs_and_Compensation.md** — 异步与补偿
  - 用途：Sensor/SkipSensor/TimeDelta/PubSub/ES 幂等/Dataproc 删簇与风险矩阵
  - 适用场景：排障 Sensor、小时 Skip、日报 execution_delta、空转边

- **07_Config_and_Observability.md** — 配置与可观测
  - 用途：Variable/Connection、TT/ES/飞书配置、异常与日志、监控 paused 风险
  - 适用场景：告警接线、Unpause 检查、凭据治理、ES 超时可配化

### 业务维度（纵向切片）

| 文件 | 模块 id | 用途 | 适用场景 |
|---|---|---|---|
| **08a_Module_共享编排工厂与告警.md** | airflow-config | Sensor/BQ/TT/ES/飞书工厂决策与失败模式 | 改工厂默认、告警 callback、ES 写删 |
| **08b_Module_ODS日批贴源层.md** | ods-d | ODS 日批 MERGE/DELETE+INSERT、Adjust/飞书/Spark 等待 | 改贴源、订单 MERGE ON id |
| **08c_Module_ODS小时批贴源层.md** | ods-h | 小时 ODS 写 `*_h`、下游 Skip vs dwd_h 日工厂反例 | 改小时贴源、核对下游等待语义 |
| **08d_Module_DIM维度层日时批.md** | dim-d | 日维/时维、2999 镜像、dim→dwd 倒挂 | 改维表、结算维、Skip 模板 |
| **08e_Module_DWD明细日批.md** | dwd-d | 日明细枢纽、voucher 售后 RETURN、孤儿 Sensor | 改订单/券明细、日批依赖 |
| **08f_Module_DWD明细小时批.md** | dwd-h | **日工厂等小时反例**、小时 voucher 无售后改写 | 改小时明细；禁止复制日工厂等 `*_h` |
| **08g_Module_DWS汇总层日时批.md** | dws-d | device_active、完单口径、小时 Skip 正面样本 | 改设备活跃/汇总；评估 SLA 扇出 |
| **08h_Module_RPT报表日批.md** | rpt-d | 日批最大汇聚、ES 吞绿、device_active 扇出 | 改经营报表、日报上游、ES 旁路 |
| **08i_Module_RPT报表小时批.md** | rpt-h | 小时 RPT Skip 合规、写回 `qpon_rpt_d` | 改小时报表；勿当日批 voucher 口径 |
| **08j_Module_标签生产日批.md** | tag-d | 写 `qpon_services_prod` + `tag_qpon_metadata` | 改标签宽表/水位、device_active 依赖 |
| **08k_Module_分析服务风控日报出口.md** | analyst-serving | 日报 delta、data_server ES **raise 红**、alarm_h 反例 | 改出口/风控/日报/ES 红路径 |
| **08l_Module_元数据与GCP监控.md** | metadata | paused 三 DAG、Variable 集中、meta load 吞绿 | Unpause、`gcp_alter`、元数据同步 |
| **08m_Module_运维清理与Dataproc接入.md** | ops-staging | Spark ephemeral、Adjust、清理、kill、ops ES 吞绿 | Dataproc/kill/清理/运维 ES |
| **08n_Module_测试环境DAG包.md** | test-dags | 测包 Sensor/表后缀隔离、生产 dim 债 | 测试包隔离、禁止假绿放行 |

---

## 3. 场景路由表

| 场景 | 必读文件 | 可选文件 | 说明 |
|------|---------|---------|------|
| 快速上手 | 00, 01, 05 | 08a, manifest | 先总目录与骨架，再编排与工厂 |
| 改 DAG / 调度依赖 | 05, 02, 06 | 对应 08x, 01 | 先编排与契约，再 Sensor 语义；同步双写 |
| 排障：Sensor 久等 / Task 绿仍错 | 06, 07, 03 | 05, 对应 08x | 区分 Skip vs 日工厂；勿把吞绿/旁路成功当数据就绪 |
| 改标签（tag / metadata 水位） | 08j, 04, 05 | 08g, 07 | 幂等=`dayno`+`tag_name`；读 `tag_qpon_metadata.latest_dayno` |
| 改 ES 写删 / 出口 | 08k, 08a, 03 | 08h, 08m, 07 | **区分** data_server raise 红 vs rpt/meta/ops 吞绿；测包无 ES |
| 运维 Dataproc / kill / 清理 | 08m, 06, 03 | 08b, 07 | 删簇 `all_done`；kill 阈值以代码为准；清理勿当 ADS 日 |
| 测试包隔离 / 防污染生产 | 08n, 01, 04 | 05, 07 | Sensor 须 `*_test`；隔离=表后缀；禁扩生产 dim/事件混读 |
| 新增/改表或分区 SQL | 04, 05 | 对应 08x | DELETE+INSERT 分区重算 vs MERGE 贴源 |
| 告警 / TT / 监控静默 | 07, 08l, 08a | 06, 08n | Unpause+`gcp_alter`；先接线 `etl_alter` 再删硬编码 |
| 性能 / slot / Sensor 风暴 | 07, 06, 01 | 03, 08a | 禁止盲目提高 retries=1000；评估 Composer slot |
| 改小时批等待语义 | 06, 08f, 08c | 08d, 08i, 08k | 小时必须 Skip；反例：`dwd_h`、`alarm_h`、`test_d→dwd_h` |
| device_active / DAU SLA | 08g, 08j, 08h | 08k | SLA 评估集=**tag ∪ rpt-d ∪ analyst-serving**（不含 test-dags） |
| 查 APP/H5 等各环境活跃设备数 / DAU | 04, 08g | data-agent `catalog.py` | 权威表=`qpon_dws_d.dws_qpon_device_active_info_inc_d`（`host_environment`+`uni_device_id`）；派生 RPT 仅核对 |

---

## 4. 关键发现汇总

### 4.1 架构与依赖

- NON_JAVA：无 Maven/Dubbo；契约=工厂函数 + DAG 入口 + Sensor 边（441+）。
- 主链日批 `0 18 * * *`：ods→dim/dwd→dws→rpt；小时 `10 * * * *`：ods_h→dim_h/dwd_h→dws_h/rpt_h。
- 幽灵：`create_external_sensor_hour` 无活调用；`ElasticsearchWriteOperator` 活调用=0；`check_allowed_hours_is_run` 空转边；`etl_alter_webhook_url` 无消费者。
- 分层倒挂：dim→dwd、dwd→dws、rpt 自等；失败传播难排。

### 4.2 Red Flags（跨 Step 提炼）

- 凭据/TT token/飞书 Secret 硬编码；ES task log 可 print password。
- 日批 Sensor `retries=1000` / `timeout=64800` 无 pool。
- 测试 DAG 与生产同仓同 cron；隔离靠表后缀非独立 dataset。
- 依赖版本未入库（无 requirements/pyproject）。

### 4.3 开放债（Step08 RELAY → 收官必须保留，勿丢失）

| # | 开放债 | 权威来源 | 收官落点 |
|---|---|---|---|
| 1 | 生产须 **Unpause** `gcp_monitoring_alert` 且 **`gcp_alter_webhook_url` 非空**，否则 Pub/Sub→TT 静默 | 07 / 08l / 08n RELAY | 目录 §4.3 + 军规 G-OPS-01 |
| 2 | 告警治理：**先接线** `etl_alter_webhook_url` + `TeamtalkRobot`，**再删**硬编码 TT（含测包） | 07 G-07-08 / 08a / 08l–n | 军规 G-OPS-02 |
| 3 | 区分 **吞绿**（meta load、ops `task_write_es`、rpt ES except print）vs **ES raise 红**（生产 data_server）；禁止用测包 BQ 绿代替 | 08k / 08l / 08m / 08n | 军规 G-ES-01 |
| 4 | 对账 ADS/DAU **禁止**用旁路/TimeDelta/meta/`date.today`/alarm `now()`/GenAI fallback/`data_options.current_date` 当业务日 | 08k–n RELAY | 军规 G-DAY-01 |
| 5 | **device_active SLA** 评估集 = **tag ∪ rpt-d ∪ analyst-serving**（不含 test-dags） | 08g / 08j / 08h / 08k | 军规 G-SLA-01 |
| 6 | **hour-Skip 未闭环**：`alarm_h` 日工厂等小时；`qpon_test_d→dwd_h` Skip 反例仍在 | 08k / 08f / 08n | 军规 G-HR-01 |
| 7 | 测试包对生产 **dim Sensor 债** + **表后缀隔离红线**（禁无后缀写生产表） | 08n | 军规 G-TEST-01/02 |
| 8 | **`dwd_h` 日工厂等小时**反例；订单 **MERGE 仅 ON `id`**（跨分表非唯一） | 08b/c/e/f | 军规 G-HR-02 / G-SQL-01 |

### 4.4 设计模式（可复用）

- 工厂方法：`create_composer_bq_task` / `create_external_sensor` / SkipSensor。
- 策略：日批失败即失败 vs 小时 Skip 透传。
- 分区幂等：DELETE+INSERT（日事实）vs MERGE 贴源（ODS）vs TRUNCATE 维表。

---

> [!SUCCESS] 总目录组装闭环验证
> - 输入范围：Legacy + 01–07 + `05_module_manifest.json` + 08a–08n（14 模块）全部产出
> - 提取结果：23 个知识库导航条目（含 Legacy/manifest）、12 个场景路由、8 项开放债入库、关键发现 4 类
> - 产出文件：`00_Master_Catalog.md` + `.cursor/rules/qpon-bigdata.mdc` + `.gemini/rules/qpon-bigdata.md`
> - EOF 状态：已确认遍历至最后一行，无静默截断
