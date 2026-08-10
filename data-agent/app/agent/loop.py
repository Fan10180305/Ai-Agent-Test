"""Gemini tool-calling agent loop for data analysis."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.tools.bq import TOOL_DECLARATIONS, BigQueryTools, BqGuardError, dispatch_tool
from app.tools.catalog import DOMAIN_CATALOG

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""你是 Qpon 数仓数据分析助手，通过飞书与用户对话。

职责：
- 理解业务问题，自主探索表结构并查询 BigQuery
- 用中文给出清晰结论：数字、对比、可能原因、下一步建议
- 不确定时先查 schema / 小样本，再下结论；禁止编造表名或指标

约束：
- 只能使用提供的工具访问数据
- 严格遵守只读与 dataset 白名单
- 查询失败时解释原因并给出可执行的修正 SQL 思路
- 回复简洁，适合飞书阅读；关键数字加粗或分行展示
- 不要输出密钥、完整服务账号信息

{DOMAIN_CATALOG}
"""

MAX_TOOL_ROUNDS = 8


class DataAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=self.settings.gemini_api_key)
        self.bq = BigQueryTools(self.settings)
        self._tools = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(**decl) for decl in TOOL_DECLARATIONS
            ]
        )

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        contents: list[types.Content] = []
        for turn in history or []:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn.get("content", ""))],
                )
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=question)])
        )

        for round_idx in range(MAX_TOOL_ROUNDS):
            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[self._tools],
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content:
                return "模型未返回有效内容，请稍后重试。"

            parts = candidate.content.parts or []
            fn_calls = [p for p in parts if getattr(p, "function_call", None)]
            if not fn_calls:
                text = "".join(
                    getattr(p, "text", "") or "" for p in parts if getattr(p, "text", None)
                ).strip()
                return text or "（空回复）"

            # Append model turn with function calls
            contents.append(candidate.content)

            response_parts: list[types.Part] = []
            for part in fn_calls:
                fc = part.function_call
                name = fc.name
                args = dict(fc.args or {})
                log.info("tool_call round=%s name=%s args=%s", round_idx, name, args)
                try:
                    result = dispatch_tool(name, args, self.bq)
                    payload: Any = result
                except BqGuardError as e:
                    payload = {"error": "policy_violation", "message": str(e)}
                except Exception as e:  # noqa: BLE001 - surface tool errors to model
                    log.exception("tool failed: %s", name)
                    payload = {"error": "tool_error", "message": str(e)}

                response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response={"result": _jsonable(payload)},
                    )
                )
            contents.append(types.Content(role="user", parts=response_parts))

        return "分析轮次过多仍未收敛，请缩小问题范围后重试（例如指定日期与指标）。"


def _jsonable(obj: Any) -> Any:
    """Make BQ/tool results JSON-serializable for function responses."""
    try:
        return json.loads(json.dumps(obj, default=str))
    except TypeError:
        return str(obj)
