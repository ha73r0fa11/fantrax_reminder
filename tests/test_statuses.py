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
    def test_out_icon_in_active_slot(self):
        resp = _roster([_row("1", _scorer([{"typeId": "30", "tooltip": "Hamstring - Out"}]))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "OUT")

    def test_suspended_icon(self):
        resp = _roster([_row("1", _scorer([{"typeId": "6", "tooltip": "Suspended"}]))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(issues[0].severity, "SUSPENDED")

    def test_doubtful_icon(self):
        resp = _roster([_row("1", _scorer([{"typeId": "1", "tooltip": "Back - Late fitness test"}]))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(issues[0].severity, "DOUBTFUL")

    def test_expected_to_play_is_not_an_issue(self):
        resp = _roster([_row("1", _scorer([{"typeId": "32", "tooltip": "Expected to play in upcoming/current game"}]))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_starting_is_not_an_issue(self):
        resp = _roster([_row("1", _scorer([{"typeId": "12", "tooltip": "Starting in upcoming/current game"}]))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

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

    def test_news_mentioning_bench_is_not_an_issue(self):
        icons = [
            {
                "typeId": "8",
                "tooltip": "Oct 10, 6:22 AM: Wilson (quadriceps) is on the bench for...",
            }
        ]
        resp = _roster([_row("1", _scorer(icons))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_reserve_slot_is_ignored(self):
        resp = _roster([_row("2", _scorer([{"typeId": "30", "tooltip": "Out"}]))])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_empty_slot_is_ignored(self):
        resp = _roster([_row("1", None)])
        self.assertEqual(detect_issues("t1", "Team", resp), [])

    def test_out_has_priority_over_doubtful(self):
        icons = [
            {"typeId": "1", "tooltip": "Late fitness test"},
            {"typeId": "30", "tooltip": "Out for next game"},
        ]
        resp = _roster([_row("1", _scorer(icons))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "OUT")

    def test_bench_has_priority_over_doubtful(self):
        icons = [
            {"typeId": "1", "tooltip": "Late fitness test"},
            {"typeId": "34", "tooltip": "On the bench, potential substitute"},
        ]
        resp = _roster([_row("1", _scorer(icons))])
        issues = detect_issues("t1", "Team", resp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "NOT_STARTING")


if __name__ == "__main__":
    unittest.main()
