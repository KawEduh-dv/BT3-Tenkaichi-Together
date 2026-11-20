"""Local visual policy must not load upstream images, including on transitions."""
import unittest
from unittest.mock import patch
import native_menu_texture
import guest_loading_screen
import fullcoop_loading_art as art
import scenario_menu
from pathlib import Path


class VisualPolicyTests(unittest.TestCase):
    def test_generic_transition_does_not_announce_cooperative_history(self):
        with patch.object(art, 'centred', wraps=art.centred) as draw_text:
            art.transition()
        words = [call.args[1] for call in draw_text.call_args_list]
        self.assertIn('CARREGANDO', words)
        self.assertFalse(any('COOPERATIVO' in word or 'JOGADORES' in word for word in words))

    def test_transition_uses_no_logo_asset(self):
        native_menu_texture.picture.cache_clear()
        native_menu_texture.packet.cache_clear()
        with patch('PIL.Image.open', side_effect=AssertionError('Unexpected external image')):
            pic = native_menu_texture.picture()
            self.assertTrue(any(high>low for low,high in pic.convert('RGB').getextrema()))
            self.assertLess(len(native_menu_texture.packet()), native_menu_texture.END-native_menu_texture.DATA)

    def test_loading_uses_no_external_art(self):
        with patch('PIL.Image.open', side_effect=AssertionError('Unexpected external image')):
            layers = guest_loading_screen._compose([], 50, 'Loading', 'teams', 2)
        self.assertEqual(layers['background'].size, (512, 448))
        self.assertIsNone(layers['foreground'])
        self.assertIsNone(layers['lights'])
        self.assertFalse(guest_loading_screen.is_v4(layers))

    def test_portrait_cannot_escape_iso_asset_directory(self):
        with patch.object(art.character_names,'character_info',return_value={'portrait_path':'C:/Windows/test.png'}):
            with self.assertRaises(ValueError):
                art.portrait(1)

    def test_own_browser_excludes_upstream_story_examples(self):
        own=scenario_menu.missions.LIBRARY/'FullCoop'/'raditz.json'
        upstream=scenario_menu.missions.LIBRARY/'Examples'/'saiyans.json'
        rows=[{'path':own,'title':'Local'},{'path':upstream,'title':'Example'}]
        with patch.object(scenario_menu,'library',return_value=rows):
            self.assertEqual(scenario_menu.visible_library({'fullcoop_interface':True}),rows[:1])
            self.assertEqual(scenario_menu.visible_library({}),rows)


if __name__ == '__main__':
    unittest.main()
