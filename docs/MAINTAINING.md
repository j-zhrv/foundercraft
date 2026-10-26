# Поддержка одного публичного пакета

`plugins/foundercraft/` — единственный поддерживаемый исходник устанавливаемого плагина. `.agents/plugins/marketplace.json` — каталог FounderCraft. Владелец и будущие пользователи устанавливают одну запись `foundercraft@foundercraft` из этого репозитория.

Версия 0.2.0 перенесена из существующего личного FounderCraft 0.1.22, полученного поддерживаемым чтением Plugin Creator. Это не новая имитация методики. Сохранены основной skill, шесть справочников и иконка. Педагогические справочники `guided-dialogue.md`, `learning-feedback.md` и `practice.md` перенесены без содержательных изменений; изменения сосредоточены на обезличивании, первом входе, восстановлении и границах сохранения данных. Приватный экспорт и его служебные идентификаторы в репозиторий не входят.

## Формат

- Portable `plugin.json`: Agent Plugins 1.0; skill в фиксированном `skills/`.
- `.codex-plugin/plugin.json`: совместимый манифест с той же идентичностью, версией и интерфейсом. При наличии `extensions.com.openai` в корневом манифесте OpenAI использует его целиком, без слияния с overlay.
- Нет MCP endpoint, hooks, runner, настроек моделей или app bindings. WebMCP обнаруживается на текущей странице сайта.
- `policy.installation=AVAILABLE`, `authentication=ON_USE`: значения проверены по схеме локального app-server. У skills-only пакета нет внешнего входа в аккаунт.
- `policy.products` намеренно отсутствует: нет запроса ограничивать продукт. Официальный пример marketplace допускает отсутствие поля и описывает Work. Ограничение `CODEX` из примера open-pstack не перенесено, непроверенные значения для Work не придуманы.

Пример [open-pstack](https://github.com/ericlitman/open-pstack/blob/main/.agents/plugins/marketplace.json) использован только как модель расположения пакета и каталога. Его рабочие процессы и runner не включены.

## Проверка перед выпуском

Нужны Python 3 и зависимости только для разработчика (пользователю плагина они не нужны):

```sh
python3 -m venv /tmp/foundercraft-check
/tmp/foundercraft-check/bin/pip install -r requirements-dev.txt
/tmp/foundercraft-check/bin/python scripts/check.py
curl --fail --location https://agent-plugins.org/schemas/1.0.0/plugin.schema.json -o /tmp/foundercraft-plugin.schema.json
/tmp/foundercraft-check/bin/python scripts/check.py --schema /tmp/foundercraft-plugin.schema.json --links --archive /tmp/foundercraft.zip
```

Проверка читает JSON/YAML как данные, проверяет согласованность манифестов, пути, ссылки, состав пакета и типовые следы персональных данных/секретов. `--schema` дополнительно проверяет корневой manifest официальной схемой; `--links` делает сетевые GET-запросы. Детектор не доказывает отсутствие всех возможных секретов: перед push просмотрите весь staged diff и список файлов. Приватный оригинал, дампы, записи, локальные сессии и пользовательские данные не добавляйте даже в ранние коммиты.

`--archive` создаёт ZIP только из проверенного плагина, без marketplace, репозитория и личных данных. Архив пишется вне дерева исходника. Это дополнительный переносимый пакет; основной путь установки — GitHub marketplace.

После проверки увеличьте SemVer в обоих манифестах, обновите CHANGELOG, выполните smoke test из [TESTING.md](TESTING.md), сделайте обычный commit и push. Не меняйте бюджет Actions и не используйте force push. GitHub Actions для этого пакета не требуется.

После установки `python3 scripts/smoke.py --codex /путь/к/runtime/codex` проверяет через `plugin/read`, что пакет установлен, включён и содержит ожидаемый skill без MCP/app/hooks. Укажите бинарный файл, который использует Desktop; `codex` из PATH может быть другой версией. Для Git snapshot передайте `--marketplace-path /путь/к/snapshot/.agents/plugins/marketplace.json`. Этот тест не запускает модель или голос и не доказывает качество учебного диалога.

Изменения сайта выпускаются отдельно. Плагин следует актуальным регистрациям WebMCP; схема или HTML сайта не заменяют реального вызова. Непрочитанная статья, поставленная навигация и сохранённая сессия не доказывают обучение человека.
