"""Хранение состояния уведомлений для дедупликации.

Чтобы не спамить чат на каждой проверке, бот запоминает, о каком игроке
(и с каким статусом) уже сообщал. Повторное уведомление уходит только
если статус игрока изменился (например, «под вопросом» -> «не сыграет»).
"""
from __future__ import annotations

import json
import os
import threading


class State:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.notified: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return dict(data.get("notified", {}))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def get(self, key: str) -> str | None:
        return self.notified.get(key)

    def replace_and_save(self, current: dict[str, str]) -> None:
        """Заменяет состояние текущим набором проблем и атомарно сохраняет."""
        with self._lock:
            self.notified = dict(current)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {"notified": self.notified},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            os.replace(tmp, self.path)
