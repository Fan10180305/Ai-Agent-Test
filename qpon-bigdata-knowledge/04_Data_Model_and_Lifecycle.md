# 04_Data_Model_and_Lifecycle — qpon-bigdata

> 项目类型：NON_JAVA / Airflow DAG（Cloud Composer）  
> 扫描权威范围：`dags/`（含子目录）；禁止 `scripts/`  
> 语义映射：Java dao/entity/mapper → **BigQuery 表/视图实体 + SQL CREATE/INSERT/MERGE/DELETE 目标 + 分区生命周期 + ES index 文档模型**  
> BQ 锚点：`oppo-gcp-prod-digfood-129869` @ `asia-southeast2`  
> Legacy：NO_DOCS  
> 完成度策略：**全量计数 + 抽样证据**；禁止对未读 DDL 虚构列结构  
> 物理拦截：对 `dags/**/*.py`（1167）做 backtick 三元组 FQN 全量正则；`insert_dataset_id`/`insert_table_id` 变量展开；ES 写入口全量枚举；飞书仅活路径

---

### 1. 实体决策摘要

N/A：无 Java `@TableName` Entity / MyBatis Mapper。等价「实体」= **BQ 目标表（含注释 DDL）+ 标签宽表 + ES 文档模型 + 飞书落地表**。

**基类公共字段（仓内惯例，非 OOP 基类）**：多数日批/小时批事实表携带 `partition_date DATE`（分区键）；ETL 贴源表常见 `etl_time`；标签表公共键为 `(dayno, tag_name, {entity_id})`。后续实体不重复展开这组惯例，除非它是主键/状态机。

**扫描规模声明**：backtick FQN 命中 **5989**；唯一 `project.dataset.table` **1062**（其中 UDF 名如 `aes_decrypt`/`url_decode` 计入 FQN 但非表实体）；唯一 dataset **35**。下文仅展开**代表性实体**；其余表仅在 §2 以 dataset 聚合 + Top 读写明细给出，**不虚构列**。

#### 1.A 仓内分层代表实体

##### DwdProductOrderVoucherAll（`qpon_dwd_d.dwd_product_order_voucher_all` | 分区表 | 分区键：`partition_date`）

- 总字段数：**179** 个（源：`insert_table_fields`，`dags/qpon_dwd_d/tasks/dwd_product_order_voucher_all.py`）；主键：`id`（业务 INPUT，非 DB AUTO）
- 分区键：`partition_date`
- 状态机：`order_status` — 代码可见 `COMPLETED` / `RETURN`（另有 ODS DDL 注释全集，见 §8）；`order_pay_status`；`use_status`；`voucher_status`；`after_sale_status` / `t_life_after_sale_order_status`；`pay_status`；`product_status`；`is_formal`（0/1）；`is_deleted`；`is_pay`；`is_consume`；`is_refund`；`is_first_finish_order` / `is_first_place_order`（0/1 派生）
- 关键关联：`store_id` / `merchant_id` / `user_id` / `product_id` / `sku_id` / `stock_id` / `order_item_id` / `voucher_id` / `pay_id` / `pay_order_id` / `consume_store_id` / `place_store_id` / `provider_id` → 维表/ODS 业务键（BQ 无跨分片 JOIN 风险；⚠️大表无分区过滤扫全历史）
- 特殊注解：N/A（无 MyBatis TypeHandler）；逻辑删除：`is_deleted`；乐观锁：无
- 时间范围控制：`effective_begin_time` / `effective_end_time` / `sold_start_time` / `sold_end_time` / `product_sold_start_time` / `product_sold_end_time` / `voucher_start_time` / `voucher_end_time` / `exchange_end_time`
- 已显式列出字段数 K=**39**；其他字段：R=**140** 个（`business_type` / `merchant_name` / `user_ip` / `user_device_id` / `country_code` / `phone_no` / `order_type` / `order_pay_id` / `order_pay_channel` / `order_pay_time` / `order_source` / `create_time` / `update_time` / `logo_url` / `order_product_type` / `rule_description_id` / `rule_description_en` / `rule_description_cn` / `redeem_description_id` / `redeem_description_en` / `redeem_description_cn` / `code_source_type` / `redeem_type` / `redeem_time_type` / `redeem_times` / `category_type` / `effective_time_type` / `effective_days` / `business_cp_type` / `pay_cp_type` / `pay_service_provider` / `pay_channel_id` / `currency` / `pay_time` / `pay_create_time` / `pay_update_time` / `purchase_count` / `sale_amount` / `original_amount` / `reality_amount` / `taxation_amount` / `coupon_amount` / `discount_amount` / `subsidy_amount` / `pay_amount` / `red_amount` / `red_count` / `voucher_sale_amount` / `voucher_original_amount` / `voucher_reality_amount` / `voucher_taxation_amount` / `voucher_coupon_amount` / `voucher_discount_amount` / `voucher_subsidy_amount` / `voucher_pay_amount` / `voucher_red_amount` / `voucher_red_count` / `is_voucher_id` / `voucher_type` / `code` / `code_source` / `voucher_code` / `consume_store_name` / `bank_name` / `bank_user_name` / `bank_no` / `consume_order_id` / `consume_time` / `consume_ip` / `operator_id` / `operator_name` / `consume_source` / `consume_scene` / `product_name` / `product_name_cn` / `product_name_id` / `product_name_en` / `product_type` / `total_stock` / `daily_stock` / `settlement_type` / `subsidy_percent` / `platform_brokerage_amount` / `platform_brokerage_amount_tax` / `platform_allowance_amount` / `platform_incentive_amount` / `platform_procurement_price` / `profit_amount` / `profit_amount_tax` / `source_tag` / `host_environment` / `provider_name` / `merchant_level` / `voucher_create_time` / `split_reality_amount` / `is_formal_consume_store` / `consume_category_name_cn` / `procurement_price` / `place_store_country` / `place_province_google_name` / `place_city_google_name` / `place_area_google_name` / `place_province_region_name` / `place_city_region_name` / `place_area_region_name` / `sale_price` / `provider_type` / `place_store_name` / `place_category_name_cn` / `place_category_name_cn_level_1` / `place_category_name_cn_level_2` / `order_activity_id` / `order_activity_name` / `order_activity_type` / `module_enter` / `module_enter_id` / `promotion_activity_discount_amount` / `merchant_subsidy_amount` / `voucher_pay_fee_amount` / `pay_fee_amount` / `refund_policy` / `platform_brokerage_ratio` / `platform_incentive_ratio` / `product_lvl1_cate_id` / `product_lvl2_cate_id` / `product_lvl1_cate_name_cn` / `product_lvl1_cate_name_en` / `product_lvl1_cate_name_idn` / `product_lvl2_cate_name_cn` / `product_lvl2_cate_name_en` / `product_lvl2_cate_name_idn` / `coins_deduct_amount` / `voucher_coins_deduct_amount` / `use_coins` / `voucher_use_coins` / `t_life_after_sale_order_complete_time` / `activity_channel_sale_price` / `ad_trace` / `business` / `third_party_subsidy_amount`）
- 生命周期：`DELETE … WHERE partition_date = DATE(?)` + `INSERT INTO`（日增量覆盖分区）

