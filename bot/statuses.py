"""Детекция игроков основного состава, которые не выйдут со старта.

Fantrax отдаёт у каждого игрока список ``icons`` (иконок статуса), где
``typeId`` кодирует состояние относительно ближайшего/текущего матча:

* ``30`` — «Out for next game» (травма/выбыл) — точно не сыграет;
* ``6``  — «Suspended» (дисквалификация) — точно не сыграет;
* ``1``  — «Late fitness test (Game-time decision)» — под вопросом;
* ``32`` — «Expected to play» — ожидается в старте (здоров).

Состав разбит на слоты: ``statusId == "1"`` — основной (Active),
``"2"`` — скамейка (Reserve), ``"3"`` — лазарет (Injured Reserve).
Нас интересуют только игроки в основном составе (``statusId == "1"``).
"""
from __future__ import annotations

from dataclasses import dataclass

ACTIVE_SLOT_STATUS = "1"

# (typeId иконки, код, эмодзи, подпись). Порядок задаёт приоритет:
# первый совпавший статус считается самым важным для игрока.
STATUS_RULES: list[tuple[str, str, str, str]] = [
    ("30", "OUT", "🔴", "не сыграет (Out)"),
    ("6", "SUSPENDED", "🔴", "дисквалификация"),
    ("1", "DOUBTFUL", "🟡", "под вопросом (game-time decision)"),
]


@dataclass
class PlayerIssue:
    team_id: str
    team_name: str
    player_id: str
    player_name: str
    position: str
    club: str
    severity: str
    emoji: str
    label: str
    reason: str

    def key(self) -> str:
        """Уникальный ключ игрока в составе команды для дедупликации."""
        return f"{self.team_id}:{self.player_id}"

    def line(self) -> str:
        base = (
            f"{self.emoji} {self.player_name} "
            f"({self.position}, {self.club}) — {self.label}"
        )
        if self.reason and self.reason.lower() != "suspended":
            return f"{base}: {self.reason}"
        return base


def detect_issues(
    team_id: str, team_name: str, roster_response: dict
) -> list[PlayerIssue]:
    """Возвращает проблемы (не выйдет со старта) для активного состава команды."""
    issues: list[PlayerIssue] = []
    for table in roster_response.get("tables", []):
        for row in table.get("rows", []):
            if row.get("statusId") != ACTIVE_SLOT_STATUS:
                continue
            scorer = row.get("scorer")
            if not scorer:
                continue

            icons = scorer.get("icons") or []
            for type_id, severity, emoji, label in STATUS_RULES:
                icon = next(
                    (i for i in icons if str(i.get("typeId")) == type_id),
                    None,
                )
                if icon is not None:
                    issues.append(
                        PlayerIssue(
                            team_id=team_id,
                            team_name=team_name,
                            player_id=str(scorer.get("scorerId", "")),
                            player_name=scorer.get("name", "?"),
                            position=scorer.get("posShortNames", "?"),
                            club=scorer.get("teamName", "?"),
                            severity=severity,
                            emoji=emoji,
                            label=label,
                            reason=icon.get("tooltip") or "",
                        )
                    )
                    break  # берём самый приоритетный статус игрока

    return issues
