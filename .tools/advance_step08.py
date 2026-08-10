# -*- coding: utf-8 -*-
"""Mark a Step08 module done and prepare the next pending module prompt."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")
KB = ROOT / "qpon-bigdata-knowledge"
TMP = KB / ".tmp"
SUFFIXES = "abcdefghijklmnopqrstuvwxyz"


def main() -> int:
    done_id = sys.argv[1] if len(sys.argv) > 1 else ""
    write_bytes = sys.argv[2] if len(sys.argv) > 2 else ""
    write_sha = sys.argv[3] if len(sys.argv) > 3 else ""
    relay = sys.argv[4] if len(sys.argv) > 4 else ""

    manifest = json.loads((KB / "05_module_manifest.json").read_text(encoding="utf-8"))
    prog_path = TMP / "step08_progress.json"
    if prog_path.exists():
        prog = json.loads(prog_path.read_text(encoding="utf-8"))
    else:
        prog = {"done": [], "pending": [m["id"] for m in manifest]}

    if done_id and done_id not in prog["done"]:
        prog["done"].append(done_id)
    prog["pending"] = [m["id"] for m in manifest if m["id"] not in prog["done"]]
    prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")

    if done_id:
        (TMP / "last-success.txt").write_text(
            f"> [!SUCCESS] Step08 {done_id} done\n"
            f"> WRITE_BYTES: {write_bytes}\n"
            f"> WRITE_SHA256: {write_sha}\n"
            f"> RELAY: {relay}\n",
            encoding="utf-8",
            newline="\n",
        )

    print("done", prog["done"])
    print("pending", prog["pending"])
    if not prog["pending"]:
        print("ALL_STEP08_DONE")
        return 0

    # reuse prep_step08 logic via import-like call
    # write cores if missing
    if not (TMP / "module_cores.json").exists():
        subprocess.check_call([sys.executable, str(ROOT / ".tools/prep_step08.py")], cwd=str(ROOT))

    cores = json.loads((TMP / "module_cores.json").read_text(encoding="utf-8"))
    mid = prog["pending"][0]
    idx = next(i for i, m in enumerate(manifest) if m["id"] == mid)
    m = manifest[idx]
    suffix = SUFFIXES[idx]
    core = cores.get(mid, f"- 未找到 {mid}，请自行从 dags/ 与 05 推断")

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
RELAY_STRATEGY=Step08 {mid}: drill decision/failure modes; do not redo Step05; dags/ only; {relay[:200]}
"""
    (TMP / "pipeline-state.env").write_text(state, encoding="utf-8", newline="\n")

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
    shutil.copy(TMP / "next-prompt.md", KB / f"step-08-{mid}_prompt.md")
    out = f"08{suffix}_Module_{m['name']}.md"
    meta = {"id": mid, "name": m["name"], "suffix": suffix, "out": out, "core": core}
    (TMP / "current_module.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CURRENT_ID=" + mid)
    print("CURRENT_SUFFIX=" + suffix)
    print("CURRENT_NAME=" + m["name"])
    print("CURRENT_OUT=" + out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