##### OdsTLifeOrderAllD（`qpon_ods_d.ods_t_life_order_all_d` | 分区表 | 分区键：`date(create_time)`；cluster：`db_name`）

- 总字段数：注释 DDL 列出 **约 50+** 列（见文件尾 CREATE 注释；**未在运行时再声明 insert_table_fields**）；主键：`id`（INPUT）
- 状态机（DDL 注释摘录，非 Enum 类）：`order_status` — `SUBMIT` / `COMPLETED` / `CANCEL` / `RETURN`；`pay_status` — `WAIT_PAY` / `PAY_SUCCESS` / `CLOSE`；`use_status` — `VALID` / `USED` / `REFUND` / `EXPIRED`；`after_sale_status`；`is_flash_sale`（1/0）
- 关键关联：`store_id` / `merchant_id` / `user_id` / `pay_id` / `exchange_store_id`
- 逻辑删除：无显式 `@TableLogic`；乐观锁：`version`（DDL 注释）
- 时间范围：`exchange_start_time` / `exchange_end_time` / `pay_time` / `create_time` / `cancel_time` / `update_time`
- 其他字段：以 DDL 注释为准（`db_name` / `table_name` / `etl_time` / 金额族 / `flash_sale_info` / `feature` / `extend_info` 等）——**禁止在未逐列核对时改写为「精确 N」以外的臆造总数**；本实体以注释 DDL 为权威字段清单
- 生命周期：源库分表 `digital_food_market` 经 Datastream 落地后 **MERGE INTO** 目标（`digital_food_market_0_3` 任务族）；分区 `PARTITION BY date(create_time)`

##### DimStoreInfo（`qpon_dim_d.dim_store_info` | 全量覆盖表 | 无日分区删除键）

- 总字段数：未集中声明 `insert_table_fields`；以 `INSERT … SELECT` 投影为准（文件长 SQL）
- 主键/业务键：`store_id`（INPUT）
- 状态机：`is_formal`（0/1，测试/黑名单门店过滤）
- 关键关联：`merchant_id` → `dim_merchant_basic_info` / ODS 商家
- 生命周期：`TRUNCATE TABLE` + `INSERT INTO`（全量刷新）

##### DwsQponDeviceActiveInfoIncD（`qpon_dws_d.dws_qpon_device_active_info_inc_d` | 分区表 | 分区键：`partition_date`）

