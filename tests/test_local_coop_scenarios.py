"""Local scenario receipts: independent seats, no accidental versus or story claim."""
import unittest
import scenario_menu
import story_missions


def mission():
    return dict(schema='tag-team-mission', version=1, id='local-coop-test',
                title='Local co-op', human_players=2, player_team=1,
                player_selection=False, events=[], fighters=[
                    dict(id='goku_p1', team=1, slot=1, character=1),
                    dict(id='goku_p2', team=1, slot=2, character=1),
                    dict(id='vegeta', team=2, slot=1, character=29)])


class CoOpScenarioTests(unittest.TestCase):
    def test_duplicate_character_has_two_seats(self):
        d = story_missions.validate(mission())
        browser = object.__new__(scenario_menu.Controller)
        browser.document, browser.launched = d, True
        receipt = browser.selection_receipt(dict(mode='teams', humans=1, choice=0))
        self.assertEqual((receipt['humans'], receipt['assignment']), (2, (0, 2)))

    def test_missing_or_reserve_partner_is_rejected(self):
        for reserve in (False, True):
            d = mission()
            if reserve:
                d['fighters'][1]['reserve'] = True
            else:
                d['fighters'].pop(1)
            with self.assertRaises(story_missions.InvalidMission):
                story_missions.validate(d)

    def test_other_team_and_cpu_only(self):
        d = mission()
        for f in d['fighters']:
            f['team'] = 3 - f['team']
        d['player_team'] = 2
        browser = object.__new__(scenario_menu.Controller)
        browser.document, browser.launched = story_missions.validate(d), True
        self.assertEqual(browser.selection_receipt(dict(mode='teams', humans=1, choice=0))['assignment'], (1, 3))
        cpu = dict(mode='teams', humans=0)
        self.assertEqual(browser.selection_receipt(cpu), cpu)

    def test_ordinary_scenario_and_original_menu_unchanged(self):
        browser = object.__new__(scenario_menu.Controller)
        browser.document, browser.launched = mission(), False
        original = dict(mode='teams', humans=1, choice=5)
        self.assertEqual(browser.selection_receipt(original), original)
        browser.launched = True
        self.assertEqual(browser.selection_receipt(original), original)
        del browser.document['human_players']
        self.assertEqual(browser.selection_receipt(original), original)

    def test_shared_physical_slot_is_rejected(self):
        d = mission()
        d['fighters'][1]['slot'] = 1
        with self.assertRaises(story_missions.InvalidMission):
            story_missions.validate(d)


if __name__ == '__main__':
    unittest.main()
