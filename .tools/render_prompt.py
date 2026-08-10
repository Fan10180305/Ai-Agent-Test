#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render archaeology step prompt from template + pipeline state."""
from __future__ import annotations

import argparse
import pathlib
import re
import sys


NON_JAVA_HEADER = """
【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Airflow DAG、Python 算子、SQL/BigQuery、配置文件、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 `<project>-xxx/` 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在而触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

【扫描边界硬约束】本次知识库的代码事实权威范围严格限定为工作区内的 `dags/` 目录（含子目录）。
禁止以仓库其他目录（如 scripts/、ai-knowledge-knowledge/）作为业务事实来源；仅可读取协作协议与产出目录。
""".strip()

NON_JAVA_STEP01_EXTRA = """
此外，作为全链路第一个接触项目源码的步骤，你的 [!RELAY] 必须额外包含：
- 本项目的实际技术栈清单（框架、包管理器、构建工具、测试框架）
- 项目的物理目录结构与各目录职责推断（聚焦 dags/）
- 对后续步骤（契约提取、数据模型、异步机制等）的具体扫描路径建议
这些信息将被指挥官用于后续步骤的接力注入，直接影响后续步骤的分析方向。
""".strip()

STDOUT_TAIL = """
**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: <本步目标知识文件相对路径>
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

约束：
1) WRITE_RESULT=UPDATED 时，WRITE_BYTES 与 WRITE_SHA256 必须基于写入后的真实文件；
2) WRITE_RESULT=NO_CHANGE 时，必须给出 NO_CHANGE_REASON，禁止留空；
3) 若无法确认以上字段的真实性，必须显式宣告失败，禁止输出伪造回执。
""".strip()


def load_state(path: pathlib.Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        state[k] = v
    return state


def inject_after_role(text: str, block: str) -> str:
    # Insert after first "## 角色定义" section (after its first blank-line-separated paragraph block)
    m = re.search(r"(## 角色定义\n.*?\n\n)", text, flags=re.S)
    if not m:
        return block + "\n\n" + text
    idx = m.end()
    return text[:idx] + block + "\n\n" + text[idx:]


def inject_priority_blocks(text: str, relay: str, rules: str) -> str:
    # Insert before "## 先验知识注入"
    block = (
        "# 0. 核心接力策略（最高执行优先级）\n\n"
        f"{relay}\n\n"
        "**[执行准则]**: 以上为上一步指挥官转交的\"强制任务\"。你必须优先响应并回显证据，否则将被判定为考古失败。\n\n"
        "# 0.5 项目军规（项目级行为约束）\n\n"
        f"{rules}\n\n"
        "**[执行准则]**: 项目军规对本步分析与写回具有高优先级约束，不得被普通先验信息覆盖。\n\n"
    )
    marker = "## 先验知识注入"
    if marker in text:
        return text.replace(marker, block + marker, 1)
    return block + text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prior-summary", default="")
    ap.add_argument("--prior-file", default="")
    ap.add_argument("--module-name", default="")
    ap.add_argument("--module-suffix", default="")
    ap.add_argument("--module-core-classes", default="")
    args = ap.parse_args()

    state = load_state(pathlib.Path(args.state))
    template = pathlib.Path(args.template).read_text(encoding="utf-8")

    project = state["PROJECT_NAME"]
    display = state.get("PROJECT_DISPLAY", project)
    output_dir = state["OUTPUT_DIR"].rstrip("/") + "/"
    legacy_dir = state.get("LEGACY_DOCS_DIR", "old-readme/")
    relay = state.get("RELAY_STRATEGY", "无先验接力偏好，请按标准考古规范执行。")

    if args.prior_file:
        prior_raw = pathlib.Path(args.prior_file).read_text(encoding="utf-8")
    else:
        prior_raw = args.prior_summary
    prior = prior_raw.strip() or "无先验知识（Step 0 为 NO_DOCS，或首步）。"

    rules_path = pathlib.Path(".cursor/rules/ai-knowledge.mdc")
    if not rules_path.exists():
        rules_path = pathlib.Path(".gemini/rules/ai-knowledge.md")
    if rules_path.exists():
        rules = (
            "意图路由：先读知识库入口再改代码；Skill 优先调度流水线。\n"
            "强制红线：禁止 macOS 专有 sed；路径锚定；Shell set -euo pipefail。\n"
            "双写要求：改调度逻辑须同步更新知识库。\n"
            "本轮相关约束：扫描权威范围为 dags/；产出写入 "
            f"{output_dir}；NON_JAVA 语义映射。"
        )
    else:
        rules = "无项目级军规文件，继续按通用协议执行"

    text = template
    replacements = {
        "{{project_name}}": project,
        "{{project_display_name}}": display,
        "{{output_dir}}": output_dir,
        "{{legacy_docs_dir}}": legacy_dir,
        "{{evolution_mode_context}}": "",
        "{{RELAY_STRATEGY}}": relay,
        "{{PROJECT_RULE_CONTEXT}}": rules,
        "{{module_name}}": args.module_name,
        "{{module_suffix}}": args.module_suffix,
        "{{module_core_classes}}": args.module_core_classes,
        # step-specific prior placeholders used by some templates
        "{{step02_prior_findings}}": prior,
        "{{step03_prior_findings}}": prior,
        "{{step04_prior_findings}}": prior,
        "{{step05_prior_findings}}": prior,
        "{{step06_prior_findings}}": prior,
        "{{step07_prior_findings}}": prior,
        "{{prior_findings}}": prior,
        "{{LAST_SUMMARY}}": prior,
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Fix legacy claims path references left in templates
    text = text.replace(
        f"{output_dir}Legacy_SignInCenter_Claims.md",
        f"{output_dir}Legacy_{project}_Claims.md",
    )
    text = text.replace(
        "Legacy_SignInCenter_Claims.md",
        f"Legacy_{project}_Claims.md",
    )

    if state.get("ACTUAL_MODULE_PREFIX") == "NON_JAVA":
        nj = NON_JAVA_HEADER
        step_name = pathlib.Path(args.template).name
        if "step-01" in step_name:
            nj = nj + "\n\n" + NON_JAVA_STEP01_EXTRA
        text = inject_after_role(text, nj)

    # Prior knowledge injection note
    text = inject_priority_blocks(text, relay, rules)
    text = text.replace(
        "## 先验知识注入\n",
        "## 先验知识注入\n\n"
        f"### 前序步骤 [!SUCCESS] 摘要\n```\n{prior}\n```\n\n",
        1,
    )

    text = text.rstrip() + "\n\n" + STDOUT_TAIL + "\n"

    # Re-apply replacements after injections (injected blocks may contain placeholders)
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Fail if unresolved placeholders remain (except N/A style braces in prose)
    leftover = re.findall(r"\{\{[a-zA-Z0-9_\-]+\}\}", text)
    if leftover:
        print("UNRESOLVED_PLACEHOLDERS:" + ",".join(sorted(set(leftover))), file=sys.stderr)
        return 2

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"RENDERED={out} BYTES={out.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