- 主键语义：`(partition_date, host_environment, uni_device_id)`（窗口去重）
- 关键关联：`user_id` / `qpon_device_id` / `device_id` / `adid`
- 生命周期：`DELETE WHERE partition_date = DATE(?)` + `INSERT`；被标签层高读（如 `tag` ← `dws_qpon_device_active_info_all_d`）
- **查数口径（权威）**：APP / H5 等各环境「活跃设备数 / DAU」统一读本表；环境维=`host_environment`，去重=`COUNT(DISTINCT uni_device_id)`，业务日=`partition_date`。禁止把 `rpt_dau_report_inc_d` / `rpt_app_user_statistic_v3` 等派生报表当首选源（仅可交叉核对）。位图/留存窗用 `*_all_d`，勿与日活设备数混口径。

##### RptBusinessIndicatorDetailD（`qpon_rpt_d.rpt_business_indicator_detail_d` | 分区表 | 分区键：`partition_date`）

- 总字段数：`insert_table_fields` 声明 **94** 个（含注释行内字段名）
- 主键语义：业务明细组合键（`partition_date` + `merchant_id`/`store_id`/`product_id`/`order_id` 等，见 SELECT qualify）
- 状态机：大量 `is_*` / `if_first_*` 标志位（0/1）
- 生命周期：`DELETE FROM … WHERE partition_date=…` + `INSERT INTO`

##### AdsCheckinIncD（`qpon_analyst_d.ads_checkin_inc_d` | 分区表）

- 注释 CREATE 列抽样可见：`user_id` / `partition_date` / `partition_month` / `local_event_time` / `checkin_entry_name` / `eventgroup` 等（注释 DDL 约 66 处类型标注命中，含重复块）
- 生命周期：日批 DELETE+INSERT（与层内同类 ADS 一致）

##### TagQponAllD（`qpon_services_prod.tag_qpon_all_d` | 标签宽表 | 逻辑分区键：`dayno`）

- 总字段数：**4** 个；主键：复合 `(dayno, tag_name, device_id)`（INPUT）
- 状态机：无；标签值在 `tag_value`
- 关键关联：`device_id` → 设备维；`tag_name` → 元数据 `tag_qpon_metadata.data_id`
- 逻辑删除：无；乐观锁：无
- 其他字段：R=**0**（4 字段均已显式：`device_id` / `tag_value` / `dayno` / `tag_name`）
- 生命周期：`DELETE WHERE dayno=? AND tag_name=?` + `INSERT`；随后 `MERGE` 元数据表 `tag_qpon_metadata`（`data_type='TAG'`, `latest_dayno`）
- 同族表：`tag_qpon_userid_all_d` / `tag_qpon_merchant_all_d` / `tag_qpon_store_all_d`（dataset=`qpon_services_prod`；test=`qpon_services_test`）

##### 小时批落点（代表）

小时 DAG 写入口常落在**日批同名 dataset**（非独立 `qpon_*_h` dataset）：

| 写包 | 目标 dataset.table（变量展开抽样） |
|---|---|
| `qpon_ods_h` | `qpon_ods_d.ods_qpon_event_message` |
| `qpon_dim_h` | `qpon_dim_d.dim_merchant_basic_info_h` / `dim_store_info_h` |
| `qpon_dwd_h` | `qpon_dwd_d.dwd_product_order_voucher_all_h` 等 18 个写目标 |
| `qpon_dws_h` | `qpon_dws_d.dws_feature_*_h`（3） |
| `qpon_rpt_h` | `qpon_rpt_d.rpt_*_h` / 部分无 `_h` 后缀表（13） |
| `qpon_analyst_h` | `qpon_analyst_h.ads_*`（字面 FQN 存在） |

#### 1.B 飞书活路径实体（仅此）

##### OdsNewStoreFromMktForUsing（`qpon_sync_from_feishu.ods_new_store_from_mkt_for_using` | 普通表）

- 总字段数：**8** 个；主键：`id`（INPUT）
- 状态机：无
- 关键关联：`store_id` / `merchant_id`
- 时间控制：`adjustment_date` / `offline_date`（TIMESTAMP）
- 逻辑删除：无；乐观锁：无
- 其他字段：R=**3** 个（`store_name` / `merchant_name` / `etl_time`）— 已显式主键+关联+时间=5，8-5=3
- 写入：`ReadFeiShuToBigQuery.write_to_bigquery`（活注册：`ods_new_store_from_mkt_for_using`）
- **失活对照**：同 dataset 另有 `ods_expense_*` / `ods_channel_info` 等 14 表被 FQN 引用或模块存在，但 DAG 入口多为注释失活（Step03）；本步不把失活模块当活写模型

#### 1.C ES 文档模型（写入口全量枚举 + 字段映射样例）

