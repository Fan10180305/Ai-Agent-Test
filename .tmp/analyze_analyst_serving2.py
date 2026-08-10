# -*- coding: utf-8 -*-
import re
from pathlib import Path
from collections import Counter, defaultdict

root = Path("dags")


def extract_sensor_pairs(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    pairs = []
    for m in re.finditer(
        r"(\w+)\s*=\s*create_external_sensor\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        text,
    ):
        pairs.append((m.group(1), m.group(2), m.group(3)))
    for m in re.finditer(
        r"(\w+)\s*=\s*create_skip_external_sensor\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        text,
    ):
        pairs.append((m.group(1), m.group(2) + "[SKIP]", m.group(3)))
    return pairs, text


def fanout_from_waits(text, wait_names):
    fan = Counter()
    # flatten chains: a >> b >> c and a >> [b,c]
    # For each wait_X >> RHS, count reachable BQ-like tokens until end of statement
    for w in wait_names:
        # find all occurrences of wait in dependency section
        for m in re.finditer(rf"{w}\s*>>\s*([^\n]+)", text):
            rhs = m.group(1)
            toks = re.findall(r"[A-Za-z_][\w]*", rhs)
            # exclude wait_/start_/Dummy-ish
            toks = [t for t in toks if not t.startswith("wait_") and t not in ("start_task", "start", "start_new_task")]
            fan[w] += len(toks)
        # also patterns wait >> [a,b]
        for m in re.finditer(rf"{w}\s*>>\s*\[([^\]]+)\]", text, re.S):
            toks = re.findall(r"[A-Za-z_][\w]*", m.group(1))
            toks = [t for t in toks if not t.startswith("wait_")]
            fan[w] += len(toks)
    return fan


# analyst_d device_active / traffic waits
for pkg in ["qpon_analyst_d", "qpon_analyst_h", "qpon_risk_d", "qpon_data_server_d", "qpon_email_date_d"]:
    path = root / pkg / f"{pkg}.py"
    pairs, text = extract_sensor_pairs(path)
    print("=" * 60, pkg)
    print("sensors", len(pairs))
    up = Counter(p[1] for p in pairs)
    print("upstream_dags", dict(up))
    hourish = [p for p in pairs if "_h" in p[1] or p[2].endswith("_h")]
    print("hourish_sensors", hourish)
    # device_active / traffic / voucher
    da = [p for p in pairs if "device_active" in p[2] or "device_active" in p[0]]
    tr = [p for p in pairs if "traffic" in p[2] or "traffic" in p[0]]
    vo = [p for p in pairs if "voucher" in p[2]]
    print("device_active waits", da)
    print("traffic waits", tr)
    print("voucher waits", vo)
    wait_names = [p[0] for p in pairs]
    fan = fanout_from_waits(text, wait_names)
    # also TimeDeltaSensor named wait_
    for m in re.finditer(r"^(wait_\w+)\s*=", text, re.M):
        if m.group(1) not in wait_names:
            wait_names.append(m.group(1))
    fan = fanout_from_waits(text, wait_names)
    print("fanout top", fan.most_common(12))
    # dummy empty
    if "start_new_task" in text:
        after = re.findall(r"start_new_task\s*>>\s*([^\n]+)", text)
        print("start_new_task downstream", after or "NONE")
        if re.search(r"start_task\s*>>\s*start_new_task\s*$", text, re.M):
            print("start>>start_new_task bare YES")
    # bare start >> task without wait
    bare = []
    for m in re.finditer(r"start_task\s*>>\s*([A-Za-z_][\w]*)\s*$", text, re.M):
        t = m.group(1)
        if not t.startswith("wait_") and t != "start_new_task":
            bare.append(t)
    # also start >> [..]
    for m in re.finditer(r"start_task\s*>>\s*\[([^\]]+)\]", text, re.S):
        for t in re.findall(r"[A-Za-z_][\w]*", m.group(1)):
            if not t.startswith("wait_"):
                bare.append(t)
    print("bare_start_tasks sample", bare[:20], "n", len(bare))


# ES exception patterns
print("\n==== ES EXCEPTION PATTERNS ====")
for f in (root / "qpon_data_server_d" / "tasks").glob("*es*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    has_try = "try:" in t
    swallow = bool(re.search(r"except\s+Exception[^\n]*:\s*\n\s*(print|log\.(error|warning|info)|pass)", t))
    raise_after = "raise" in t.split("except")[-1] if "except" in t else False
    uses_cloud = "cloud_run_write_aliyun_es" in t or "write_aliyun_es" in t
    uses_delete = "delete_by_field" in t or "delete" in f.name
    print(f.name, "try", has_try, "swallow?", swallow, "raise_in_except_tail?", raise_after, "cloud_run", uses_cloud, "deleteish", uses_delete)
    # show except blocks briefly
    for m in re.finditer(r"except[^\n]+:\n(?:[ \t]+[^\n]*\n){0,4}", t):
        block = m.group(0).strip().replace("\n", " | ")
        print("  ", block[:180])


# alarm tasks exception
print("\n==== ALARM TASKS ====")
for f in [
    root / "qpon_analyst_alarm_d/tasks/l0l1_indicators_monitoring_alert_d.py",
    root / "qpon_analyst_alarm_h/tasks/qpon_dau_bigquery_adjust_contrast_alert_h.py",
]:
    t = f.read_text(encoding="utf-8", errors="replace")
    print(f.name, "lines", len(t.splitlines()))
    print("  tokens", "TtSend" in t, "except" in t, "webhook" in t.lower() or "yzjtoken" in t)
    for m in re.finditer(r"except[^\n]+:\n(?:[ \t]+[^\n]*\n){0,5}", t):
        print("  EX", m.group(0).strip().replace("\n", " | ")[:200])


# analyst_h sensors detail
print("\n==== ANALYST_H SENSORS RAW ====")
text = (root / "qpon_analyst_h/qpon_analyst_h.py").read_text(encoding="utf-8", errors="replace")
for m in re.finditer(r"create_(?:skip_)?external_sensor\s*\([^)]+\)", text, re.S):
    print(re.sub(r"\s+", " ", m.group(0))[:200])
# also check ExternalTaskSensor / Skip
print("SkipSensor?", "Skip" in text, "create_skip", "create_skip_external_sensor" in text)
# how does it wait hour upstream?
for line in text.splitlines():
    if "wait_" in line and ("=" in line or ">>" in line):
        if "create_" in line or "Sensor" in line or "Dummy" in line or "TimeDelta" in line:
            print(line.strip()[:180])


# risk feishu / black list
print("\n==== RISK SPECIAL ====")
for name in ["base_black_list_merchant.py", "feature_merchant_risk_info_concat.py"]:
    p = list((root/"qpon_risk_d").rglob(name))[0]
    t = p.read_text(encoding="utf-8", errors="replace")
    print(name, "feishu", "feishu" in t.lower(), "COMPLETED", "COMPLETED" in t, "RETURN", "RETURN" in t, "2999", "2999" in t)


# daily report report_date math
print("\n==== DAILY REPORT DATE MATH ====")
print("schedule 0 2; rpt 0 18; delta +8h")
print("report_date = execution_date - 2h .date()")
print("If logical date of daily_report is D 02:00 UTC, wait looks for rpt logical date = D 02:00 - 8h = (D-1) 18:00 UTC")
