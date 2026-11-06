"""Тесты детекции статусов (bot/statuses.py). Запуск: python -m unittest."""
import unittest

from bot.statuses import detect_issues


def _roster(rows):
    return {"tables": [{"rows": rows}]}


def _row(status_id, scorer):
    return {"statusId": status_id, "scorer": scorer}


def _scorer(icons, name="Player", pos="F", club="Arsenal"):
    return {
        "scorerId": "p1",
        "name": name,
        "posShortNames": pos,
        "teamName": club,
        "icons": icons,
    }


class DetectIssuesTest(unittest.TestCase):
    def test_on_the_bench_is_an_issue(self):
        resp = _roster([_row("1", _scorer([{"typeId": "34", "tooltip": "On the bench, potential substitute"}]))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "NOT_STARTING")

    def test_not_starting_is_detected_by_tooltip(self):
        icons = [{"typeId": "99", "tooltip": "Not starting in upcoming/current game"}]
        resp = _roster([_row("1", _scorer(icons))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "NOT_STARTING")

    def test_reserve_slot_is_ignored(self):
        resp = _roster([_row("2", _scorer([{"typeId": "34", "tooltip": "On the bench, potential substitute"}]))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_empty_slot_is_ignored(self):
        resp = _roster([_row("1", None)])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_news_mentioning_bench_is_not_an_issue(self):
        icons = [
            {
                "typeId": "8",
                "tooltip": "Oct 10, 6:22 AM: Wilson (quadriceps) is on the bench for...",
            }
        ]
        resp = _roster([_row("1", _scorer(icons))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])


class IgnoredStatusesTest(unittest.TestCase):
    """Статусы доступности висят днями и уведомлениями не считаются."""

    def _assert_ignored(self, type_id, tooltip):
        icons = [{"typeId": type_id, "tooltip": tooltip}]
        resp = _roster([_row("1", _scorer(icons))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_starting_is_ignored(self):
        self._assert_ignored("12", "Starting in upcoming/current game")

    def test_expected_to_play_is_ignored(self):
        self._assert_ignored("32", "Expected to play in upcoming/current game")

    def test_out_is_ignored(self):
        self._assert_ignored(
            "30", "Hamstring - Out for next game - Expected return Nov 21"
        )

    def test_suspended_is_ignored(self):
        self._assert_ignored("6", "Suspended")

    def test_late_fitness_test_is_ignored(self):
        self._assert_ignored(
            "1",
            "Undisclosed - Late fitness test (Game-time decision) - Expected return Nov 8",
        )


if __name__ == "__main__":
    unittest.main()