写通道：`access_cloud_run_write_aliyun_es(select_sql, id_field, index_name)`；删：`delete_by_field_condition`。  
活写调用点 **22** + 删 **1**；唯一 index **18**（含 test）。

| 调用方模块 | index_name | id_field | 字段映射样例（BQ AS ES） |
|---|---|---|---|
| `rpt_channe_store_sales_overview_statistics_es` | `store_sale_statis_dashboard` | `id` | `partition_date→dataVestingDate`, `bd_id→userId`, `settled_store_num→settledStoreNum`, …, `coverage_rate→coverageRate` |
| `rpt_channe_store_ranking_list_es` | `store_ranking_statis` | `id` | `grid_merchant_id→gridMerchantId`, `store_id→storeId`, `redem_gtv_num→redemGtvNum` |
| `rpt_channe_sales_ranking_list_es` | `sales_ranking_statis` | `id` | `bdm_id→superviorUserId`, `bd_id→userId`, … |
| `rpt_channe_merchant_ranking_list_es` | `merchant_ranking_statis` | `id` | `merchant_id→merchantId`, … |
| `rpt_channe_grid_ranking_list_es` | `grid_ranking_statis` | `id` | `grid_area_id→gridId`, … |
| `rpt_department_sale_statis_dashboard_es` | `department_sale_statis_dashboard` | `id` | `department_id→departmentId`, … |
| `rpt_department_sales_ranking_statis_es` | `department_sales_ranking_statis` | `id` | 同上族 |
| `rpt_department_merchant_ranking_statis_es` | `department_merchant_ranking_statis` | `id` | 同上族 |
| `rpt_department_grid_ranking_statis_es` | `department_grid_ranking_statis` | `id` | 同上族 |
| `rpt_trade_store_statis_dashboard_d_es` | `trade_store_statis_dashboard` | `id` | `data_vesting_date→dataVestingDate`, `bd_id→bdId`, … |
| `rpt_trade_merchant_statis_dashboard_d_es` | `trade_merchant_statis_dashboard` | `id` | `settled_merchant_num→settledMerchantNum`, … |
| `dwd_*` / `data_server_*` `market_activity…_to_es` | `market_activity_dashboard_data` | `Id` | `concat(date,page,product)→Id`, `partition_date→dataDate`, `page_title_cn→pageTitleCN`, … |
| `dwd_*` / `data_server_*` `merchant_daily_performance_to_es` | `sync_merchant_customer_data_v2` | `id` | `concat(dataDate,merchantId,type,store)→id`, `pvSt…` |
| `dwd_*` / `data_server_*` `merchant_daily_coupon…_to_es` | `sync_merchant_product_coupon_card_data_20260410` | `id` | `concat(date,merchant,product)→id`, `coupon_card_uv` |
| `dwd_*` / `data_server_*` `recruit_activity…_to_es` | `recruit_activity_product_data` | `Id` | `es_id→Id`, `product_name_cn→productNameCN`, … |
| `data_server_store_sell_well_rank_20260521_to_es` | `store_sell_well_rank_20260521` | `id` | `store_id`, `city_id`, `rank_sort`, … |
| `data_server_merchant_refund_statistics_to_es` | `merchant_refund_statistics_2026061501` | `id` | `merchantId`, `productId`, `refundCount`, `transactionAmount`, … |
| `data_options/task_write_es` | `test_store_sale_statis_dashboard` | `id` | 与渠道看板同构 camelCase |
| `data_server_store_sell_well_rank_20260521_delete_es` | `store_sell_well_rank_20260521`（DELETE） | 条件字段 `partition_date` | term 删除当日分区文档 |

查询结果 DO（非持久表）：ES SELECT 投影、飞书 DataFrame 中间列——用途见上表，不展开为仓表实体。

---

### 2. 表与实体映射总表

#### 2.1 全量计数（权威）

| 指标 | 数值 | 说明 |
|---|---:|---|
| backtick FQN 命中 | 5989 | `dags/**/*.py` 全量 |
| 唯一 FQN | 1062 | 含 UDF 名 |
| 唯一 dataset | 35 | 见下表 |
| 唯一 `dataset.table`（粗去 UDF） | ≈1058 | `aes_decrypt`/`url_decode` 等从「表实体」视角剔除后仍 >1000 |
| SQL 写操作字面 | INSERT 961 / DELETE 919 / MERGE 208 / CREATE_TABLE 471 / CREATE_EXTERNAL_TABLE 3 | 含注释块内 DDL |
| task 内 DELETE+INSERT 模式文件 | 837 | 主生命周期 |
| `PARTITION BY partition_date` 字面 | 726 | 含窗口函数噪声；CREATE 侧为主证据见 §4/§7 |

> **显式标注**：对 1000+ FQN **无法在本步穷尽列结构**。下列为 dataset 聚合统计 + Top 读写表明细（抽样证据）。需要某表全列时，以对应 `tasks/**.py` 尾部 `# CREATE TABLE` 注释或 `insert_table_fields` 为准二次展开。

