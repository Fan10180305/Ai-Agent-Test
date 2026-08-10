"""Feishu Open API client (token + message reply)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._token: str | None = None
        self._expire_at: float = 0

    def get_tenant_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._expire_at - 60:
            return self._token
        if not self.settings.feishu_app_id or not self.settings.feishu_app_secret:
            raise RuntimeError("FEISHU_APP_ID / FEISHU_APP_SECRET required")
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{BASE}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.settings.feishu_app_id,
                    "app_secret": self.settings.feishu_app_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"feishu token error: {data}")
        self._token = data["tenant_access_token"]
        self._expire_at = now + int(data.get("expire", 7200))
        return self._token

    def reply_text(self, message_id: str, text: str) -> dict[str, Any]:
        token = self.get_tenant_access_token()
        content = {"text": text[:4000]}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{BASE}/im/v1/messages/{message_id}/reply",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "msg_type": "text",
                    "content": json.dumps(content, ensure_ascii=False),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != 0:
            log.error("feishu reply failed: %s", data)
        return data

    def send_text(
        self, receive_id: str, text: str, receive_id_type: str = "chat_id"
    ) -> dict[str, Any]:
        token = self.get_tenant_access_token()
        content = {"text": text[:4000]}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{BASE}/im/v1/messages",
                params={"receive_id_type": receive_id_type},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": receive_id,
                    "msg_type": "text",
                    "content": json.dumps(content, ensure_ascii=False),
                },
            )
            resp.raise_for_status()
            return resp.json()
