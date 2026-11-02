"""Static instruction-contract checks, not a browser or model behavior test."""
from pathlib import Path
import unittest


REFERENCES = (Path(__file__).resolve().parents[1] /
              'plugins/foundercraft/skills/foundercraft-coach/references')


class BrowserRecoveryContract(unittest.TestCase):
    def test_recovery_is_bounded_and_does_not_bypass_denials(self):
        text = (REFERENCES / 'browser.md').read_text()
        for required in (
            'browser.user is unavailable',
            'Если та же ошибка повторяется',
            'допустима одна попытка',
            'Отказ хоста или пользователя нельзя обходить',
            'Не сбрасывай среду, пока вызов ещё выполняется',
            'не перезагрузка страницы, очистка данных сайта',
            'не повторяй её после восстановления',
            'Если сброс недоступен',
        ):
            self.assertIn(required, text)

    def test_reset_uses_fresh_same_browser_context_before_continuing(self):
        text = (REFERENCES / 'browser.md').read_text()
        steps = [text.index(label) for label in (
            '1. Вызови доступный',
            '2. Первый вызов после сброса',
            '3. Получи актуальный список вкладок',
            '4. Заново получи capability',
            '5. Продолжи исходный запрос',
        )]
        self.assertEqual(steps, sorted(steps))
        for required in ('того же встроенного браузера', 'не создавай дубликат',
                         'один свежий `get_context`', 'используй `read_material`'):
            self.assertIn(required, text)

    def test_user_changed_session_invalidates_old_conflict(self):
        text = (REFERENCES / 'voice-entry.md').read_text()
        start = text.index('Реплика «я уже начал другой набор»')
        paragraph = text[start:text.index('\n\n', start)]
        for required in ('один свежий `get_context`', 'фактической карточки',
                         'свежей `expectedStateVersion`',
                         'не вызывай `start_learning`', 'уточни цель до мутации'):
            self.assertIn(required, paragraph)
