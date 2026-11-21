import unittest

import fullcoop_loading_art as art


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


if __name__ == '__main__':
    unittest.main()
