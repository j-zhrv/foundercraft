"""Public handoff/installation contracts, not a live Desktop or voice test."""
from pathlib import Path
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
class OnboardingContract(unittest.TestCase):
    def test_existing_marketplace_identity_and_no_new_services(self):
        market=json.loads((ROOT/'.agents/plugins/marketplace.json').read_text())
        self.assertEqual(market['name'],'foundercraft');self.assertEqual(len(market['plugins']),1)
        self.assertEqual(market['plugins'][0]['name'],'foundercraft')
        manifest=json.loads((ROOT/'plugins/foundercraft/plugin.json').read_text())
        self.assertEqual(manifest['version'],'0.3.1')
        self.assertEqual(set(manifest['extensions']['com.openai']),{'interface'})
    def test_install_guide_preserves_choice_and_distinguishes_profile_and_active_chat(self):
        text=(ROOT/'INSTALL.md').read_text()
        for token in ['foundercraft@foundercraft','j-zhrv/foundercraft','--ref main','plugin list --marketplace foundercraft --json','новый Work-чат','Выбор набора не является согласием','облачную песочницу','микрофон']:
            self.assertIn(token,text)
        self.assertNotIn('curl |',text);self.assertNotIn('codex exec',text)
    def test_coach_dispatches_site_handoff_without_loosening_session_consent(self):
        skill=(ROOT/'plugins/foundercraft/skills/foundercraft-coach/SKILL.md').read_text();self.assertIn('references/site-handoff.md',skill)
        handoff=(ROOT/'plugins/foundercraft/skills/foundercraft-coach/references/site-handoff.md').read_text()
        for token in ['публичный набор','не согласие начать','Открыть карточки','expectedStateVersion','не запускай её повторно','не переносит ответы']:
            self.assertIn(token,handoff)

class SelectedStartHandoff(unittest.TestCase):
    def test_selected_start_route_keeps_explicit_consent(self):
        from pathlib import Path
        text=(Path(__file__).resolve().parents[1]/'plugins/foundercraft/skills/foundercraft-coach/references/site-handoff.md').read_text()
        for expected in ['/ru/builds/<публичный-id>/start/','Открыть подготовку набора','получи явное согласие','не начинает сессию сам']:
            self.assertIn(expected,text)
