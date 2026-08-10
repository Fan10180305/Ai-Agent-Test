# -*- coding: utf-8 -*-
import re
import pathlib
import collections

root = pathlib.Path(r"D:/Fanisy/Project_File/PycharmProjects/Professional/qpon-bigdata-agent")
p = root / "dags/qpon_tag_d/qpon_tag_d.py"
text = p.read_text(encoding="utf-8")
lines = text.splitlines()

live_sensors = []
commented_sensors = []
for i, l in enumerate(lines, 1):
    s = l.strip()
    if "create_external_sensor" in s or "create_external_task_skip" in s:
        if s.startswith("#"):
            commented_sensors.append((i, s[:140]))
        else:
            m = re.search(r'create_external_sensor\([^,]+,\s*"([^"]+)",\s*"([^"]+)"', s)
            if m:
                live_sensors.append((i, m.group(1), m.group(2)))
            else:
                live_sensors.append((i, "?", s[:100]))

live_bq = []
commented_bq = []
for i, l in enumerate(lines, 1):
    s = l.strip()
    if "create_composer_bq_task" in s:
        if s.startswith("#"):
            commented_bq.append((i, s[:140]))
        else:
            m = re.search(r'create_composer_bq_task\([^,]+,\s*([^,]+),\s*"([^"]+)"', s)
            if m:
                live_bq.append((i, m.group(1).strip(), m.group(2)))

print("FILE_LINES", len(lines))
print("LIVE_SENSORS", len(live_sensors))
print("BY_UPSTREAM", dict(collections.Counter(x[1] for x in live_sensors)))
for x in live_sensors:
    print(f"  S {x[0]} {x[1]}.{x[2]}")
print("COMMENTED_SENSORS", len(commented_sensors))
for x in commented_sensors:
    print(f"  #S {x[0]} {x[1]}")
print("LIVE_BQ", len(live_bq))
print("BY_LAYER", dict(collections.Counter(x[1] for x in live_bq)))
print("COMMENTED_BQ", len(commented_bq))
for x in commented_bq:
    print(f"  #BQ {x[0]} {x[1]}")
print("SKIP_IMPORT", "create_external_task_skip" in text)
print("SKIP_LIVE", sum(1 for l in lines if "create_external_task_skip" in l and not l.strip().startswith("#")))

# Parse >> edges roughly: collect sensor vars that appear after >>
sensor_vars = {f"wait_{s[2]}" if False else None for s in live_sensors}
# Better: extract names from assignment
sensor_name_map = {}
for i, l in enumerate(lines, 1):
    s = l.strip()
    if s.startswith("#"):
        continue
    m = re.match(r'(wait_\w+)\s*=\s*create_external_sensor', s)
    if m:
        sensor_name_map[m.group(1)] = i

# Which sensors are in dependency section (after 任务依赖)
dep_start = None
for i, l in enumerate(lines):
    if "任务依赖顺序" in l:
        dep_start = i
        break
dep_text = "\n".join(lines[dep_start:]) if dep_start else ""
wired = []
orphans = []
for name in sensor_name_map:
    # appear as operand in >>
    if re.search(rf"\b{name}\b", dep_text):
        wired.append(name)
    else:
        orphans.append(name)
print("SENSOR_WIRED", len(wired), wired)
print("SENSOR_ORPHAN_CREATE", orphans)

# Count fanout: lines with wait_dws_qpon_device_active
for key in [
    "wait_dws_qpon_device_active_info_inc_d",
    "wait_dws_qpon_device_active_info_all_d",
    "wait_dwd_product_order_voucher_all",
    "wait_dim_store",
    "wait_dim_device_latest_all_d",
    "start_new_task",
]:
    # count tasks in list after this wait - rough: find blocks
    pass

# Analyze task SQL targets
tasks_dir = root / "dags/qpon_tag_d/tasks"
py_files = list(tasks_dir.rglob("*.py"))
print("TASK_PY_FILES", len(py_files))

target_counter = collections.Counter()
meta_count = 0
return_files = []
dim2999 = []
dim_day = []
device_active_reads = []
delete_patterns = collections.Counter()
status_filters = collections.Counter()
no_meta = []
insert_table = {}

for f in py_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    # insert_table_id
    m = re.search(r'insert_table_id\s*=\s*"([^"]+)"', t)
    table = m.group(1) if m else None
    if not table:
        # base tables maybe different
        for cand in ["tag_qpon_all_d", "tag_qpon_userid_all_d", "tag_qpon_merchant_all_d", "tag_qpon_store_all_d",
                      "tag_qpon_base_qponid_all_d", "tag_qpon_base_userid_all_d", "tag_qpon_base_merchantid_all_d",
                      "tag_qpon_base_storeid_all_d", "tag_qpon_qponid_userid_latest"]:
            if cand in t and ("insert" in t.lower() or "CREATE OR REPLACE" in t or "delete" in t.lower()):
                # check write
                pass
        m2 = re.findall(r'(?:into|INTO|table_id\s*=)\s*[`"]?[\w.-]*?(tag_qpon_[\w]+)[`"]?', t)
        # fallback: insert_table patterns
    ds = re.search(r'insert_dataset_id\s*=\s*"([^"]+)"', t)
    dataset = ds.group(1) if ds else "?"
    if table:
        target_counter[f"{dataset}.{table}"] += 1
        insert_table[str(f.relative_to(tasks_dir))] = f"{dataset}.{table}"
    if "tag_qpon_metadata" in t:
        meta_count += 1
    else:
        no_meta.append(str(f.relative_to(tasks_dir)))
    if re.search(r"\bRETURN\b", t):
        return_files.append(str(f.relative_to(tasks_dir)))
    if "2999-12-31" in t or "2999/12/31" in t:
        dim2999.append(str(f.relative_to(tasks_dir)))
    if re.search(r"dim_product_basic_info|dim_merchant|dim_store", t, re.I):
        if "2999" in t:
            pass
        else:
            # check partition filter
            if re.search(r"partition_date|dayno", t):
                dim_day.append(str(f.relative_to(tasks_dir)))
    if "dws_qpon_device_active" in t:
        device_active_reads.append(str(f.relative_to(tasks_dir)))
    if re.search(r"DELETE\s+FROM", t, re.I):
        if "tag_name" in t and "dayno" in t:
            delete_patterns["dayno+tag_name"] += 1
        elif "dayno" in t:
            delete_patterns["dayno"] += 1
        else:
            delete_patterns["other_delete"] += 1
    for st in re.findall(r"order_status\s*(?:in|=)\s*\(?([^)\n]+)\)?", t, re.I):
        status_filters[st.strip()[:80]] += 1
    for st in re.findall(r"(?:COMPLETED|RETURN|OK|PAID|SUCCESS)", t):
        status_filters[f"token:{st}"] += 1

