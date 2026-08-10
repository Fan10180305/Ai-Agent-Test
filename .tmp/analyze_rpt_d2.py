# -*- coding: utf-8 -*-
"""Deeper spot-checks for rpt_d representative tasks."""
import re
from pathlib import Path

ROOT = Path("dags/qpon_rpt_d")
ENTRY = (ROOT / "qpon_rpt_d.py").read_text(encoding="utf-8")
lines = ENTRY.splitlines()

# marker wiring
print("=== MARKER EDGES ===")
for i, ln in enumerate(lines, 1):
    if "marker_" in ln and not ln.lstrip().startswith("#"):
        print(f"L{i}: {ln.strip()[:180]}")

# analyst / data_server waits
print("=== CROSS LAYER NON ODS/DWD/DIM/DWS ===")
for i, ln in enumerate(lines, 1):
    if ("qpon_analyst" in ln or "qpon_data_server" in ln) and "create_external" in ln and not ln.lstrip().startswith("#"):
        print(f"L{i}: {ln.strip()[:180]}")

# self waits?
for i, ln in enumerate(lines, 1):
    if 'create_external_sensor(dag, "qpon_rpt_d"' in ln and not ln.lstrip().startswith("#"):
        print(f"SELF L{i}: {ln.strip()[:180]}")

# business indicator dependency block
print("=== BUSINESS INDICATOR BLOCK L1480-1570 ===")
for i in range(1479, min(1570, len(lines))):
    print(f"L{i+1}: {lines[i]}")

# ES BQ predecessors
print("=== ES WIRING ===")
for i, ln in enumerate(lines, 1):
    if "_es" in ln and ">>" in ln and not ln.lstrip().startswith("#"):
        print(f"L{i}: {ln.strip()[:200]}")
    if re.search(r"_es\b", ln) and ("start_task" in ln or ">>" in ln) and not ln.lstrip().startswith("#"):
        if "_es" in ln:
            print(f"L{i}: {ln.strip()[:200]}")

# find lines around channe_es and trade_es
for key in ["rpt_channe_store_sales_overview_statistics_es", "rpt_trade_merchant_statis_dashboard_d_es", "rpt_department_sale_statis_dashboard_es"]:
    print(f"-- edges involving {key}")
    for i, ln in enumerate(lines, 1):
        if key in ln and not ln.lstrip().startswith("#") and (">>" in ln or key + " =" in ln or i > 1800):
            # print context window for dependency
            pass
    # search in dependency section for var without create
    for i, ln in enumerate(lines, 1):
        if key in ln and i > 860 and not ln.lstrip().startswith("#"):
            print(f"L{i}: {ln.strip()[:200]}")

FILES = {
    "detail": "tasks/rpt_business_indicator_detail_d.py",
    "summary": "tasks/rpt_business_indicator_summary_d.py",
    "merchant_daily": "tasks/rpt_merchant_daily_data_inc_d.py",
    "dim_consume": "tasks/rpt_business_dim_consume_detail_d.py",
    "area": "tasks/rpt_area_store_redeemed_performance_inc_d.py",
    "retention": "tasks/rpt_app_newuser_retention_statistic_new.py",
    "es": "tasks/rpt_trade_merchant_statis_dashboard_d_es.py",
    "channe_es": "tasks/rpt_channe_merchant_ranking_list_es.py",
    "gtv": "tasks/rpt_app_month_gtv_statistic_inc_d.py",
    "voucher_stat": "tasks/rpt_business_payment_redeem_detail_qbi.py",
}

for label, rel in FILES.items():
    p = ROOT / rel
    if not p.exists():
        print(f"MISSING {rel}")
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    print(f"\n===== {label}: {rel} lines={len(t.splitlines())} =====")
    # key snippets
    for pat in [
        r"DELETE\s+FROM[^\n]{0,120}",
        r"INSERT\s+INTO[^\n]{0,120}",
        r"MERGE\s+[^\n]{0,120}",
        r"2999-12-31[^\n]{0,80}",
        r"partition_date[^\n]{0,100}",
        r"order_status[^\n]{0,120}",
        r"dim_merchant_basic_info[^\n]{0,120}",
        r"device_active[^\n]{0,120}",
        r"access_cloud_run_write_aliyun_es[^\n]{0,120}",
        r"delete_by_field_condition[^\n]{0,120}",
        r"COMPLETED[^\n]{0,80}",
        r"RETURN[^\n]{0,80}",
        r"voucher_all_h|_h\b",
    ]:
        ms = list(re.finditer(pat, t, re.I))
        if not ms:
            continue
        print(f"  PAT {pat[:40]}... count={len(ms)}")
        for m in ms[:3]:
            # line context
            start = t.rfind("\n", 0, m.start()) + 1
            end = t.find("\n", m.end())
            print("   ", t[start:end][:200].strip())

# count how many rpt tasks wait device_active in edges
print("\n=== DOWNSTREAM of device_active waits ===")
# crude parse: blocks containing wait_dws_qpon_device_active ending with >> task
text = "\n".join(lines[860:])
# find >> targets after device_active mentions - collect task names on same multi-line statement is hard
# instead: find lines with >> that have device_active in previous 15 lines
targets = []
for i in range(860, len(lines)):
    if "device_active" in lines[i] and not lines[i].lstrip().startswith("#"):
        # look forward for >>
        for j in range(i, min(i + 25, len(lines))):
            if ">>" in lines[j] and not lines[j].lstrip().startswith("#"):
                m = re.search(r">>\s*(\w+)", lines[j])
                if m:
                    targets.append(m.group(1))
                break
print("approx targets", len(targets), "unique", len(set(targets)))
from collections import Counter
c = Counter(targets)
print("top", c.most_common(25))

# voucher_h naked reads in live tasks
print("\n=== voucher_all_h / hour tables in tasks ===")
for f in sorted((ROOT / "tasks").glob("*.py")):
    t = f.read_text(encoding="utf-8", errors="replace")
    if re.search(r"order_voucher_all_h|voucher_all_h|_feature_.*_h\b", t):
        print(f.name)

# dim merchant partition patterns in 2999 files
print("\n=== 2999 files partition patterns ===")
for f in (ROOT / "tasks").glob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "2999-12-31" not in t:
        continue
    day = bool(re.search(r"dim_merchant_basic_info[^\n]{0,200}partition_date\s*=\s*['\"]?\s*\{\{", t, re.I | re.S))
    # simpler counts
    n2999 = len(re.findall(r"2999-12-31", t))
    n_merch = len(re.findall(r"dim_merchant_basic_info", t))
    # whether business day partition also present near merchant
    has_day_part = bool(re.search(r"dim_merchant_basic_info[\s\S]{0,300}partition_date\s*=\s*'?\{\{", t)) or bool(
        re.search(r"partition_date\s*=\s*'?\{\{[\s\S]{0,200}dim_merchant_basic_info", t)
    )
    print(f"{f.name}: 2999x{n2999} merchantx{n_merch}")
