import unittest
from history_coop_rules import (R3Coordinator,EventKind,EnemyWaves,StoryEnemy,enemy_health,
                                campaign_participation_mask)
from history_coop_plan import build,EnemyIdentity
from history_native_reader import NativeMember,NativeTeam,HistorySnapshot


class R3Tests(unittest.TestCase):
    def test_p2_claim_survives_resource_wait_and_p1_later_press(self):
        c=R3Coordinator();c.arm(1,'replace')
        self.assertIsNone(c.update(False,True,0))
        d=c.update(True,False,3)
        self.assertEqual(d.players,(2,))

    def test_transformation_waits_for_both_and_is_submitted_once(self):
        c=R3Coordinator();c.arm(1,'transform')
        self.assertIsNone(c.update(True,False,1))
        self.assertEqual(c.update(False,False,3).players,(1,2))
        self.assertIsNone(c.update(True,True,3))
        c.acknowledge(1,success=True)
        self.assertIsNone(c.update(False,True,3))

    def test_held_button_does_not_activate_next_event(self):
        c=R3Coordinator();c.arm(1,'replace');c.update(True,False)
        c.acknowledge(1,success=True);c.arm(2,'replace')
        self.assertIsNone(c.update(True,False))
        c.update(False,False)
        self.assertEqual(c.update(False,True).players,(2,))

    def test_simultaneous_replacement_has_one_winner(self):
        c=R3Coordinator();c.arm(1,EventKind.REPLACE)
        self.assertEqual(c.update(True,True).players,(1,))

    def test_failed_native_command_is_not_marked_complete(self):
        c=R3Coordinator();c.arm(1,'transform');c.update(True,False)
        c.acknowledge(1,success=False)
        self.assertFalse(c.completed)
        self.assertEqual(c.update(False,False).players,(1,2))

    def test_stale_acknowledgement_cannot_complete_another_event(self):
        c=R3Coordinator();c.arm(1,'replace');c.update(True,False)
        with self.assertRaises(ValueError):c.acknowledge(2,success=True)


class CampaignFormationTests(unittest.TestCase):
    def test_duo_mode_keeps_p1_p2_and_every_native_enemy_not_ally_reserves(self):
        # The observed Nappa setup was five allies against one enemy (mask 343).
        self.assertEqual(campaign_participation_mask(343,10,'duo'),0b111)

    def test_time_x_time_mode_retains_every_authored_fighter(self):
        self.assertEqual(campaign_participation_mask(343,10,'time_x_time'),343)

    def test_formation_requires_two_player_bodies_and_an_enemy(self):
        for mask in (0,0b10,0b101):
            with self.subTest(mask=mask),self.assertRaises(ValueError):
                campaign_participation_mask(mask,6,'duo')
        with self.assertRaises(ValueError):campaign_participation_mask(343,10,'everybody')

    def test_single_native_ally_gets_a_reserved_second_player_body(self):
        self.assertEqual(campaign_participation_mask(0b11,4,'duo'),0b111)
        self.assertEqual(campaign_participation_mask(0b11,4,'time_x_time'),0b111)


class WaveTests(unittest.TestCase):
    def test_next_pair_waits_for_both_defeats_and_story_gate(self):
        w=EnemyWaves([StoryEnemy(str(i),(i,)) for i in range(5)])
        self.assertEqual(len(w.release_next(story_ready=True)),2)
        w.defeat('0');self.assertEqual(w.release_next(story_ready=True),())
        w.defeat('1');self.assertEqual(w.release_next(story_ready=False),())
        self.assertEqual(len(w.release_next(story_ready=True)),2)
        w.defeat('2');w.defeat('3')
        self.assertEqual(len(w.release_next(story_ready=True)),1)
        w.defeat('4');self.assertTrue(w.complete)

    def test_form_change_does_not_consume_an_enemy_or_wave_slot(self):
        w=EnemyWaves([StoryEnemy('boss',(1,2,3)),StoryEnemy('other',(4,))])
        w.release_next(story_ready=True);w.transform('boss',2);w.transform('boss',3)
        self.assertEqual(w.active,{'boss':3,'other':4})
        self.assertEqual(w.defeated,set())
        self.assertFalse(w.complete)

    def test_two_identical_characters_can_be_distinct_enemies(self):
        w=EnemyWaves([StoryEnemy('saibaman-a',(70,)),StoryEnemy('saibaman-b',(70,))])
        self.assertEqual(len(w.release_next(story_ready=True)),2)

    def test_unauthorized_form_is_rejected(self):
        w=EnemyWaves([StoryEnemy('boss',(1,2))]);w.release_next(story_ready=True)
        with self.assertRaises(ValueError):w.transform('boss',3)


def snapshot(allies=(0,22),enemies=(77,)):
    def team(side,characters):
        return NativeTeam(0x1800000+side*0x1600,0x900000+side*0x2000,0,
            tuple(NativeMember(side,i,c,0,30000,40000 if not side else 60000,bytes(164))
                  for i,c in enumerate(characters)))
    return HistorySnapshot(0x1700000,0x1600000,(team(0,allies),team(1,enemies)),(False,False))


class PlanTests(unittest.TestCase):
    def test_original_allies_are_retained_and_bench_stays_outside_human_seats(self):
        p=build(snapshot((0,22,25)),[EnemyIdentity('raditz',(0,))],
                verified_costumes={0:(0,1),22:(0,),25:(0,)})
        self.assertEqual([s.native_member.character for s in p.humans],[0,22])
        self.assertEqual([m.character for m in p.bench],[25])
        self.assertEqual(p.enemy_maximum_hp,(('raditz',90000),))

    def test_single_ally_is_duplicated_with_an_original_alternate_costume(self):
        p=build(snapshot((0,)),[EnemyIdentity('raditz',(0,))],verified_costumes={0:(0,1)})
        self.assertEqual([s.costume for s in p.humans],[0,1])
        self.assertTrue(p.humans[1].duplicated)

    def test_explicit_form_group_occupies_one_enemy_identity(self):
        p=build(snapshot(enemies=(50,51,52)),[EnemyIdentity('boss',(0,1)),EnemyIdentity('other',(2,))],
                verified_costumes={0:(0,),22:(0,)})
        self.assertEqual(len(p.enemies),2)
        self.assertEqual(p.enemies[0].forms,(50,51))

    def test_missing_or_shared_enemy_slot_is_not_guessed(self):
        for identities in ([EnemyIdentity('a',(0,))],
                           [EnemyIdentity('a',(0,1)),EnemyIdentity('b',(1,))]):
            with self.assertRaises(ValueError):
                build(snapshot(enemies=(50,51)),identities,verified_costumes={0:(0,),22:(0,)})

    def test_unverified_costume_is_rejected(self):
        with self.assertRaises(ValueError):
            build(snapshot(),[EnemyIdentity('raditz',(0,))],verified_costumes={0:(1,),22:(0,)})

    def test_health_scaling_is_bounded(self):
        self.assertEqual(enemy_health(30000),60000)
        self.assertEqual(enemy_health(60000),90000)
        self.assertEqual(enemy_health(1000000),1000000)


if __name__=='__main__':unittest.main()
