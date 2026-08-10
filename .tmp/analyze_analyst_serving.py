# -*- coding: utf-8 -*-
import re
from pathlib import Path
from collections import Counter

root = Path("dags")
packages = [
    "qpon_analyst_d",
    "qpon_analyst_h",
    "qpon_analyst_alarm_d",
    "qpon_analyst_alarm_h",
    "qpon_risk_d",
    "qpon_daily_report",
    "qpon_data_server_d",
    "qpon_email_date_d",
    "qpon_search_d",
]


def analyze_entry(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    schedule = re.findall(r"schedule_interval\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not schedule:
        schedule = re.findall(r"schedule\s*=\s*['\"]([^'\"]+)['\"]", text)

    calls = []
    for m in re.finditer(r"create_external_sensor\s*\((.*?)\)", text, re.S):
        qs = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
        calls.append(qs)

    skip_calls = []
    for m in re.finditer(r"create_skip_external_sensor\s*\((.*?)\)", text, re.S):
        qs = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
        skip_calls.append(qs)

    ets = []
    for m in re.finditer(r"ExternalTaskSensor\s*\((.*?)\)", text, re.S):
        block = m.group(1)
        ed = re.search(r"external_dag_id\s*=\s*['\"]([^'\"]+)['\"]", block)
        et = re.search(r"external_task_id\s*=\s*['\"]([^'\"]+)['\"]", block)
        delta = re.search(r"execution_delta\s*=\s*([^\n,]+)", block)
        retries = re.search(r"retries\s*=\s*(\d+)", block)
        timeout = re.search(r"timeout\s*=\s*(\d+)", block)
        poke = re.search(r"poke_interval\s*=\s*(\d+)", block)
        ets.append(
            {
                "dag": ed.group(1) if ed else None,
                "task": et.group(1) if et else None,
                "delta": delta.group(1).strip() if delta else None,
                "retries": retries.group(1) if retries else None,
                "timeout": timeout.group(1) if timeout else None,
                "poke": poke.group(1) if poke else None,
            }
        )

    wait_assign = re.findall(r"^(wait_\w+)\s*=", text, re.M)
    orphans = []
    for w in wait_assign:
        if len(re.findall(rf"\b{w}\b", text)) <= 1:
            orphans.append(w)

    bare_start = re.findall(r"start\s*>>\s*(\w+)", text)
    hour_waits = [c for c in calls if any(("_h" in x) for x in c)]

    up = Counter()
    for c in calls:
        for x in c:
            if x.startswith("qpon_") or x.startswith("Qpon_"):
                up[x] += 1
                break

    # dependency edges: left >> right with wait_
    edges_from_wait = Counter()
    for m in re.finditer(r"(wait_\w+)\s*>>\s*([^\n#]+)", text):
        rhs = m.group(2)
        targets = re.findall(r"[A-Za-z_][\w]*", rhs)
        edges_from_wait[m.group(1)] += len(targets)

    return {
        "file": str(path),
        "lines": len(lines),
        "schedule": schedule,
        "bq": len(re.findall(r"create_composer_bq_task\s*\(", text)),
        "py": len(re.findall(r"create_composer_python_task\s*\(", text)),
        "sensor": len(re.findall(r"create_external_sensor\s*\(", text)),
        "skip_factory": len(re.findall(r"create_skip_external_sensor\s*\(", text)),
        "marker": len(re.findall(r"create_external_marker\s*\(", text)),
        "dummy": len(re.findall(r"DummyOperator", text)),
        "python_op": len(re.findall(r"PythonOperator\s*\(", text)),
        "sensor_calls": len(calls),
        "skip_calls": skip_calls,
        "ets": ets,
        "wait_assign": len(wait_assign),
        "orphans": orphans,
        "bare_start": bare_start,
        "hour_sensor": len(hour_waits),
        "upstream": dict(up.most_common(20)),
        "top_wait_fanout": edges_from_wait.most_common(10),
    }


def scan_sql_patterns(pkg: str):
    p = root / pkg
    files = list(p.rglob("*.py"))
    patterns = {
        "COMPLETED": 0,
        "RETURN": 0,
        "2999-12-31": 0,
        "voucher_all_h": 0,
        "voucher_all": 0,
        "device_active": 0,
        "traffic": 0,
        "except": 0,
        "write_aliyun": 0,
        "genai": 0,
        "feishu": 0,
    }
    hits = {k: [] for k in patterns}
    for f in files:
        if f.name.startswith("__"):
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        for k in list(patterns):
            if k == "except":
                if re.search(r"except\s+Exception", t) and (
                    "_es" in f.name or "es" in f.name.lower() or "alert" in f.name.lower()
                ):
                    patterns[k] += 1
                    hits[k].append(str(f.relative_to(root)))
            elif k == "write_aliyun":
                if "write_aliyun" in t or "cloud_run_write" in t:
                    patterns[k] += 1
                    hits[k].append(str(f.relative_to(root)))
            elif k == "genai":
                if "genai" in t.lower() or "generate_narrative" in t:
                    patterns[k] += 1
                    hits[k].append(str(f.relative_to(root)))
            elif k == "feishu":
                if "feishu" in t.lower():
                    patterns[k] += 1
                    hits[k].append(str(f.relative_to(root)))
            else:
                c = t.count(k)
                if c:
                    patterns[k] += c
                    if len(hits[k]) < 8:
                        hits[k].append(f"{f.relative_to(root)}:{c}")
    return patterns, hits


for pkg in packages:
    p = root / pkg
    if not p.exists():
        print("MISSING", pkg)
        continue
    entries = [f for f in sorted(p.glob("*.py")) if not f.name.startswith("__")]
    # also search_d may have nested
    if pkg == "qpon_search_d":
        entries = [f for f in sorted(p.rglob("*.py")) if not f.name.startswith("__")]
    for f in entries:
        # skip tasks
        if "tasks" in f.parts:
            continue
        info = analyze_entry(f)
        print("=" * 70)
        print(f.name, "lines", info["lines"], "sched", info["schedule"])
        print(
            "bq",
            info["bq"],
            "py",
            info["py"],
            "sensor",
            info["sensor"],
            "skip_factory",
            info["skip_factory"],
            "marker",
            info["marker"],
            "dummy",
            info["dummy"],
            "PythonOp",
            info["python_op"],
        )
        print("hour_sensor", info["hour_sensor"], "skip_calls", info["skip_calls"])
        print("ets", info["ets"])
        print(
            "waits",
            info["wait_assign"],
            "orphan_n",
            len(info["orphans"]),
            "orphans",
            info["orphans"][:25],
        )
        print("bare_start", info["bare_start"][:30], "n", len(info["bare_start"]))
        print("upstream", info["upstream"])
        print("top_wait_fanout", info["top_wait_fanout"])
    pats, hits = scan_sql_patterns(pkg)
    print("SQL/PAT", pkg, pats)
    for k, v in hits.items():
        if v:
            print("  HIT", k, v[:6])
