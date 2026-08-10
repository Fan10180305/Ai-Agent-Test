# -*- coding: utf-8 -*-
import re
from pathlib import Path

# orphan sensors excluding commented lines
text = Path("dags/qpon_analyst_d/qpon_analyst_d.py").read_text(encoding="utf-8")
live_lines = []
for ln in text.splitlines():
    if ln.strip().startswith("#"):
        continue
    live_lines.append(ln)
live = "\n".join(live_lines)

pairs = re.findall(
    r"(\w+)\s*=\s*create_external_sensor\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
    live,
)
print("live sensors", len(pairs))
# dep section
idx = live.find("调起主任务")
dep = live[idx:] if idx >= 0 else live
orphans = [(n, d, t) for n, d, t in pairs if n not in dep]
wired = [(n, d, t) for n, d, t in pairs if n in dep]
print("wired", len(wired), "orphans", len(orphans))
for o in orphans:
    print("  orphan", o)

# same for risk / data_server / email / alarm
for pkg in [
    "qpon_risk_d",
    "qpon_data_server_d",
    "qpon_email_date_d",
    "qpon_analyst_alarm_d",
    "qpon_analyst_alarm_h",
]:
    p = Path(f"dags/{pkg}/{pkg}.py")
    t = p.read_text(encoding="utf-8")
    live = "\n".join(ln for ln in t.splitlines() if not ln.strip().startswith("#"))
    pairs = re.findall(
        r"(\w+)\s*=\s*create_external_sensor\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        live,
    )
    skips = re.findall(
        r"(\w+)\s*=\s*create_external_task_skip_sensor_hour\s*\(\s*dag\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        live,
    )
    # find dependency marker
    for marker in ["调起主任务", "任务依赖", "start_task >>"]:
        if marker in live:
            break
    # use last half as dep heuristic
    dep = live[len(live) // 3 :]
    orphans = [x for x in pairs if x[0] not in dep]
    print(pkg, "sensor", len(pairs), "skip", len(skips), "orphan_est", len(orphans), orphans[:8])

# alarm_h exact
ah = Path("dags/qpon_analyst_alarm_h/qpon_analyst_alarm_h.py").read_text(encoding="utf-8")
print("alarm_h line83:", [ln.strip() for ln in ah.splitlines() if "create_external" in ln and not ln.strip().startswith("#")])

# search on_failure_callback bug?
print("search callback:", "on_failure_callback=send_failure_alert_factory," in Path("dags/qpon_search_d/qpon_search_store_fea_export.py").read_text(encoding="utf-8"))

# data_server wait_dim_daytime orphan?
ds = Path("dags/qpon_data_server_d/qpon_data_server_d.py").read_text(encoding="utf-8")
dslive = "\n".join(ln for ln in ds.splitlines() if not ln.strip().startswith("#"))
for name in ["wait_dim_daytime_info", "wait_ods_t_life_voucher_consume_record_all_d"]:
    print(name, "in dep?", name in dslive.split("调起主任务")[-1] if "调起主任务" in dslive else "n/a")
