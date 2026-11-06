"""Кто нажал «Старт» у бота: привязка участника и уведомление администратора.

Telegram отдаёт chat_id только тем, кто уже писал боту, поэтому «Старт» —
единственный момент, когда нового участника можно привязать к команде.
Входящие сообщения вычитываются в каждом цикле проверки, а обработанные
апдейты подтверждаются offset-ом и повторно не приходят.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Iterable

import requests

from .config import Config
from .fantrax import FantraxClient
from .link import load_participants, resolve_team
from .mapping import load_mapping
from .notifier import send_telegram

log = logging.getLogger("fantrax_bot")

# None — процесс только запустился: забираем всё непрочитанное (до 100
# апдейтов за последние сутки), дальше ходим по offset-у.
_offset: int | None = None


def fetch_updates(token: str, offset: int | None) -> tuple[list[dict], int | None]:
    """Возвращает (апдейты, новый offset); предыдущая пачка этим подтверждается."""
    params: dict[str, Any] = {
        "limit": 100,
        "timeout": 0,
        "allowed_updates": json.dumps(["message"]),
    }
    if offset is not None:
        params["offset"] = offset

    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params=params,
        timeout=30,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API вернул ошибку: {data}")

    updates = data.get("result", [])
    if not updates:
        return [], offset
    return updates, max(int(u["update_id"]) for u in updates) + 1


def message_chats(updates: list[dict]) -> list[dict]:
    chats = []
    for update in updates:
        chat = (update.get("message") or {}).get("chat") or {}
        if chat.get("id") is not None:
            chats.append(chat)
    return chats


def apply_chats(
    chats: Iterable[dict],
    mapping: dict[str, Any],
    participants: dict[str, str],
    teams: dict[str, str],
) -> tuple[list[str], bool]:
    """Привязывает chat_id к командам по @username из participants.json.

    Возвращает (сообщения администратору, были ли изменения в привязке).
    """
    by_username = {
        str(user).strip().lstrip("@").lower(): team
        for team, user in participants.items()
    }
    messages: list[str] = []
    changed = False

    for chat in chats:
        chat_id = str(chat["id"])
        username = str(chat.get("username") or "").strip().lstrip("@")
        who = f"@{username}" if username else f"{chat_id} (без @username)"

        team_key = by_username.get(username.lower()) if username else None
        if team_key is None:
            messages.append(
                f"{who} нажал «Старт», но его нет в participants.json "
                f"(chat_id {chat_id})"
            )
            continue

        resolved = resolve_team(team_key, teams)
        if resolved is None:
            messages.append(
                f"{who} нажал «Старт», но команда «{team_key}» не найдена в лиге "
                f"(chat_id {chat_id})"
            )
            continue

        team_id, team_name = resolved
        current = mapping.get(team_name, mapping.get(team_id))
        if current is not None and str(current) == chat_id:
            continue  # уже привязан, повторно не сообщаем

        mapping[team_name] = chat_id
        changed = True
        messages.append(
            f"{who} нажал «Старт» — привязан к команде «{team_name}» "
            f"(chat_id {chat_id})"
        )

    return messages, changed


def _load_participants(path: str) -> dict[str, str]:
    try:
        return load_participants(path)
    except SystemExit as exc:  # load_participants завершает процесс, если файла нет
        log.warning("Привязка новых участников недоступна: %s", exc)
        return {}


def handle_starts(cfg: Config, client: FantraxClient) -> None:
    """Привязывает новых участников и сообщает о них администратору."""
    global _offset

    if not cfg.telegram_bot_token:
        return

    updates, _offset = fetch_updates(cfg.telegram_bot_token, _offset)
    chats = message_chats(updates)
    if not chats:
        return

    mapping = load_mapping(cfg.mapping_file)
    messages, changed = apply_chats(
        chats,
        mapping,
        _load_participants(cfg.participants_file),
        client.teams(),
    )

    if changed:
        with open(cfg.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
            f.write("\n")
        log.info("Привязка обновлена: %s", cfg.mapping_file)

    for text in messages:
        log.info("%s", text)
        if not cfg.admin_chat_id:
            continue
        try:
            send_telegram(cfg.telegram_bot_token, cfg.admin_chat_id, text)
        except Exception as exc:
            # Сбой уведомления не должен ломать цикл проверки.
            log.error("Не удалось уведомить администратора: %s", exc)
