import unittest

import fullcoop_loading_art as art
import guest_loading_screen as cover
import native_preparation
from prototype import Assembler
from test_ai_shadow import Mips


class PreparationLabelTests(unittest.TestCase):
    def test_live_preparation_stages_are_visible_in_portuguese(self):
        cases = {
            'Preparing team battle': 'Organizando as equipes...',
            'Loading fighters': 'Carregando os lutadores...',
            'Preparing arena': 'Preparando a arena...',
            'Getting ready': 'Finalizando os detalhes...',
            'Preparing tag attacks': 'Preparando os ataques em equipe...',
            'Starting your match...': 'Iniciando a luta...',
        }
        for source, visible in cases.items():
            with self.subTest(source=source):
                self.assertEqual(art.preparation_label(source), visible)

    def test_unknown_stage_is_preserved_and_empty_stage_gets_a_fallback(self):
        self.assertEqual(art.preparation_label('Carregando recursos especiais'),
                         'Carregando recursos especiais')
        self.assertEqual(art.preparation_label(''), 'Preparando a batalha...')


class HistoryLoadingGateTests(unittest.TestCase):
    def run_gate(self, *, loop=0, accepted=0, history=0, scene=0):
        base=0x00100000
        a=Assembler(base);cover.emit_battle_surface_gate(a)
        a.label('surface_ready');a.addiu(2,0,1);a.jr()
        a.label('undrawn');a.move(2,0);a.jr()
        cpu=Mips({'segments':[dict(address=base,data_hex=a.finish().hex())]})
        scene_manager=0x00180000
        cpu.w(cover.SCENE_LOOP,loop)
        cpu.w(native_preparation.ACCEPTED_MODE,accepted)
        cpu.w(cover.A(0x331DD0),history)
        cpu.w(cover.A(0x2FF10C),scene_manager if scene else 0)
        cpu.w(scene_manager+0x18,scene)
        cpu.run(base)
        return cpu.r[2]

    def test_normal_battle_keeps_the_existing_cover_route(self):
        self.assertEqual(self.run_gate(loop=1),1)

    def test_dragon_history_coop_battle_draws_the_cover_with_loop_flag_clear(self):
        self.assertEqual(self.run_gate(accepted=1,history=1,scene=8),1)

    def test_history_chapter_and_unarmed_story_battles_do_not_draw_a_battle_cover(self):
        self.assertEqual(self.run_gate(accepted=1,history=1,scene=6),0)
        self.assertEqual(self.run_gate(accepted=0,history=1,scene=8),0)
        self.assertEqual(self.run_gate(accepted=1,history=0,scene=8),0)


class LoadingVisibilityRetryTests(unittest.TestCase):
    def test_an_unconfirmed_frame_is_retried_and_never_reported_as_shown(self):
        import autopilot

        class Presentation:
            visible=False
            def set_mode(self,*_args):pass
            def show(self,*_args,**_kwargs):pass
            def wait_visible(self,timeout=2):return self.visible

        watcher=object.__new__(autopilot.Autopilot)
        watcher.presentation=Presentation();watcher.cover_started=False;watcher.progress=0
        watcher.battle_mode='coop';watcher.humans=2
        lines=[]
        with unittest.mock.patch.object(autopilot,'log',lines.append):
            watcher.cover('Carregando os lutadores...',0)
            self.assertFalse(watcher.cover_confirmed)
            self.assertTrue(any('not confirmed a visible frame' in line for line in lines))
            watcher.presentation.visible=True
            watcher.cover('Preparando a arena...',50)
        self.assertTrue(watcher.cover_confirmed)


if __name__ == '__main__':
    unittest.main()
