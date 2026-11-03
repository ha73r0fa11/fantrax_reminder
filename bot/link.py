"""Собирает chat_id участников и генерирует mapping.json.

Источник списка участников — participants.json (команда -> @username):

    {
      "Fq": "@Viktor_Ev_St",
      "butep": "@alndrmn"
    }

Telegram отдаёт chat_id только для тех, кто уже писал боту, поэтому каждый
участник должен сначала нажать «Старт» (@<бот>), а затем запустить:

    python -m bot.link

Скрипт создаст mapping.json (команда -> chat_id) и перечислит тех, кого
ещё не удалось связать.
"""
from __future__ import annotations

import json
import sys

import requests

from .config import load_config
from .fantrax import FantraxClient
from .mapping import load_mapping


def fetch_usernames(token: str) -> dict[str, str]:
    """Возвращает {username_lower: chat_id} по накопленным обновлениям бота."""
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"limit": 100, "allowed_updates": json.dumps(["message"])},
        timeout=30,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API вернул ошибку: {data}")

    found: dict[str, str] = {}
    for update in data.get("result", []):
        chat = (update.get("message") or {}).get("chat") or {}
        username = chat.get("username")
        if username:
            found[username.strip().lstrip("@").lower()] = str(chat["id"])
    return found


def load_participants(path: str) -> dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit(
            f"Не найден {path}. Создайте его по образцу participants.example.json"
        )
    if not isinstance(data, dict):
        raise SystemExit(f"{path} должен быть JSON-объектом {{команда: @username}}")
    return data


def resolve_team(team_key: str, teams: dict[str, str]) -> tuple[str, str] | None:
    """Находит команду по ID, точному имени или его началу.

    Возвращает (team_id, каноническое имя) или None, если команда
    не найдена либо подходящих несколько.
    """
    key = str(team_key).strip()
    if key in teams:
        return key, teams[key]

    lowered = key.lower()
    exact = [
        (tid, name) for tid, name in teams.items()
        if name.strip().lower() == lowered
    ]
    if exact:
        return exact[0]

    partial = [
        (tid, name) for tid, name in teams.items()
        if name.strip().lower().startswith(lowered)
    ]
    return partial[0] if len(partial) == 1 else None


def main() -> int:
    cfg = load_config()
    if not cfg.telegram_bot_token:
        print("Не задан TELEGRAM_BOT_TOKEN (см. .env).")
        return 1

    participants = load_participants(cfg.participants_file)
    usernames = fetch_usernames(cfg.telegram_bot_token)

    teams = FantraxClient(cfg.league_id).teams()

    mapping: dict[str, str] = {}
    unresolved_user: list[str] = []
    unknown_team: list[str] = []

    for team_key, username in participants.items():
        clean = str(username).strip().lstrip("@").lower()
        chat_id = usernames.get(clean)
        if chat_id is None:
            unresolved_user.append(f"{team_key} -> @{clean}")
            continue

        resolved = resolve_team(team_key, teams)
        if resolved is None:
            unknown_team.append(str(team_key))
            continue

        mapping[resolved[1]] = chat_id

    with open(cfg.mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Записано в {cfg.mapping_file}: {len(mapping)} команд")
    for name, chat_id in sorted(mapping.items()):
        print(f"  {name} -> {chat_id}")

    if unresolved_user:
        print("\nЕщё не нажали «Старт» у бота (chat_id неизвестен):")
        for item in unresolved_user:
            print(f"  {item}")

    if unknown_team:
        print("\nНе найдены в лиге (проверьте название команды):")
        for item in unknown_team:
            print(f"  {item}")

    return 0 if not (unresolved_user or unknown_team) else 2


if __name__ == "__main__":
    sys.exit(main())
