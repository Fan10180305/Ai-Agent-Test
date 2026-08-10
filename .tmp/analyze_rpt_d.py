# -*- coding: utf-8 -*-
"""Analyze qpon_rpt_d for Step 08h deep dive."""
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "dags/qpon_rpt_d/qpon_rpt_d.py"
TASKS = ROOT / "dags/qpon_rpt_d/tasks"
text = ENTRY.read_text(encoding="utf-8")
lines = text.splitlines()
print("LINES", len(lines))
print("BYTES", len(text.encode("utf-8")))

# active sensors
sensor_re = re.compile(
    r'^(\w+)\s*=\s*create_external_sensor\(\s*dag\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']',
    re.M,
)
sensors = sensor_re.findall(text)
print("ACTIVE_SENSORS", len(sensors))
by_dag = defaultdict(list)
for name, d, t in sensors:
    by_dag[d].append((name, t))
for d in sorted(by_dag):
    print(f"  {d}: {len(by_dag[d])}")

commented = re.findall(r"^#\s*(wait_\w+)\s*=\s*create_external_sensor", text, re.M)
print("COMMENTED_SENSORS", len(commented))

print("SKIP_IMPORT", "create_external_task_skip_sensor" in text)
for pat in ["qpon_ods_h", "qpon_dwd_h", "qpon_dim_h", "qpon_dws_h", "qpon_rpt_h"]:
    # only uncommented
    cnt = 0
    for ln in lines:
        if ln.lstrip().startswith("#"):
            continue
        if pat in ln:
            cnt += 1
    print(f"  live_ref {pat}: {cnt}")

bq = re.findall(
    r'^(\w+)\s*=\s*create_composer_bq_task\(\s*dag\s*,\s*warehouse_layer\s*,\s*["\']([^"\']+)["\']',
    text,
    re.M,
)
py = re.findall(
    r'^(\w+)\s*=\s*create_composer_python_task\(\s*dag\s*,\s*warehouse_layer\s*,\s*["\']([^"\']+)["\']',
    text,
    re.M,
)
print("BQ_TASKS", len(bq))
print("PY_TASKS", len(py))
print("COMMENTED_BQ", len(re.findall(r"^#\s*\w+\s*=\s*create_composer_bq_task", text, re.M)))
print("COMMENTED_PY", len(re.findall(r"^#\s*\w+\s*=\s*create_composer_python_task", text, re.M)))

markers = re.findall(r"create_external_marker\(\s*dag\s*,\s*[\"']([^\"']+)[\"']\s*,\s*[\"']([^\"']+)[\"']", text)
print("MARKERS", markers)

es_tasks = [(a, b) for a, b in py if "_es" in b.lower()]
print("ES_PY_TASKS", len(es_tasks))
for a, b in es_tasks:
    print(" ", b)

# dependency edges: find wait_* used on RHS of >>
# crude: extract all >> lines and see which wait vars appear as predecessors of tasks
edge_block = "\n".join(lines[860:])  # dependency section approx
wired_waits = set(re.findall(r"\b(wait_\w+)\b", edge_block))
# remove commented lines from edge section
wired = set()
for ln in lines[860:]:
    s = ln.strip()
    if not s or s.startswith("#"):
        continue
    for w in re.findall(r"\b(wait_\w+)\b", ln):
        wired.add(w)

created = {name for name, _, _ in sensors}
orphans = sorted(created - wired)
wired_only = sorted(wired & created)
print("WIRED_SENSORS", len(wired_only))
print("ORPHAN_SENSORS", len(orphans))
for o in orphans:
    dag_t = next((d, t) for n, d, t in sensors if n == o)
    print(f"  ORPHAN {o} -> {dag_t[0]}.{dag_t[1]}")

# device_active wiring
print("--- device_active ---")
for i, ln in enumerate(lines, 1):
    if "device_active" in ln and not ln.lstrip().startswith("#"):
        print(f"L{i}: {ln.strip()[:160]}")

# ShortCircuit
print("--- ShortCircuit ---")
for i, ln in enumerate(lines, 1):
    if "ShortCircuit" in ln or "wait_check_" in ln:
        if "create_external" in ln:
            continue
        print(f"L{i}: {ln.strip()[:160]}")

# 2999 / order_status in tasks
print("--- task SQL patterns ---")
task_files = list(TASKS.glob("*.py"))
print("TASK_FILES", len(task_files))
pat_counts = defaultdict(int)
samples = defaultdict(list)
for f in task_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    for key, pat in [
        ("DELETE+INSERT", r"DELETE\s+FROM"),
        ("MERGE", r"\bMERGE\b"),
        ("2999", r"2999-12-31"),
        ("order_status", r"order_status"),
        ("COMPLETED", r"COMPLETED"),
        ("RETURN", r"'RETURN'|\"RETURN\""),
        ("device_active", r"device_active"),
        ("dim_merchant", r"dim_merchant_basic_info"),
        ("voucher_all_h", r"voucher_all_h|order_voucher_all_h"),
        ("access_cloud_run", r"access_cloud_run_write_aliyun_es"),
        ("delete_by_field", r"delete_by_field_condition"),
        ("partition_date", r"partition_date"),
    ]:
        if re.search(pat, t, re.I):
            pat_counts[key] += 1
            if len(samples[key]) < 8:
                samples[key].append(f.name)

for k, v in sorted(pat_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} files")
    print("   ", ", ".join(samples[k]))

# DWS waits wiring targets
print("--- DWS waits ---")
for name, d, t in sensors:
    if d == "qpon_dws_d":
        print(f"  {name} wired={name in wired} -> {t}")

print("--- DIM waits ---")
for name, d, t in sensors:
    if d == "qpon_dim_d":
        print(f"  {name} wired={name in wired} -> {t}")

# business indicator chain
print("--- business_indicator ---")
for i, ln in enumerate(lines, 1):
    if "business_indicator" in ln.lower() and not ln.lstrip().startswith("#"):
        print(f"L{i}: {ln.strip()[:180]}")

# daily_report consumers outside
print("--- external wait on rpt_d ---")
for p in (ROOT / "dags").rglob("*.py"):
    if "qpon_rpt_d" in p.parts:
        continue
    tt = p.read_text(encoding="utf-8", errors="replace")
    if "qpon_rpt_d" in tt and ("ExternalTaskSensor" in tt or "create_external_sensor" in tt or "create_external_task_skip" in tt):
        # extract lines
        hits = []
        for ln in tt.splitlines():
            if "qpon_rpt_d" in ln and not ln.lstrip().startswith("#"):
                hits.append(ln.strip()[:140])
        if hits:
            print(p.relative_to(ROOT))
            for h in hits[:12]:
                print(" ", h)
