"""Domain catalog hints injected into the agent system prompt."""

DOMAIN_CATALOG = """
## Qpon 数仓只读范围
- GCP 项目: oppo-gcp-prod-digfood-129869
- 区域: asia-southeast2
- 允许 dataset（仅这些）:
  - qpon_rpt_d  — 报表/ADS
  - qpon_dws_d  — 汇总
  - qpon_dwd_d  — 明细事实
- 禁止访问: ODS/DIM/源库/标签/临时表/analyst 等其它 dataset

## 常用表（优先考虑）
| FQN | 用途 | 分区键 |
|---|---|---|
| qpon_rpt_d.rpt_business_indicator_detail_d | 业务指标明细（日报同源） | partition_date |
| qpon_dws_d.dws_qpon_device_active_info_inc_d | 各环境设备活跃/DAU（权威源） | partition_date |
| qpon_dwd_d.dwd_product_order_voucher_all | 订单券事实明细 | partition_date |
| qpon_dwd_d.dwd_qpon_event_traffic_inc_d | 流量事件明细 | partition_date |

## 指标口径（强制）
- APP / H5 等各环境「活跃设备数 / DAU」：**唯一权威表** = `qpon_dws_d.dws_qpon_device_active_info_inc_d`
  - 环境维度：`host_environment`（如 `app` / `h5`，大小写以表内实际值为准）
  - 去重键：`COUNT(DISTINCT uni_device_id)`
  - 业务日：`partition_date`（必须带分区过滤）
  - 禁止优先用 `rpt_dau_report_inc_d` / `rpt_app_user_statistic_v3` 等派生报表代替；后者仅可交叉核对，不作首选源
  - 位图/留存窗看 `dws_qpon_device_active_info_all_d`，不要与日活跃设备数口径混用

## SQL 规范
1. 只写 SELECT / WITH，禁止 DML/DDL
2. 分区表必须带 partition_date 过滤，避免全表扫描
3. 先 describe_table 再查；不确定表名先 list_tables
4. 聚合优先；结果行数有上限，大结果要摘要
5. 金额/汇率口径不确定时先说明假设，再给数
6. 业务日以分区键为准，不要用 CURRENT_DATE 当权威业务日 unless用户明确要求「今天」
"""
