# -*- coding: utf-8 -*-
"""Prepare Step 08 module deep-dive: list modules, extract core anchors, render first prompt."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")
KB = ROOT / "qpon-bigdata-knowledge"
TMP = KB / ".tmp"
SUFFIXES = "abcdefghijklmnopqrstuvwxyz"


def main() -> int:
    p07 = KB / "07_Config_and_Observability.md"
    b = p07.read_bytes()
    print("07", len(b), hashlib.sha256(b).hexdigest())

    manifest = json.loads((KB / "05_module_manifest.json").read_text(encoding="utf-8"))
    orch = (KB / "05_Business_Orchestration.md").read_text(encoding="utf-8")

    # crude core-class extraction: collect backtick paths/names near each module id/name
    cores: dict[str, str] = {}
    for m in manifest:
        mid, mname = m["id"], m["name"]
        hits = []
        for line in orch.splitlines():
            if mid in line or mname in line or mid.replace("-", "_") in line:
                for tok in re.findall(r"`([^`]+)`", line):
                    if any(x in tok for x in (".py", "/", "create_", "qpon_", "DAG", "Sensor")):
                        if tok not in hits:
                            hits.append(tok)
        if not hits:
            # fallback mapping by id
            fallback = {
                "airflow-config": ["dags/airflow_config/*.py", "create_composer_bq_task", "create_external_sensor", "airflow_tt_send", "cloud_run_write_aliyun_es"],
                "ods-d": ["dags/qpon_ods_d/qpon_ods_d.py", "dags/qpon_ods_d/tasks/**"],
                "ods-h": ["dags/qpon_ods_h/qpon_ods_h.py", "dags/qpon_ods_h/tasks/**"],
                "dim-d": ["dags/qpon_dim_d/qpon_dim_d.py", "dags/qpon_dim_h/qpon_dim_h.py"],
                "dwd-d": ["dags/qpon_dwd_d/qpon_dwd_d.py", "dags/qpon_dwd_d/tasks/dwd_product_order_voucher_all.py"],
                "dwd-h": ["dags/qpon_dwd_h/qpon_dwd_h.py"],
                "dws-d": ["dags/qpon_dws_d/qpon_dws_d.py", "dags/qpon_dws_h/qpon_dws_h.py"],
                "rpt-d": ["dags/qpon_rpt_d/qpon_rpt_d.py", "dags/qpon_rpt_d/tasks/**"],
                "rpt-h": ["dags/qpon_rpt_h/qpon_rpt_h.py"],
                "tag-d": ["dags/qpon_tag_d/qpon_tag_d.py", "dags/qpon_tag_d/tasks/**"],
                "analyst-serving": ["dags/qpon_analyst_d/", "dags/qpon_risk_d/", "dags/qpon_daily_report/", "dags/qpon_data_server_d/"],
                "metadata": ["dags/qpon_metadata/", "gcp_monitoring_alert.py", "utils/variables.py"],
                "ops-staging": ["dags/data_options/", "dags/qpon_staging_d/", "dags/task_kill/"],
                "test-dags": ["dags/qpon_*_test/", "dags/qpon_test_d/", "dags/qpon_review_score_test/"],
            }.get(mid, [f"未在 05 中找到模块 {mid} 的核心类描述，请执行 Agent 自行从 OUTPUT_DIR 与 dags/ 推断"])
            hits = fallback
        cores[mid] = "\n".join(f"- `{h}`" for h in hits[:20])

    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "module_cores.json").write_text(json.dumps(cores, ensure_ascii=False, indent=2), encoding="utf-8")

    # progress tracker
    progress = {"done": [], "pending": [m["id"] for m in manifest]}
    prog_path = TMP / "step08_progress.json"
    if prog_path.exists():
        old = json.loads(prog_path.read_text(encoding="utf-8"))
        done = set(old.get("done", []))
        progress["done"] = [m["id"] for m in manifest if m["id"] in done]
        progress["pending"] = [m["id"] for m in manifest if m["id"] not in done]
    else:
        prog_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")

    print("pending", progress["pending"])
    if not progress["pending"]:
        print("ALL_STEP08_DONE")
        return 0

    # render first pending module
    mid = progress["pending"][0]
    idx = next(i for i, m in enumerate(manifest) if m["id"] == mid)
    m = manifest[idx]
    suffix = SUFFIXES[idx]
    core = cores[mid]

    state = f"""PROJECT_NAME=qpon-bigdata
PROJECT_DISPLAY=qpon-bigdata
OUTPUT_DIR=qpon-bigdata-knowledge
LEGACY_DOCS_DIR=old-readme/
PROMPT_DIR=.gemini/skills/archaeology-commander/resources/prompts
TIMESTAMP=2026-07-30_141302
LOG_DIR=qpon-bigdata-knowledge/.logs/2026-07-30_141302
ACTUAL_MODULE_PREFIX=NON_JAVA
SKIP_STEP0=true
EVOLUTION_MODE=false
RUN_BASE=FULL_REBUILD
LEGACY_MODE=NO_DOCS
SCAN_ROOT=dags
EXECUTOR=cursor-task
RELAY_STRATEGY=Step08 module deep-dive for {mid}: drill decision points/failure modes; do not redo Step05 call chains; dags/ only; prioritize Composer slots, gcp_monitoring_alert pause, hardcoded TT tokens, ES credential logs
"""
    (TMP / "pipeline-state.env").write_text(state, encoding="utf-8", newline="\n")
    (TMP / "last-success.txt").write_text(
        "> [!SUCCESS] Step07 done\n> WRITE_TARGET: qpon-bigdata-knowledge/07_Config_and_Observability.md\n> WRITE_BYTES: 23901\n> WRITE_SHA256: f3e6d470911c16f979dae055e4612144c03fd64800cfeb9d54649cbdf510cd8a\n",
        encoding="utf-8",
        newline="\n",
    )

    cmd = [
        sys.executable,
        str(ROOT / ".tools/render_prompt.py"),
        "--state",
        str(TMP / "pipeline-state.env"),
        "--template",
        str(ROOT / ".gemini/skills/archaeology-commander/resources/prompts/step-08-module-template.md"),
        "--out",
        str(TMP / "next-prompt.md"),
        "--prior-file",
        str(TMP / "last-success.txt"),
        "--module-name",
        m["name"],
        "--module-suffix",
        suffix,
        "--module-core-classes",
        core,
    ]
    print(subprocess.check_output(cmd, cwd=str(ROOT), text=True))
    out_name = f"08{suffix}_Module_{m['name']}.md"
    # archive prompt
    import shutil

    shutil.copy(TMP / "next-prompt.md", KB / f"step-08-{mid}_prompt.md")
    meta = {"id": mid, "name": m["name"], "suffix": suffix, "out": out_name, "core": core}
    (TMP / "current_module.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CURRENT", json.dumps({"id": mid, "suffix": suffix, "out": out_name}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