#### 2.2 Dataset 聚合（引用频次 / 唯一表名数）

| 类别 | dataset | FQN 命中 | 唯一 table 名 | 角色 |
|---|---|---:|---:|---|
| 仓内-DWD | `qpon_dwd_d` | 1741 | 184 | 明细事实 |
| 仓内-ODS | `qpon_ods_d` | 1239 | 225 | 贴源 |
| 仓内-RPT | `qpon_rpt_d` | 1198 | 293 | 报表/ADS |
| 仓内-DIM | `qpon_dim_d` | 682 | 43 | 维度 |
| 仓内-DWS | `qpon_dws_d` | 263 | 29 | 汇总 |
| 仓内-ANALYST | `qpon_analyst_d` | 101 | 34 | 分析师 |
| 仓内-ANALYST_H | `qpon_analyst_h` | 7 | 3 | 小时分析 |
| 仓内-TMP | `qpon_tmp` | 114 | 16 | 临时 |
| 仓内-EMAIL | `qpon_email_date_d` / `_test` | 47 / 49 | 11 / 11 | 邮件市集 |
| 仓内-DATA_SERVER | `qpon_data_server` | 26 | 6 | 服务投递中间表 |
| 标签落点 | `qpon_services_prod` / `_test` | （变量写为主，字面 FQN 少） | 9 / 4 写目标 | 标签宽表 |
| 飞书 | `qpon_sync_from_feishu` | 32 | 15 | 飞书同步（活 1） |
| **源库** | `digital_food_order` | 170 | 66 | Datastream/直读源 |
| **源库** | `digital_food_market` | 88 | 57 | 源 |
| **源库** | `digital_food_settle` | 20 | 6 | 源 |
| **源库** | `digital_food_admin` | 1 | 1 | 源 |
| **源库** | `order_center_hzero_platform` | 40 | 6 | HZERO |
| **源库** | `order_center_qpon_bd` | 5 | 3 | BD |
| **源库** | `market_db_user_growing` | 3 | 2 | UG |
| **源库** | `qpon_crm` / `qpon_operation` / `qpon_review` 等 | ≤12 | ≤5 | 业务库镜像 |
| 事件 | `pubsub_to_bq_qpon_events_collection` | 33 | 4 | 含 UDF `url_decode` |
| Adjust | `Qpon_Adjust_Raw_Data` | 3 | 2 | 外部表 |
| 测试源 | `test_env_digital_food_*` 等 | 若干 | — | 测试镜像 |

**区分原则**：`digital_food_*` / `order_center_*` / `market_db_*` / `qpon_crm|operation|review|…` = **源库 dataset**（Datastream 或直读）；`qpon_ods|dim|dwd|dws|rpt|tag|analyst|…` = **仓内分层**（ODS 及之后由本仓 SQL 生产）。标签物理 dataset 名为 `qpon_services_prod`，由包 `qpon_tag_d` 生产。

#### 2.3 Top 读写表（字面 FQN）

| 命中 | FQN | 典型角色 |
|---:|---|---|
| 385 | `…qpon_dwd_d.dwd_qpon_event_traffic_inc_d` | 事件明细（高读） |
| 370 | `…qpon_dwd_d.dwd_product_order_voucher_all` | 订单券事实（高读/高写） |
| 151 | `…qpon_dim_d.dim_daytime_info` | 日期维 |
| 115 | `…qpon_dws_d.dws_qpon_device_active_info_inc_d` | 设备活跃 |
| 99 | `…qpon_dwd_d.dwd_product_store_detail_d` | 门店商品 |
| 89/87/85 | `dim_product_basic_info` / `dim_store_info` / `dim_merchant_basic_info` | 核心维 |
| 86 | `…qpon_rpt_d.rpt_store_merchant_detail_dashboard_inc_d` | 报表 |
| 59 | `…digital_food_order.aes_decrypt` | **UDF**（非表） |
| 53 | `…qpon_ods_d.ods_qpon_event_message` | ODS 事件 |

#### 2.4 变量展开写目标（`insert_dataset_id` + `insert_table_id`）

| 目标 dataset | 展开写次数 | 唯一表 |
|---|---:|---:|
| `qpon_rpt_d` | 235 | 234 |
| `qpon_dwd_d` | 169 | 125 |
| `qpon_services_prod` | 142 | 9 |
| `qpon_services_test` | 40 | 4 |
| `qpon_analyst_d` | 28 | 28 |
| `qpon_dim_d` | 22 | 22 |
| `qpon_dws_d` | 21 | 21 |
| `qpon_email_date_d`(+test) | 20+20 | 10+10 |
| `qpon_ods_d` | 4* | 4 |

