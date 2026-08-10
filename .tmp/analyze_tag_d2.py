# -*- coding: utf-8 -*-
import re
import pathlib
import collections

root = pathlib.Path(r"D:/Fanisy/Project_File/PycharmProjects/Professional/qpon-bigdata-agent")
p = root / "dags/qpon_tag_d/qpon_tag_d.py"
lines = p.read_text(encoding="utf-8").splitlines()

# Extract all dependency statements more carefully
dep_start = next(i for i, l in enumerate(lines) if "任务依赖顺序" in l)
dep_lines = lines[dep_start:]

# Find sensors with no BQ downstream: parse graph
# Nodes and edges
edges = []  # (src, dst)
i = 0
text = "\n".join(dep_lines)
# Normalize multi-line >> lists
# Use a state machine over dep_lines
buf = ""
stmts = []
for l in dep_lines:
    s = l.strip()
    if not s or s.startswith("#") or s.startswith("##"):
        continue
    buf += (" " if buf else "") + s
    if ">>" in buf and buf.count("[") == buf.count("]"):
        # complete if no open bracket or brackets balanced and ends reasonably
        if buf.count("[") == 0 or buf.rstrip().endswith("]"):
            stmts.append(buf)
            buf = ""
    elif ">>" in buf and buf.count("[") == buf.count("]") and not ("[" in buf):
        stmts.append(buf)
        buf = ""
if buf.strip():
    stmts.append(buf)

print("STMT_COUNT", len(stmts))
sensors = set()
bq_downstream_of = collections.defaultdict(set)
all_dst = set()
all_src = set()
for st in stmts:
    if ">>" not in st:
        continue
    left, right = st.split(">>", 1)
    left = left.strip()
    right = right.strip()
    # left can be start_task, wait_*, or [a,b]
    def parse_nodes(side):
        side = side.strip()
        if side.startswith("[") and side.endswith("]"):
            inner = side[1:-1]
            return [x.strip() for x in inner.split(",") if x.strip()]
        return [side]
    srcs = parse_nodes(left)
    dsts = parse_nodes(right)
    for s in srcs:
        for d in dsts:
            edges.append((s, d))
            all_src.add(s)
            all_dst.add(d)
            if s.startswith("wait_"):
                sensors.add(s)
                if not d.startswith("wait_") and d not in ("start_task", "start_new_task"):
                    bq_downstream_of[s].add(d)

print("EDGES", len(edges))
print("SENSORS_IN_EDGES", len(sensors))
empty_hang = []
for s in sorted(sensors):
    downs = bq_downstream_of.get(s, set())
    # also transitive one hop via other waits? for empty hang: no non-wait downstream
    if not downs:
        empty_hang.append(s)
        print("EMPTY_OR_ONLY_WAIT", s, "->", [d for a,d in edges if a==s])
    else:
        print(f"FANOUT {s}: {len(downs)}")

# Also check sensors that are created but only feed other waits
print("--- multi-hop empty check ---")
# BFS from each sensor to any BQ
from collections import deque
adj = collections.defaultdict(list)
for a,b in edges:
    adj[a].append(b)

def reaches_bq(start):
    seen=set(); q=deque([start])
    while q:
        n=q.popleft()
        if n in seen: continue
        seen.add(n)
        for nxt in adj[n]:
            if not nxt.startswith("wait_") and nxt not in ("start_task","start_new_task"):
                return True, nxt
            q.append(nxt)
    return False, None

created_sensors = []
for l in lines:
    m=re.match(r'(wait_\w+)\s*=\s*create_external_sensor', l.strip())
    if m and not l.strip().startswith('#'):
        created_sensors.append(m.group(1))

for s in created_sensors:
    ok, tip = reaches_bq(s)
    if not ok:
        print("NO_BQ_REACHABLE", s)
    # also check if sensor never appears as src
    if s not in all_src and s not in all_dst:
        print("NEVER_IN_GRAPH", s)

# start_new_task
print("start_new_task outs", adj.get("start_new_task"))
print("start_new_task ins", [a for a,b in edges if b=="start_new_task"])

