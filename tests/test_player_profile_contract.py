import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class PlayerProfileContract(unittest.TestCase):
    def test_profile_requires_specific_consent_and_does_not_promise_sync(self):
        text = (ROOT / 'plugins/foundercraft/skills/foundercraft-coach/SKILL.md').read_text()
        for phrase in ('foundercraft_get_player_profile', 'foundercraft_update_player_profile', 'profileRevision', 'дождись согласия', 'не разыскивай другие беседы', 'не обещай синхронизацию', 'foundercraft_get_player_profile_history', 'links.workIds', 'links.buildIds'):
            self.assertIn(phrase, text)
    def test_privacy_discloses_local_storage_and_control(self):
        text = (ROOT / 'PRIVACY.md').read_text()
        for phrase in ('локальных данных браузера', 'не синхронизируется автоматически', 'изменять и удалять', 'согласованные'):
            self.assertIn(phrase, text)

if __name__ == '__main__':
    unittest.main()