\*多数 ODS 使用字面 FQN 或 MERGE，不完全依赖 `insert_dataset_id` 变量（ODS task 文件 167：`delete_insert` 121 / `from_digital` 118 / `create` 注释 163）。

#### 2.5 映射总表（代表行；非全量 1062）

| 逻辑实体 | 表名（dataset.table） | 字段数 | 主键策略 | 逻辑删除 | 乐观锁 | 分区/分片 | 备注 |
|---|---|---:|---|---|---|---|---|
| DwdProductOrderVoucherAll | `qpon_dwd_d.dwd_product_order_voucher_all` | 179 | INPUT `id` | `is_deleted` | 无 | `partition_date` | 核心事实 |
| OdsTLifeOrderAllD | `qpon_ods_d.ods_t_life_order_all_d` | DDL≈50+ | INPUT `id` | 无 | `version` | `date(create_time)` | MERGE 贴源 |
| DimStoreInfo | `qpon_dim_d.dim_store_info` | 未集中声明 | INPUT `store_id` | 无 | 无 | TRUNCATE 全量 | 维表 |
| DwsDeviceActiveInc | `qpon_dws_d.dws_qpon_device_active_info_inc_d` | 未集中声明 | 复合 | 无 | 无 | `partition_date` | 高读 |
| RptBizIndicator | `qpon_rpt_d.rpt_business_indicator_detail_d` | 94 | 复合 | 无 | 无 | `partition_date` | 报表 |
| TagQponAllD | `qpon_services_prod.tag_qpon_all_d` | 4 | 复合 | 无 | 无 | `dayno`+tag | 多任务写同一表 |
| TagMetadata | `qpon_services_prod.tag_qpon_metadata` | 3 | (`data_type`,`data_id`) | 无 | 无 | MERGE | 182 处元数据 MERGE |
| FeishuNewStore | `qpon_sync_from_feishu.ods_new_store_from_mkt_for_using` | 8 | INPUT `id` | 无 | 无 | 无 | 唯一活飞书 |
| ES:* | 18 indexes | 见 §1.C | `id`/`Id` | 按日删 1 | 无 | N/A | Cloud Run 写 |

旧文档差异：NO_DOCS → N/A。

---

### 3. 查询模式矩阵

#### 3.0 BaseMapper 统一说明

N/A：无 MyBatis `BaseMapper`。等价统一写模板：

- **分区覆盖**：`DELETE FROM tgt WHERE partition_date = DATE({{ds+1}})` + `INSERT INTO tgt (…) SELECT …`
- **全量维**：`TRUNCATE` + `INSERT`
- **贴源合并**：`MERGE INTO tgt USING (… ROW_NUMBER 去重) ON id …`
- **标签**：按 `tag_name`+`dayno` 删除插入 + `MERGE` metadata
- **ES**：`SELECT … AS camelCase FROM bq_table WHERE 近窗` → Cloud Run bulk index

#### 3.1 写操作清单（聚合）

| 操作类型 | 涉及表（范围） | 触发场景 | 批量/单条 | 风险标注 |
|---|---|---|---|---|
| DELETE+INSERT | 绝大多数 `qpon_{dwd,dws,rpt,ods,analyst}_*` 分区表 | 日/小时任务函数返回多语句 SQL | 批量（整分区） | 🔴无 `partition_date` 谓词则整表删除；代码主流带谓词 |
| TRUNCATE+INSERT | `dim_store_info` 等维表 | dim 日批 | 批量全表 | ⚠️并发读窗口空表风险 |
| MERGE | ODS `ods_t_life_order*_all_d` 等；标签 metadata | Datastream 增量合并 / 标签水位 | 批量 | ⚠️ON 键必须唯一；分表 `_TABLE_SUFFIX` |
| CREATE TABLE | 注释 DDL 为主；少量运行时 CREATE | 建表文档/一次性 | — | 注释 ≠ 运行时执行 |
| CREATE EXTERNAL TABLE | Adjust 原始 | `Qpon_Adjust_Raw_Data` | — | GCS 依赖 |
| ES index | 18 indexes | `*_es` / `*_to_es` Python 任务 | bulk | ⚠️与 BQ 近窗过滤不一致会导致 ES 陈旧 |
| ES delete | `store_sell_well_rank_20260521` | delete 任务 | 按 `partition_date` | — |
| 飞书 write_to_bigquery | `ods_new_store_from_mkt_for_using` | 活 Python 任务 | DataFrame 载入 | 凭证硬编码（Step01） |

#### 3.2 查询模式矩阵（SELECT 聚合）

