"""Детекция игроков основного состава, которых нет в стартовом составе.

Ловим только статусы состава: они появляются примерно за час до матча и
исчезают после него. Статусы доступности (травмы, дисквалификации, «под
вопросом») игнорируются намеренно: они висят днями и неделями, а из-за
правок состава уведомления по ним приходят повторно.

Проблемой считается иконка (``typeId`` либо текст подсказки):

* ``34`` — «On the bench, potential substitute»;
* «Not starting in upcoming/current game» — попадает по тексту подсказки.

Игнорируются: ``12`` «Starting in upcoming/current game», ``32`` «Expected
to play in upcoming/current game», ``30`` «Out for next game», ``6``
«Suspended», ``1`` «Late fitness test (Game-time decision)», а также
новостные иконки игрока.

Состав разбит на слоты: ``statusId == "1"`` — основной (Active),
``"2"`` — скамейка (Reserve), ``"3"`` — лазарет (Injured Reserve).
Нас интересуют только игроки в основном составе (``statusId == "1"``).
"""
from __future__ import annotations

from dataclasses import dataclass

ACTIVE_SLOT_STATUS = "1"


@dataclass(frozen=True)
class StatusRule:
    """Правило распознавания иконки статуса.

    Иконка подходит, если её typeId входит в ``type_ids`` либо её
    подсказка начинается с одного из ``tooltip_prefixes``. Сравниваем
    начало, а не вхождение: подсказки новостей — это фразы с датой
    в начале, где «on the bench» может просто упоминаться в тексте.
    """

    severity: str
    emoji: str
    label: str
    type_ids: frozenset[str] = frozenset()
    tooltip_prefixes: tuple[str, ...] = ()

    def matches(self, icon: dict) -> bool:
        if str(icon.get("typeId")) in self.type_ids:
            return True
        tooltip = str(icon.get("tooltip") or "").lower()
        return any(tooltip.startswith(prefix) for prefix in self.tooltip_prefixes)


# Порядок задаёт приоритет: первый совпавший статус считается самым важным
# для игрока.
STATUS_RULES: list[StatusRule] = [
    StatusRule(
        "NOT_STARTING",
        "🟠",
        "не в стартовом составе",
        frozenset({"34"}),
        ("on the bench", "not starting"),
    ),
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

    def key(self) -> str:
        """Уникальный ключ игрока в составе команды для дедупликации."""
        return f"{self.team_id}:{self.player_id}"

    def line(self) -> str:
        return (
            f"{self.emoji} {self.player_name} "
            f"({self.position}, {self.club}) — {self.label}"
        )


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
            for rule in STATUS_RULES:
                if not any(rule.matches(icon) for icon in icons):
                    continue
                issues.append(
                    PlayerIssue(
                        team_id=team_id,
                        team_name=team_name,
                        player_id=str(scorer.get("scorerId", "")),
                        player_name=scorer.get("name", "?"),
                        position=scorer.get("posShortNames", "?"),
                        club=scorer.get("teamName", "?"),
                        severity=rule.severity,
                        emoji=rule.emoji,
                        label=rule.label,
                    )
                )
                break  # берём самый приоритетный статус игрока

    return issues
