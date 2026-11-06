"""Хранение состояния уведомлений для дедупликации.

Чтобы не спамить чат на каждой проверке, бот запоминает, о каком игроке
(и с каким статусом) уже сообщал, а также по каким матчам уже объявлял
появление составов. Повторное уведомление об игроке уходит только если
его статус изменился.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Iterable


class State:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.notified: dict[str, str] = {}
        self.lineup_events: set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        self.notified = dict(data.get("notified", {}))
        self.lineup_events = set(data.get("lineup_events", []))

    def _save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "notified": self.notified,
                    "lineup_events": sorted(self.lineup_events),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(tmp, self.path)

    def get(self, key: str) -> str | None:
        return self.notified.get(key)

    def add_lineup_events(self, event_ids: Iterable[str]) -> None:
        with self._lock:
            self.lineup_events.update(event_ids)

    def replace_and_save(self, current: dict[str, str]) -> None:
        """Заменяет состояние текущим набором проблем и атомарно сохраняет."""
        with self._lock:
            self.notified = dict(current)
            self._save()
