from pathlib import Path
import json
import hashlib

root = Path("qpon-bigdata-knowledge")
for n in [
    "05_Business_Orchestration.md",
    "05_module_manifest.json",
    "06_Async_Jobs_and_Compensation.md",
    "07_Config_and_Observability.md",
    "00_Master_Catalog.md",
]:
    p = root / n
    if p.exists():
        b = p.read_bytes()
        print(f"OK {n} bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}")
    else:
        print(f"MISSING {n}")

mp = root / "05_module_manifest.json"
if mp.exists():
    data = json.loads(mp.read_text(encoding="utf-8"))
    print(f"manifest_modules={len(data)}")
