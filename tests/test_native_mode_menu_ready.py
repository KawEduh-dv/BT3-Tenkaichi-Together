import unittest
from unittest.mock import patch
import native_mode_menu as menu


class Memory:
    def __init__(self, values):self.values=values
    def read_u32(self,address):return self.values.get(address,0)


class NativeMenuReadinessTests(unittest.TestCase):
    def memory(self,*,scene=4,tree=0x180200,nodes=0x180400,count=72):
        values={
            menu.old.SCENE_MANAGER:0x180000,
            0x180000+0x18:scene,
            menu.assets.MAIN_OBJECT:0x181000,
            0x181000+0x34:tree,
            0x181000+0x144:9,
            tree:nodes,
            tree+4:count,
        }
        for index,descriptor in ((8,0x182000),(12,0x183000)):
            values[0x181000+0x40+4*index]=descriptor
            values[descriptor+0x38]=0x184000+index*0x21000
            values[descriptor+0x3c]=0x184000+index*0x21000+0x20080
            values[descriptor+8]=0x20080
            values[descriptor+12]=0x480
        return Memory(values)

    def test_main_menu_waits_for_its_native_label_tree(self):
        self.assertTrue(menu.ready(self.memory()))

    def test_partial_tree_pointer_is_not_treated_as_a_pager_failure(self):
        self.assertFalse(menu.ready(self.memory(tree=0xFFFFFFFF)))

    def test_partial_or_unbuilt_label_array_is_not_ready(self):
        self.assertFalse(menu.ready(self.memory(nodes=0xFFFFFFFF)))
        self.assertFalse(menu.ready(self.memory(count=0)))

    def test_unpopulated_or_out_of_range_atlas_dmas_wait_for_native_menu(self):
        memory=self.memory()
        memory.values[0x181000+0x40+4*8]=0xFFFFFFFF
        self.assertFalse(menu.ready(memory))
        memory=self.memory()
        memory.values[0x182000+0x38]=0x076FFFF0
        self.assertFalse(menu.ready(memory))

    def test_story_scene_never_reads_the_main_menu_object(self):
        self.assertFalse(menu.ready(self.memory(scene=6)))

    def test_transient_tree_pointer_race_waits_without_disabling_the_menu(self):
        with patch.object(menu,'owned_plan',side_effect=ValueError('Native menu address out of range')):
            self.assertIsNone(menu.try_owned_plan(object()))
        with patch.object(menu,'owned_plan',side_effect=ValueError('Invalid native menu asset pointer')):
            self.assertIsNone(menu.try_owned_plan(object()))
        with patch.object(menu,'owned_plan',side_effect=ValueError('Native animated label nodes changed')):
            self.assertIsNone(menu.try_owned_plan(object()))

    def test_unrecognized_menu_errors_still_surface(self):
        with patch.object(menu,'owned_plan',side_effect=ValueError('Unexpected native menu row count')):
            with self.assertRaisesRegex(ValueError,'Unexpected native menu row count'):
                menu.try_owned_plan(object())


if __name__=='__main__':unittest.main()
