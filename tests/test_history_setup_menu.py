import unittest
from types import SimpleNamespace
from unittest.mock import patch
import autopilot
import history_setup_menu as menu
import mod_settings
import native_mode_menu
from test_history_story_roles import EE


class StorySetupModelTests(unittest.TestCase):
    def test_solo_confirmation_does_not_require_cooperative_settings(self):
        c=menu.Controller();result=c.press(menu.CROSS)
        self.assertEqual((result['humans'],result['mode']),(1,'teams'))
        self.assertTrue(result['history'])

    def test_two_players_choose_hp_from_the_original_history_menu(self):
        c=menu.Controller();c.press(menu.RIGHT);self.assertIsNone(c.press(menu.CROSS))
        self.assertEqual(c.page,'rules')
        c.press(menu.RIGHT);c.press(menu.DOWN);c.press(menu.RIGHT);c.press(menu.DOWN)
        c.press(menu.RIGHT);c.press(menu.DOWN);c.press(menu.RIGHT);c.press(menu.DOWN)
        result=c.press(menu.CROSS)
        self.assertEqual(result['humans'],2)
        self.assertEqual(result['health'],{'history_ally_hp_percent':150,'history_enemy_hp_percent':175,
                                           'history_enemy_hp_per_ally_bonus':50,
                                           'history_formation':'time_x_time'})

    def test_inline_panel_leaves_the_original_history_scene_visible(self):
        from guest_loading_screen import CAPACITY,gif_packet,image_rectangles
        c=menu.Controller()
        image=c.picture()
        self.assertEqual(image.size,(512,448))
        self.assertEqual(image.getpixel((0,0)),(255,0,255))
        self.assertNotEqual(image.getpixel((256,270)),(255,0,255))
        packet=gif_packet(image_rectangles(image,key=(255,0,255)))
        self.assertLess(len(packet),CAPACITY)
        c.page='rules'
        image=c.picture()
        self.assertEqual(image.getpixel((0,0)),(255,0,255))
        self.assertNotEqual(image.getpixel((256,275)),(255,0,255))
        packet=gif_packet(image_rectangles(image,key=(255,0,255)))
        self.assertLess(len(packet),CAPACITY)

    def test_select_cannot_dismiss_or_commit_the_question(self):
        c=menu.Controller()
        for _ in range(4):self.assertIsNone(c.press(1))
        self.assertEqual(c.page,'players');self.assertIsNone(c.result)

    def test_back_from_rules_keeps_the_choice_and_does_not_commit(self):
        c=menu.Controller();c.press(menu.RIGHT);c.press(menu.CROSS);c.press(menu.TRIANGLE)
        self.assertEqual((c.page,c.players),('players',2));self.assertIsNone(c.result)

    def test_hp_limits_are_enforced(self):
        c=menu.Controller();c.page='rules'
        for _ in range(30):c.press(menu.RIGHT)
        self.assertEqual(c.ally_hp,400)
        for _ in range(30):c.press(menu.LEFT)
        self.assertEqual(c.ally_hp,25)


