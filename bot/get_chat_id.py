"""Утилита для получения chat_id Telegram-чата.

Запуск:  python -m bot.get_chat_id

Перед запуском добавьте бота в нужный чат (группу) и отправьте туда любое
сообщение, либо напишите боту в личку — тогда getUpdates вернёт этот чат.
"""
from __future__ import annotations

import sys

import requests

from .config import load_config


def main() -> int:
    cfg = load_config()
    if not cfg.telegram_bot_token:
        print("Не задан TELEGRAM_BOT_TOKEN. Заполните .env (см. README).")
        return 1

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/getUpdates"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        print(f"Ошибка Telegram API: {data}")
        return 1

    chats: dict[int, str] = {}
    for update in data.get("result", []):
        message = (
            update.get("message")
            or update.get("channel_post")
            or update.get("my_chat_member", {})
        )
        chat = message.get("chat") if message else None
        if chat:
            title = (
                chat.get("title")
                or chat.get("username")
                or chat.get("first_name")
                or chat.get("last_name")
                or ""
            )
            chats[chat["id"]] = title

    if not chats:
        print(
            "Чатов не найдено. Отправьте боту любое сообщение (или добавьте "
            "его в группу и напишите там) и запустите команду ещё раз."
        )
        return 1

    print("Найденные чаты (скопируйте нужный id в mapping.json):")
    for chat_id, title in chats.items():
        print(f"  {chat_id}  {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
