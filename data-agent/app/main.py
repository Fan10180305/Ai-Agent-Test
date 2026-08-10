"""FastAPI entry: health + Feishu event webhook + optional HTTP ask."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.loop import DataAgent
from app.config import get_settings
from app.feishu.bot import FeishuClient
from app.feishu.crypto import FeishuEncryptor

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("data-agent")

app = FastAPI(title="Qpon Data Analysis Agent", version="0.1.0")

# Simple in-memory dedupe for Feishu retries (per instance)
_seen_events: set[str] = set()
_seen_lock = threading.Lock()
_MAX_SEEN = 2000


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AskResponse:
    """Direct HTTP ask — disabled unless ENABLE_HTTP_ASK=true."""
    settings = get_settings()
    if not settings.enable_http_ask:
        raise HTTPException(status_code=404, detail="not found")
    if settings.ask_api_key and x_api_key != settings.ask_api_key:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        answer = DataAgent(settings).ask(body.question)
    except Exception:  # noqa: BLE001
        log.exception("ask failed")
        raise HTTPException(status_code=500, detail="analysis failed") from None
    return AskResponse(answer=answer)


@app.post("/feishu/event")
async def feishu_event(request: Request) -> dict[str, Any]:
    settings = get_settings()
    if not settings.feishu_verification_token:
        raise HTTPException(
            status_code=503,
            detail="FEISHU_VERIFICATION_TOKEN not configured",
        )

    raw = await request.json()

    # Encrypted payload unwrap
    if "encrypt" in raw:
        if not settings.feishu_encrypt_key:
            raise HTTPException(status_code=503, detail="encrypt key missing")
        encryptor = FeishuEncryptor(settings.feishu_encrypt_key)
        raw = encryptor.decrypt_json(raw["encrypt"])

    # URL verification challenge
    if raw.get("type") == "url_verification":
        token = raw.get("token", "")
        if token != settings.feishu_verification_token:
            raise HTTPException(status_code=403, detail="invalid verification token")
        return {"challenge": raw.get("challenge")}

    header = raw.get("header") or {}
    event_id = header.get("event_id") or raw.get("uuid") or ""
    token = header.get("token") or raw.get("token") or ""
    if token != settings.feishu_verification_token:
        raise HTTPException(status_code=403, detail="invalid token")

    if event_id and _already_seen(event_id):
        return {"code": 0}

    event_type = header.get("event_type") or raw.get("event", {}).get("type")
    event = raw.get("event") or {}

    if event_type == "im.message.receive_v1":
        # Detached thread: Feishu needs <3s ACK; requires Cloud Run --no-cpu-throttling
        threading.Thread(
            target=_handle_im_message,
            args=(event,),
            daemon=True,
            name="feishu-im-handler",
        ).start()
    else:
        log.info("ignore event_type=%s", event_type)

    return {"code": 0}


def _already_seen(event_id: str) -> bool:
    with _seen_lock:
        if event_id in _seen_events:
            return True
        _seen_events.add(event_id)
        if len(_seen_events) > _MAX_SEEN:
            for _ in range(_MAX_SEEN // 2):
                _seen_events.pop()
        return False


def _handle_im_message(event: dict[str, Any]) -> None:
    settings = get_settings()
    message = event.get("message") or {}
    sender = event.get("sender") or {}
    sender_id = (sender.get("sender_id") or {}).get("open_id", "")

    if settings.allowlist_open_ids and sender_id not in settings.allowlist_open_ids:
        log.warning("reject open_id not in allowlist: %s", sender_id)
        return

    msg_type = message.get("message_type")
    message_id = message.get("message_id")
    if not message_id:
        return

    chat_type = message.get("chat_type")
    mentions = message.get("mentions") or []
    if chat_type == "group" and not mentions:
        return

    if msg_type != "text":
        FeishuClient(settings).reply_text(
            message_id, "目前仅支持文本问题，请直接描述你要看的数据。"
        )
        return

    try:
        content = json.loads(message.get("content") or "{}")
        text = (content.get("text") or "").strip()
    except json.JSONDecodeError:
        text = (message.get("content") or "").strip()

    text = _strip_mentions(text)
    if not text:
        return

    client = FeishuClient(settings)
    try:
        client.reply_text(message_id, "收到，正在查数分析…")
        answer = DataAgent(settings).ask(text)
        client.reply_text(message_id, answer)
    except Exception as e:  # noqa: BLE001
        log.exception("handle message failed")
        try:
            client.reply_text(message_id, f"分析失败，请稍后重试（{type(e).__name__}）")
        except Exception:  # noqa: BLE001
            log.exception("failed to send error reply")


def _strip_mentions(text: str) -> str:
    parts = text.split()
    cleaned = [p for p in parts if not p.startswith("@_user_")]
    return " ".join(cleaned).strip()
