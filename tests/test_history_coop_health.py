import struct
import unittest
import fresh_team_combat as core
from history_coop_health import build_memory


class CampaignHealthTests(unittest.TestCase):
    def setUp(self):
        self.ram=bytearray(0x8000000)
        self.put=lambda address,value:struct.pack_into('<I',self.ram,address,value)
        self.put(0x2ff10c,0x100000)
        self.put(0x100018,8)
        self.put(0x331dd0,1)
        self.put(core.ACTORS,0x110000)
        self.put(0x110000,2)
        struct.pack_into('<4I',self.ram,core.MODE,1,4,0x110000,4)
        for physical in range(4):
            actor=0x120000+physical*0x2000
            self.put(core.POINTERS+physical*4,actor)
            self.put(actor,physical)
            self.put(actor+8,physical&1)
            self.put(actor+0x998,1)
            self.put(actor+0x9ac,1)
            self.put(actor+0x9e4,30000)
            self.put(actor+0x9e8,60000)

    def plan(self,mask=7):return build_memory(self.ram,present_mask=mask)

    def test_enemy_scaled_preserving_damage_fraction(self):
        plan=self.plan()
        self.assertEqual(len(plan['blocks']),1)
        block=plan['blocks'][0]
        self.assertEqual(block['address'],0x122000+0x9e4)
        self.assertEqual(struct.unpack('<2I',bytes.fromhex(block['data_hex'])),(45000,90000))

    def test_allies_and_absent_enemies_are_not_changed(self):
        addresses={block['address'] for block in self.plan()['blocks']}
        for physical in (0,2,3):self.assertNotIn(0x120000+physical*0x2000+0x9e4,addresses)

    def test_dead_enemy_is_not_revived(self):
        self.put(0x122000+0x9e4,0)
        self.assertEqual(struct.unpack('<2I',bytes.fromhex(self.plan()['blocks'][0]['data_hex'])),(0,90000))

    def test_second_present_enemy_is_scaled(self):
        self.assertEqual(len(self.plan(15)['blocks']),2)

    def test_other_native_modes_are_refused(self):
        self.put(0x331dd0,0)
        with self.assertRaises(ValueError):self.plan()

    def test_stale_actor_identity_is_refused(self):
        self.put(0x122000,3)
        with self.assertRaises(ValueError):self.plan()

    def test_changed_manager_is_refused(self):
        self.put(core.MODE+8,0x110004)
        with self.assertRaises(ValueError):self.plan()


if __name__=='__main__':unittest.main()
