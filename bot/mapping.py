"""Ручная таблица привязки «команда Fantrax -> Telegram chat_id».

Формат mapping.json — JSON-объект, где ключ это либо название команды
(без учёта регистра), либо её ID, а значение — chat_id пользователя:

    {
      "Fq": 123456789,
      "butep": 987654321,
      "Sognare ✨": -100222333444
    }

Узнать chat_id участников: python -m bot.get_chat_id
Посмотреть команды и текущую привязку: python -m bot.mapping
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from .config import load_config
from .fantrax import FantraxClient

log = logging.getLogger("fantrax_bot")


def load_mapping(path: str) -> dict[str, Any]:
    """Читает mapping-файл. Возвращает {ключ: chat_id}."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("Файл привязки %s не найден — уведомлять будет некого.", path)
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Невалидный JSON в файле привязки {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Файл привязки {path} должен быть JSON-объектом "
            "{«команда или id»: chat_id}"
        )
    return data


def resolve_chat_ids(
    mapping: dict[str, Any], teams: dict[str, str]
) -> dict[str, str]:
    """Сопоставляет команды лиги с chat_id.

    teams: {team_id: team_name}. Возвращает {team_id: chat_id} для тех команд,
    которые есть в привязке. Ключ привязки может быть как названием команды
    (без учёта регистра), так и её ID.
    """
    by_name = {str(key).strip().lower(): value for key, value in mapping.items()}
    result: dict[str, str] = {}
    for team_id, team_name in teams.items():
        chat_id = mapping.get(team_id)
        if chat_id is None:
            chat_id = by_name.get(team_name.strip().lower())
        if chat_id is not None:
            result[team_id] = str(chat_id)
    return result


def main() -> int:
    """Печатает команды лиги и их привязку — помощь при заполнении mapping.json."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    cfg = load_config()
    client = FantraxClient(cfg.league_id)
    teams = client.teams()
    mapping = load_mapping(cfg.mapping_file)
    chat_ids = resolve_chat_ids(mapping, teams)

    print(f"Команды лиги (привязка из {cfg.mapping_file}):")
    for team_id, team_name in sorted(teams.items(), key=lambda kv: kv[1].lower()):
        chat_id = chat_ids.get(team_id)
        status = f"-> {chat_id}" if chat_id else "(не привязана)"
        print(f"  {team_name}  [id={team_id}]  {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
