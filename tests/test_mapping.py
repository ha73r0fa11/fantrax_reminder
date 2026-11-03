"""Тесты привязки команд к chat_id (bot/mapping.py)."""
import unittest

from bot.mapping import resolve_chat_ids


class ResolveChatIdsTest(unittest.TestCase):
    def setUp(self):
        self.teams = {
            "t1": "Fq",
            "t2": "butep",
            "t3": "Sognare ✨",
        }

    def test_match_by_name_case_insensitive(self):
        mapping = {"fq": 111, "BUTEP": 222}
        self.assertEqual(
            resolve_chat_ids(mapping, self.teams),
            {"t1": "111", "t2": "222"},
        )

    def test_match_by_team_id(self):
        mapping = {"t3": 333}
        self.assertEqual(resolve_chat_ids(mapping, self.teams), {"t3": "333"})

    def test_unmatched_team_omitted(self):
        mapping = {"fq": 111}
        self.assertEqual(resolve_chat_ids(mapping, self.teams), {"t1": "111"})

    def test_chat_id_cast_to_string(self):
        mapping = {"Fq": 111}
        self.assertEqual(resolve_chat_ids(mapping, self.teams), {"t1": "111"})


if __name__ == "__main__":
    unittest.main()