| 查询场景 | 分区键是否在 WHERE | JOIN 表数 | 其他条件字段 | 分页 | 风险标注 |
|---|---|---|---|---|---|
| 下游读 `dwd_product_order_voucher_all` | 多数是 | 常 2–6 | `is_formal=1`, `order_status in (…)` | 无 | 🔴无分区过滤则扫全历史 |
| 下游读 `dwd_qpon_event_traffic_inc_d` | 多数是 | 1–3 | `host_environment`, `eventId` | 无 | 同上 |
| 维表关联 `dim_*` | 维表常全量 | 1 | `is_formal` | 无 | — |
| ES 导出 SELECT | 近窗（DAY-1/WEEK-7/MONTH） | 0–1 | `date_dimension_type` | 无 | ⚠️近窗外数据不刷新到 ES |
| 标签生产读 DWS | 是 | 1 | `host_environment`, 活跃天数 | 无 | — |
| ODS MERGE 源读 `digital_food_market.*` | 源表时间戳/后缀 | 1 | `datastream_metadata` | 无 | 源库分表后缀 |

---

### 4. 分库分表配置解析

N/A：无 ShardingSphere / sharding-jdbc。

**等价分片事实**：

| 项 | 代码事实 |
|---|---|
| a) 数据源 | 单一 BQ project `oppo-gcp-prod-digfood-129869`；源侧多 MySQL 经 Datastream Connection 前缀 `datastream-*` |
| b) 「分片表」清单 | 业务源表在 ODS 任务路径 `digital_food_*_0_3` 体现分库合并；SQL 使用 `_TABLE_SUFFIX` / `CONCAT(tb_name,_TABLE_SUFFIX)` |
| c) 分片算法 | **非哈希分片配置**；为 Datastream 多表后缀合并 + BQ `PARTITION BY`（`partition_date` 或 `date(create_time)`）+ 可选 `CLUSTER BY`（如 `db_name`） |
| d) 广播/默认 | 维表全量 TRUNCATE 可视为「广播维」；默认写 dataset 由各 task `insert_dataset_id` 钉死 |

小时层：**调度包** `*_h` 与 **物理 dataset** 常不一致（写入 `qpon_dwd_d` 等日批 dataset 的 `_h` 表）。

---

### 5. 数据源与连接配置

| 项 | 值（脱敏） |
|---|---|
| 主引擎 | BigQuery；location=`asia-southeast2`；conn=`google_cloud_default` |
| 连接池 | N/A（无 HikariCP）；Composer worker + BQ Job API |
| 多数据源 | 逻辑多 dataset；物理一 project |
| 源 MySQL | Datastream / Spark JDBC；密码 Secret Manager / Connection（`[REDACTED]`） |
| ES | Variable `es_hosts` / `es_user_name` / `es_password` / `es_api_key`=`[REDACTED]`；Cloud Run `write_es_service_url` |
| 飞书 | `FEISHU_APP_ID` / `SECRET`（硬编码 + Variable，Secret=`[REDACTED]`） |

---

### 6. TypeHandler 与类型映射

N/A：无 MyBatis TypeHandler。

等价类型映射：

| 机制 | Java/Python 侧 | BQ/ES 侧 | 使用处 |
|---|---|---|---|
| BQ 标准类型 | SQL DDL 注释 | `STRING`/`INT64`/`DATE`/`DATETIME`/`TIMESTAMP`/`NUMERIC(20,2|4)` | CREATE 注释 |
| UDF | SQL 调用 | `digital_food_order.aes_decrypt`；`pubsub_…url_decode` | 解密/URL |
| 飞书时间 | pandas `to_datetime(…, unit='ms')+8h` → UTC | `TIMESTAMP` | `ods_new_store_from_mkt_for_using` |
| ES 字段名 | SQL `AS camelCase` | ES document 字段 | 全部 `*_es` |
| ES id 合成 | `concat(...)` / `es_id` | `_id` via `id_field` | activity/merchant 类 |

---

### 7. 索引与查询模式分析

| 分析项 | 结论 |
|---|---|
| 「索引」等价物 | BQ **分区键** `partition_date`（726+ 字面）/ `date(create_time)`；**聚簇** `CLUSTER BY db_name`（订单 ODS DDL）；标签过滤键 `(dayno, tag_name)` |
| 高频过滤字段 | `partition_date`、`is_formal`、`host_environment`、`order_status`、`merchant_id`/`store_id`/`user_id`/`product_id`、`tag_name` |
| 无分区键查询风险 | 🔴报表/标签若漏 `partition_date`/`dayno` → 全表扫描（代码主流有键；复制任务时需门禁） |
| 复合索引推断（代码期望） | `(partition_date, merchant_id)`；`(partition_date, store_id)`；`(partition_date, uni_device_id, host_environment)`；`(dayno, tag_name)`；ODS `(db_name, id)` |
| 实际 DB 索引 | **无法从代码确认** BQ 是否已建 clustering/search index |
| 过期策略 | `partition_expiration` / `require_partition_filter` 字面命中极少（≤4）；**不能声称**全仓统一 TTL |

---

### 8. 实体状态机还原

