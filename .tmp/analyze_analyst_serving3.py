# -*- coding: utf-8 -*-
import re
from pathlib import Path
from collections import Counter

text = Path("dags/qpon_analyst_d/qpon_analyst_d.py").read_text(encoding="utf-8")

# uncommented dependency lines only
live = []
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    live.append(line)

live_text = "\n".join(live)

# count wait_dws_qpon_device_active occurrences in live dependency edges
for w in [
    "wait_dws_qpon_device_active_info_inc_d",
    "wait_dws_qpon_device_active_info_all_d",
    "wait_dwd_product_order_voucher_all",
    "wait_dwd_qpon_event_traffic",
]:
    # count how many BQ task blocks include this wait
    # approach: find start_task >> [ ... ] >> task OR start >> wait >> task patterns
    print(w, "live refs", live_text.count(w))

# extract live dependency edges of form ... >> taskname
# Multisensor: start_task >> [ waits ] >> task
tasks_with_da_inc = set()
tasks_with_da_all = set()
tasks_with_voucher = set()
bare_live = []

# Parse multi-line brackets roughly
blocks = re.findall(r"start_task\s*>>\s*\[(.*?)\]\s*>>\s*(\w+)", live_text, re.S)
for body, task in blocks:
    if "wait_dws_qpon_device_active_info_inc_d" in body:
        tasks_with_da_inc.add(task)
    if "wait_dws_qpon_device_active_info_all_d" in body:
        tasks_with_da_all.add(task)
    if "wait_dwd_product_order_voucher_all" in body:
        tasks_with_voucher.add(task)

# single wait chains start >> wait >> task (multi)
# also start >> task bare
for m in re.finditer(r"start_task\s*>>\s*(\w+)\s*$", live_text, re.M):
    t = m.group(1)
    if not t.startswith("wait_") and t != "start_new_task":
        bare_live.append(t)

print("da_inc downstream tasks", sorted(tasks_with_da_inc), "n", len(tasks_with_da_inc))
print("da_all downstream tasks", sorted(tasks_with_da_all), "n", len(tasks_with_da_all))
print("voucher downstream", sorted(tasks_with_voucher), "n", len(tasks_with_voucher))
print("bare live", bare_live)

# orphan sensors: assigned waits not appearing in live_text dependency (beyond assignment)
pairs = re.findall(
    r"(\w+)\s*=\s*create_external_sensor\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
    text,
)
orphans = []
for name, dag, task in pairs:
    # count in live dependency section only (after 任务依赖)
    dep = text.split("任务依赖")[-1] if "任务依赖" in text else text
    dep_live = "\n".join(
        ln for ln in dep.splitlines() if ln.strip() and not ln.strip().startswith("#")
    )
    if name not in dep_live:
        orphans.append((name, dag, task))
print("orphan sensors", orphans, "n", len(orphans))
print("total sensors", len(pairs))

# risk device_active fanout
rtext = Path("dags/qpon_risk_d/qpon_risk_d.py").read_text(encoding="utf-8")
rlive = "\n".join(
    ln for ln in rtext.splitlines() if ln.strip() and not ln.strip().startswith("#")
)
print("risk da_inc refs", rlive.count("wait_dws_qpon_device_active_info_inc_d"))
rblocks = re.findall(r"start_task\s*>>\s*\[(.*?)\]\s*>>\s*(\w+)", rlive, re.S)
rda = [t for b, t in rblocks if "wait_dws_qpon_device_active_info_inc_d" in b]
print("risk da downstream", rda)

# check ES raise presence
print("\nES raise audit:")
for f in Path("dags/qpon_data_server_d/tasks").glob("*es*.py"):
    t = f.read_text(encoding="utf-8")
    # last 8 lines of except
    m = re.search(r"except Exception as e:\n(.*)", t, re.S)
    tail = m.group(1)[:120].replace("\n", " | ") if m else "NO"
    has_raise = bool(re.search(r"except Exception as e:\n(?:.*\n)*?\s+raise\b", t))
    print(f.name, "has_raise_after_except", has_raise, "|", tail)

# alarm_h sensor type
print("\nalarm_h sensor: create_external_sensor -> qpon_analyst_h (HOUR) = day factory on hour DAG")

# analyst_h RETURN on voucher_h
for f in Path("dags/qpon_analyst_h/tasks").glob("*.py"):
    t = f.read_text(encoding="utf-8")
    if "RETURN" in t and "voucher" in t:
        print(f.name, "RETURN+voucher_h?", "voucher_all_h" in t, "COMPLETED" in t)

# dim 2999 in data_server / risk / analyst_h
for pkg in ["qpon_data_server_d", "qpon_risk_d", "qpon_analyst_h", "qpon_analyst_d", "qpon_email_date_d"]:
    hits = []
    for f in Path(f"dags/{pkg}").rglob("*.py"):
        t = f.read_text(encoding="utf-8")
        if "2999-12-31" in t:
            hits.append(f.name)
    print(pkg, "2999 files", hits)

# email COMPLETED without RETURN
for f in Path("dags/qpon_email_date_d/tasks").glob("*.py"):
    t = f.read_text(encoding="utf-8")
    if "COMPLETED" in t or "RETURN" in t or "voucher" in t.lower():
        print(
            "email",
            f.name,
            "COMPLETED",
            t.count("COMPLETED"),
            "RETURN",
            t.count("RETURN"),
            "status",
            "status" in t.lower(),
        )