# Count device_active related tasks that wait via sensor vs bare read
tasks_dir = root / "dags/qpon_tag_d/tasks"
# merchant dim patterns
merchant_files = list(tasks_dir.glob("Merchant_*.py")) + list(tasks_dir.glob("store_*.py")) + list(tasks_dir.glob("Store_*.py"))
print("MERCHANT_STORE_FILES", len(merchant_files))
for f in sorted(merchant_files)[:5]:
    t=f.read_text(encoding='utf-8')
    dims=re.findall(r'[\w.]*(?:dim_[\w]+|ods_[\w]+|dwd_[\w]+|dws_[\w]+)', t)
    has2999='2999' in t
    # partition filters near dim
    print(f.name, "2999=", has2999, "RETURN=", 'RETURN' in t)

# Sample Merchant_Sales and Merchant_Status and store_categoies
for name in ["Merchant_Sales_7.py","Merchant_Status.py","Merchant_product_count.py","store_categoies.py","Store_Hot.py","tag_qpon_base_merchantid_all_d.py","tag_qpon_qponid_userid_latest.py","DAY7_PRODUCT_LVL1_CATE_NAME.py"]:
    f=tasks_dir / name
    if not f.exists():
        # try recursive
        ms=list(tasks_dir.rglob(name))
        f=ms[0] if ms else None
    if not f: 
        print("MISSING", name); continue
    t=f.read_text(encoding='utf-8')
    print("====", name, "====")
    # extract from/join table refs
    refs=sorted(set(re.findall(r'`[^`]+`', t)))
    for r in refs:
        if any(x in r for x in ["dim_","ods_","dwd_","dws_","qpon_"]):
            print(" ", r)
    if "2999" in t:
        for i,l in enumerate(t.splitlines(),1):
            if "2999" in l:
                print(f"  L{i}: {l.strip()[:120]}")
    if "partition_date" in t and ("dim_" in t):
        for i,l in enumerate(t.splitlines(),1):
            if "dim_" in l or ("partition_date" in l and i>0):
                if "dim_" in l or (i>0 and "partition" in l and "dim" in t[max(0,t.find(l)-200):t.find(l)+50]):
                    pass
        # print lines with dim and nearby partition
        ls=t.splitlines()
        for i,l in enumerate(ls):
            if "dim_" in l:
                ctx=" | ".join(x.strip()[:80] for x in ls[max(0,i-2):i+3])
                print("  DIMCTX:", ctx[:200])

# voucher status filter variants among RETURN files
status_variants=collections.Counter()
for f in tasks_dir.rglob("*.py"):
    t=f.read_text(encoding='utf-8')
    if "dwd_product_order_voucher" not in t:
        continue
    for m in re.finditer(r"order_status\s+in\s*\(([^)]+)\)", t, re.I):
        status_variants[re.sub(r"\s+"," ",m.group(1))] += 1
    for m in re.finditer(r"order_status\s*=\s*'([^']+)'", t, re.I):
        status_variants[m.group(1)] += 1
print("VOUCHER_STATUS_VARIANTS", dict(status_variants))

# hour table bare reads
hour_reads=[]
for f in tasks_dir.rglob("*.py"):
    t=f.read_text(encoding='utf-8')
    hrs=re.findall(r'[\w.]+\w+_h\b', t)
    hrs=[h for h in hrs if any(x in h for x in ["ods_","dwd_","dws_","dim_","rpt_"])]
    if hrs:
        hour_reads.append((str(f.relative_to(tasks_dir)), sorted(set(hrs))))
print("HOUR_TABLE_READS", len(hour_reads))
for x in hour_reads:
    print(" ", x)

# Downstream of tag outside test - broader search
for f in (root/"dags").rglob("*.py"):
    rel=str(f.relative_to(root)).replace("\\","/")
    if "qpon_tag_d/" in rel:
        continue
    t=f.read_text(encoding='utf-8', errors='replace')
    if "qpon_tag_d" in t:
        # filter comments-only?
        hits=[(i,l.strip()) for i,l in enumerate(t.splitlines(),1) if "qpon_tag_d" in l]
        if hits:
            print("REF", rel, hits[:5])

# rpt_d device_active wait count for comparison
rpt = root/"dags/qpon_rpt_d/qpon_rpt_d.py"
if rpt.exists():
    rt=rpt.read_text(encoding='utf-8')
    print("RPT_device_active_sensor", rt.count("dws_qpon_device_active"))
    print("RPT_wait_device_active lines")
    for i,l in enumerate(rt.splitlines(),1):
        if "device_active" in l and not l.strip().startswith("#"):
            print(f"  L{i}: {l.strip()[:120]}")