N/A：无 Java Enum；状态值来自 **DDL 注释 + SQL 字面比较**。

#### 8.1 订单主状态（ODS DDL 注释权威）

| 字段 | 取值 | 含义（注释原文提炼） |
|---|---|---|
| `order_status` | `SUBMIT` / `COMPLETED` / `CANCEL` / `RETURN` | 提交/完成/取消/退单 |
| `pay_status` | `WAIT_PAY` / `PAY_SUCCESS` / `CLOSE` | 待支付/已支付/关闭 |
| `use_status` | `VALID` / `USED` / `REFUND` / `EXPIRED` | 待使用/已使用/已退券/已过期 |

#### 8.2 DWD 派生/使用

| 模式 | 证据 |
|---|---|
| `order_status in ('COMPLETED','RETURN')` + `is_formal=1` | `dwd_product_order_voucher_all` 首次完单判定 |
| `is_formal` 0/1 | 维表/事实过滤测试数据 |
| 标签无状态流转 | 每日按 `tag_name` 覆盖写；metadata `latest_dayno` MERGE 更新水位 |

流转方向：源库状态 → ODS MERGE 覆盖 → DWD DELETE+INSERT 日快照（非行级状态机 UPDATE）。**未发现** `UPDATE SET status=? WHERE status=?` 的行级状态推进模式（仓内以分区重算为主）。

---

### 9. 旧文档交叉验证摘要

NO_DOCS：跳过声称级 ❌/🆕/✅ 分条。

🆕相对空旧文档：数据模型主体是 BQ 分层表 + `qpon_services_*` 标签宽表 + 18 个 ES index + 飞书 `qpon_sync_from_feishu` 活表，而非 Java Entity/Mapper。

---

> [!SUCCESS] 数据模型测绘闭环验证
> - 扫描范围：N/A dao entity/mapper；等价 = `dags/` 1167 `.py` backtick FQN 全量 + `insert_*` 变量展开 + ODS/分层代表 task EOF DDL + ES 写/删入口 23 文件 + 飞书活路径 1（禁止 scripts/）
> - 提取结果：唯一 FQN 1062 / dataset 35；代表实体展开 ≥8（DWD/ODS/DIM/DWS/RPT/TAG/飞书/ES）；写操作 INSERT961/DELETE919/MERGE208/CREATE471；ES index 18（写22+删1）；TypeHandler=0（UDF/类型映射替代）
> - 分库分表：无 ShardingSphere；等价 = BQ dataset 分层 + Datastream 源表后缀合并 + PARTITION/CLUSTER
> - 表清单统计：字面唯一 FQN 1062（表实体≈1058，剔除 UDF）；分区表为主，维表 TRUNCATE 全量；标签集中 9 张宽表多任务写入
> - 旧文档差异：❌幽灵表 N/A / 🆕新发现 N/A / ✅其余 N/A（NO_DOCS）
> - EOF 状态：已确认 FQN 全仓计数、各层代表 task/ES/飞书文件读至产出所需行，并显式标注 1000+ FQN 列结构未穷尽；无静默伪造列

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: 核心事实表 `qpon_dwd_d.dwd_product_order_voucher_all`（179 字段，`partition_date` 日覆盖）；订单状态机字段在 ODS `ods_t_life_order_all_d` DDL 注释；标签落在 `qpon_services_prod.tag_qpon_*` + `tag_qpon_metadata`；ES 18 index 经 Cloud Run；飞书仅 `qpon_sync_from_feishu.ods_new_store_from_mkt_for_using`；源库 dataset 与仓内分层必须区分；小时批常写入日批 dataset 的 `_h` 表
> - **推演约束 (Constraint)**: Step 05 业务编排必须沿 `DELETE+INSERT` 分区重算与 `MERGE` 贴源两条生命周期追踪任务 DAG 依赖；订单/券状态以 ODS 注释枚举为权威；分析标签水位读 `tag_qpon_metadata.latest_dayno`；禁止把 `digital_food_*` 当仓内可写层；禁止 scripts/
> - **物理锚点 (Anchors)**: `dags/qpon_dwd_d/tasks/dwd_product_order_voucher_all.py:17-218`；`dags/qpon_ods_d/tasks/digital_food_market_0_3/ods_t_life_order_all_d.py:336-394`；`dags/qpon_dim_d/tasks/dim_store_info.py:14-24`；`dags/qpon_dws_d/tasks/dws_qpon_device_active_info_inc_d.py:15-31`；`dags/qpon_tag_d/tasks/app_active/device_app_last_version_code.py:8-76`；`dags/qpon_ods_d/tasks/qpon_feishu/ods_new_store_from_mkt_for_using.py:33-86`；`dags/qpon_rpt_d/tasks/rpt_channe_store_sales_overview_statistics_es.py:10-37`；`dags/airflow_config/cloud_run_write_aliyun_es.py:5`
