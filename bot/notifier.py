"""Отправка сообщений в Telegram через Bot API."""
from __future__ import annotations

import logging
from typing import Any

import requests

log = logging.getLogger("fantrax_bot")


def send_telegram(token: str, chat_id: str, text: str) -> dict[str, Any]:
    """Отправляет сообщение в чат и возвращает ответ Telegram API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API вернул ошибку: {data}")
    return data