print("WRITE_TARGETS", dict(target_counter))
print("META_MERGE_FILES", meta_count)
print("NO_META_COUNT", len(no_meta))
print("NO_META_SAMPLE", no_meta[:20])
print("RETURN_FILES", len(return_files), return_files[:30])
print("DIM2999", dim2999)
print("DEVICE_ACTIVE_READS", len(device_active_reads))
for x in device_active_reads:
    print("  DA", x)
print("DELETE_PATTERNS", dict(delete_patterns))
print("STATUS_TOKEN_COUNTS", {k: v for k, v in status_filters.items() if k.startswith("token:")})

# Live BQ stems that write each wide table
live_stems = {x[2] for x in live_bq}
# Map stem to file
stem_to_file = {}
for f in py_files:
    stem = f.stem
    stem_to_file[stem] = f

wide = collections.defaultdict(list)
for stem in sorted(live_stems):
    f = stem_to_file.get(stem)
    if not f:
        # try subdirs
        matches = list(tasks_dir.rglob(f"{stem}.py"))
        f = matches[0] if matches else None
    if not f:
        wide["MISSING_FILE"].append(stem)
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'insert_table_id\s*=\s*"([^"]+)"', t)
    if m:
        wide[m.group(1)].append(stem)
    else:
        # base table writers
        if "tag_qpon_base_" in stem or stem.startswith("tag_qpon_base"):
            wide["BASE:" + stem].append(stem)
        elif "CREATE OR REPLACE TABLE" in t or "create or replace table" in t.lower():
            m3 = re.search(r"(?:CREATE OR REPLACE TABLE|create or replace table)\s+[`\"]?([\w.\-]+)[`\"]?", t, re.I)
            wide["REPLACE:" + (m3.group(1) if m3 else "?")].append(stem)
        else:
            wide["UNKNOWN"].append(stem)

print("WIDE_TABLE_WRITERS")
for k, v in sorted(wide.items(), key=lambda x: (-len(x[1]), x[0])):
    print(f"  {k}: {len(v)}")

# Dependency fanout counts: extract list lengths after each wait
# Simple approach: find "wait_xxx >> [" and count commas+1 until ]
fanouts = {}
i = 0
while i < len(lines):
    l = lines[i]
    m = re.search(r"(wait_\w+)\s*>>\s*\[", l)
    if m and not l.strip().startswith("#"):
        name = m.group(1)
        buf = l[m.end() - 1 :]  # from [
        j = i
        while "]" not in buf and j + 1 < len(lines):
            j += 1
            buf += "\n" + lines[j]
        # count identifiers that look like tasks (contain = not, just names ending or commas)
        inner = buf[buf.find("[") + 1 : buf.find("]")]
        items = [x.strip().rstrip(",") for x in inner.split("\n") if x.strip() and not x.strip().startswith("#")]
        items = [x for x in items if x and x != "]"]
        # also split by comma on same line
        flat = []
        for it in items:
            for part in it.split(","):
                part = part.strip().rstrip(",")
                if part and re.match(r"^[\w]+$", part):
                    flat.append(part)
        fanouts[name] = fanouts.get(name, 0) + len(flat)
        i = j
    # also wait >> single
    m2 = re.search(r"(wait_\w+)\s*>>\s*(\w+)\s*$", l.strip())
    if m2 and not l.strip().startswith("#"):
        fanouts[m2.group(1)] = fanouts.get(m2.group(1), 0) + 1
    i += 1

print("FANOUTS")
for k, v in sorted(fanouts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# Check for hour upstream refs
hour_refs = [l for l in lines if re.search(r"qpon_\w+_h|_h\"|ods_.*_h|dwd_.*_h", l) and "create_external" in l]
print("HOUR_SENSOR_LINES", hour_refs[:10], "count", len(hour_refs))

# Downstream waiting on qpon_tag_d
dags = root / "dags"
tag_waiters = []
for f in dags.rglob("*.py"):
    if "qpon_tag_d" in str(f) and "test" not in str(f).lower():
        continue
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if 'create_external_sensor' in t and '"qpon_tag_d"' in t:
        tag_waiters.append(str(f.relative_to(root)))
    if "qpon_tag_d" in t and ("ExternalTaskSensor" in t or "create_external" in t):
        if "qpon_tag_d/" not in str(f).replace("\\", "/"):
            tag_waiters.append(str(f.relative_to(root)))

print("TAG_WAITERS_UNIQUE", sorted(set(tag_waiters)))

# start_new_task wiring
print("START_NEW_TASK_EDGES")
for i, l in enumerate(lines, 1):
    if "start_new_task" in l and ">>" in l and not l.strip().startswith("#"):
        print(f"  L{i}: {l.strip()[:160]}")
