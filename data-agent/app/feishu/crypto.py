"""Feishu encrypt/decrypt helpers for event subscription."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class FeishuEncryptor:
    """AES-256-CBC decrypt for Feishu Encrypt Key payloads."""

    def __init__(self, encrypt_key: str) -> None:
        # Feishu derives key = SHA256(encrypt_key)
        self._key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()

    def decrypt(self, encrypt: str) -> str:
        raw = base64.b64decode(encrypt)
        iv, ciphertext = raw[:16], raw[16:]
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        pad_len = padded[-1]
        return padded[:-pad_len].decode("utf-8")

    def decrypt_json(self, encrypt: str) -> dict[str, Any]:
        return json.loads(self.decrypt(encrypt))
