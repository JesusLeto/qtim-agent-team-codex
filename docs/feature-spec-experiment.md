# Обкатка одной спецификации qtim-feature

Ветка: `experiment/qtim-feature-spec`. Версия: `2.16.0-experimental.1`.
Изменение остаётся экспериментальным до проверки на реальной задаче. Основная
ветка репозитория и установленный плагин не обновляются автоматически.

## Подготовка

Выбери реальную задачу и отдельный worktree целевого проекта. Generated `.codex`
состояние проверяй/мигрируй в этом worktree, сохраняя основное дерево и его WIP.
Если переносишь существующий charter/роли, проверь portable hook paths и stamp.

Установка полного experimental snapshot по Git ref поддерживается CLI:

```bash
codex plugin marketplace add JesusLeto/qtim-agent-team-codex --ref experiment/qtim-feature-spec
codex plugin add qtim@qtim-agent-team
```

Эти команды меняют выбранный marketplace/plugin snapshot на машине. Выполняй их
намеренно для обкатки; при конфликте уже зарегистрированного источника сначала
прочитай `codex plugin marketplace list` и `codex plugin marketplace add --help`.
Не выдавай обычный default-branch snapshot за experimental. Проверь версию через
`codex plugin list` и manifest установленного qtim.

После установки открой новую задачу Codex на Astra/Ultra в worktree проекта.
Для существующей команды выполни `$qtim-update`: review показанного managed diff,
сохранение manual/model overrides и legacy документов. Если команды нет —
`$qtim-setup` с PM track. После изменения agent TOML открой ещё одну новую задачу:
уже открытая задача не перезагружает custom roles. PM должен иметь read-only reviewer
с SPEC_REVIEW; наличие reviewer само по себе не добавляет dev track.

## Пробный запуск

```text
$qtim-feature, <идея и ссылки на требования>.
Работаем по experimental one-spec процессу. Сначала планирование;
реализацию запущу после проверки спецификации и handoff.
```

Ожидаемый результат — один `docs/features/<slug>/spec.md`. Сопоставь наблюдаемые
действия с условиями ниже; автоматические repository checks проверяют структуру,
а эти условия требуют настоящей сессии:

- интервью закрывает решения; факты из кода агент выясняет самостоятельно;
- scope, AC, решения, один WI-план и gates находятся в одном spec;
- независимый SPEC_REVIEW выполняется без истории автора и с read-only sandbox;
- есть один полный pass, максимум один fix/recheck; итог содержит evidence и revision;
- build/tests/browser до реализации не запускаются только ради ревью документа;
- approval относится к проверенной текущей ревизии; handoff не запускает реализацию сам;
- pointer в memory/decisions.md завершает handoff; повторный вызов не повторяет интервью;
- реальная semantic delta открывает только затронутые решения; rename агента или
  compaction не обнуляет review budget;
- последующая реализация использует актуальные receipts вместо второго identical gate.

При недоступном reviewer состояние UNAVAILABLE не считается PASS. Явное owner
waiver — отдельное ручное исключение с причиной/риском, а не successful review.

## Что сохранить для корректировки

Сохрани session ID, spec, revision/verdict, подтверждённые findings и указатели на
receipts. Для каждого лишнего повторения достаточно: действие -> неизменные входы
-> прежний результат -> зачем повторилось. Секреты, raw auth data и чужой диалог
в feedback не копируются. Поправки вносятся в экспериментальную ветку.

## Возврат и критерий слияния

Верни marketplace на default branch и переустанови stable qtim через штатные CLI
команды, затем открой новую задачу. `$qtim-update` не делает downgrade generated
state: основной проект сохраняет исходную `.codex`, экспериментальный worktree
можно оставить для анализа. Если мигрировал основной проект намеренно, возвращай
его generated state из заранее сохранённой копии, сохраняя последующие ручные изменения.

В main ветку изменение переносится только после отдельного решения владельца:
реальная задача прошла planning/review/handoff и реализацию, замечания исправлены,
required repository checks пройдены, version/migration notes отражают итоговый
стабильный контракт. Создание экспериментальной ветки или Draft PR не означает
такого решения.