class StorySetupHostIntegrationTests(unittest.TestCase):
    def test_new_install_enables_the_story_setup_interface(self):
        self.assertIs(mod_settings.validate_settings({})['fullcoop_interface'],True)

    def test_per_ally_enemy_hp_bonus_has_safe_settings_bounds(self):
        self.assertEqual(mod_settings.validate_settings({})['history_enemy_hp_per_ally_bonus'],25)
        self.assertEqual(mod_settings.validate_settings({'history_enemy_hp_per_ally_bonus':0})[
            'history_enemy_hp_per_ally_bonus'],0)
        for value in (True,-1,101,25.5):
            with self.subTest(value=value),self.assertRaises(ValueError):
                mod_settings.validate_settings({'history_enemy_hp_per_ally_bonus':value})

    def test_menu_host_returns_history_choice_to_the_watcher(self):
        host=object.__new__(native_mode_menu.Controller)
        host.closed=False;host.settings={}
        host.scenarios=SimpleNamespace(settings={},checkpoint_ready=False)
        choice=dict(mode='coop',humans=2,history=True,
                    health=dict(history_ally_hp_percent=125,history_enemy_hp_percent=175,
                                history_enemy_hp_per_ally_bonus=25,history_formation='duo'))
        host.history_setup=SimpleNamespace(tick=lambda _p:choice)
        self.assertEqual(host.tick(object()),choice)
        self.assertEqual((host.mode,host.humans,host.custom_match),("coop",2,True))
        self.assertEqual(host.history_config,choice['health'])

    def test_history_opt_in_survives_native_menu_controller_dismissal(self):
        watcher=autopilot.Autopilot()
        watcher.mode_menu=SimpleNamespace(custom_match=False)
        watcher.history_coop=True
        watcher.tournament=None
        self.assertTrue(watcher.preparation_enabled)
        with patch.object(autopilot,'PineClient') as pine,patch.object(autopilot.native_preparation,'arm') as arm:
            pine.return_value.__enter__.return_value=object()
            watcher.sync_preparation(SimpleNamespace(streaming=True,clean=True))
        arm.assert_called_once_with(pine.return_value.__enter__.return_value,
            include_single_ffa=True,accepted_mode=1)
        watcher.history_coop=False
        self.assertFalse(watcher.preparation_enabled)


class StorySetupGuestTests(unittest.TestCase):
    def setUp(self):
        self.manager=0x180000
        self.memory={menu.CONTROL:menu.MAGIC,menu.CONTROL+4:1,menu.CONTROL+8:180,
            menu.CONTROL+20:self.manager,menu.MANAGER:self.manager,self.manager+0x18:6}
        self.code=[(menu.CODE,menu.input_code())]

    def cpu(self):return EE(self.code,self.memory)

    def test_second_port_is_captured_and_both_native_inputs_are_consumed(self):
        self.memory.update({menu.PAD+0x1c0+0x148:menu.RIGHT,menu.PAD+0x1c0+0x150:menu.RIGHT,
                            menu.PAD+0x18c:menu.CROSS,menu.PAD+0x1c0+0x18c:menu.CROSS})
        cpu=self.cpu();cpu.run(menu.CODE)
        self.assertEqual(cpu.r[2],1)
        self.assertEqual(cpu.mem[menu.CONTROL+12],menu.RIGHT)
        self.assertEqual(cpu.mem[menu.CONTROL+24],menu.RIGHT)
        for port in (0,0x1c0):
            for field in (0x150,0x18c,0x190):self.assertEqual(cpu.mem[menu.PAD+port+field],0)

    def test_wrong_scene_or_owner_expires_without_consuming_native_input(self):
        for field,value in ((self.manager+0x18,7),(menu.CONTROL+20,0x190000)):
            with self.subTest(field=field):
                memory=dict(self.memory);memory[field]=value;memory[menu.PAD+0x150]=menu.CROSS
                cpu=EE(self.code,memory);cpu.run(menu.CODE)
                self.assertEqual(cpu.r[2],0);self.assertEqual(cpu.mem[menu.CONTROL+4],0)
                self.assertEqual(cpu.mem[menu.PAD+0x150],menu.CROSS)

    def test_confirmation_is_drained_until_both_ports_release(self):
        self.memory.update({menu.CONTROL+4:2,menu.PAD+0x148:menu.CROSS})
        cpu=self.cpu();cpu.run(menu.CODE);self.assertEqual(cpu.mem[menu.CONTROL+4],2)
        cpu.mem[menu.PAD+0x148]=0
        release=EE(self.code,cpu.mem);release.run(menu.CODE)
        self.assertEqual(release.mem[menu.CONTROL+4],0)
        self.assertEqual(release.r[2],1) # the release frame is also filtered
        release.mem[menu.PAD+0x150]=menu.CROSS
        native=EE(self.code,release.mem);native.run(menu.CODE)
        self.assertEqual(native.r[2],0);self.assertEqual(native.mem[menu.PAD+0x150],menu.CROSS)


if __name__=='__main__':unittest.main()
