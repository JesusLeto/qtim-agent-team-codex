# qtim — команда Codex-субагентов и missions под твой проект

Плагин для Codex, который разворачивает в проекте **команду специализированных subagents**: архитектор, database/backend, frontend, tester, reviewer и дополнительные роли под зрелые продукты. Вместо одного ассистента-универсала ты получаешь воспроизводимый workflow: проектирование, реализация, real-browser QA, ревью и фиксация решений в `memory/`.

qtim двух-ролевой: **разработчик** получает dev-команду с ограниченными циклами implement -> test -> review, **PM/аналитик** — риск-пропорциональный `$qtim-feature`: короткий feature brief для простой хотелки или полный PRD -> grounded decomposition -> plan с оценкой по запросу. Роли уживаются в одном проекте.

qtim подстраивается под стек проекта: анализирует репозиторий, задаёт несколько вопросов (первый — твоя роль) и генерирует Codex custom agents под реальные фреймворки, команды и инварианты.

## Что это даёт

- **Разделение труда** — роли отвечают за свои слои: архитектура, данные, UI, тесты, ревью.
- **PM-трек без фиксированного налога** — `$qtim-feature` выбирает fast-path `feature-brief.md` для S/M одной фазы без развилок или полный трек; estimate строится по запросу, consult зовёт только владельцев затронутых слоёв, после PRD можно завершить планирование.
- **Встроенные дисциплины** — `$qtim-debug-loop` для сложных багов, `$qtim-prototype` для дизайн-развилки, `$qtim-brainstorm` до ADR, `$qtim-grill` для stress-test плана и `$qtim-minimal-diff` для минимального полноценного объёма решения поставляются самим плагином и доступны любой роли.
- **Продуктовая память** — `$qtim-product-onboard` собирает из кодовой базы карту разделов, модель акторов, словарь домена и реестр событий аналитики (плюс материалы ПМа из `docs/product-context/`, если есть) — intake и PRD опираются на факты, а не на пересказ.
- **Актуализация базы знаний** — `$qtim-kb-refresh` проверяет устаревшие ссылки памяти по выбранной Git-базе, инвентаризует артефакты фич, ограничивает объём работы и сверяет потери после записи; `$qtim-kb-format` задаёт компактный формат новых фактов.
- **Codex-native упаковка** — плагин состоит из `.codex-plugin/plugin.json`, `skills/`, custom-agent templates и plugin-bundled Codex hooks; project `PostToolUse` остаётся опциональным.
- **Подстройка под стек** — setup создаёт `.codex/team-charter.md` и `.codex/agents/*.toml` под проект.
- **Контроль качества** — встроены gates: typecheck/build/tests, real-browser evidence, risk-based review кода и обязательный clean-context Sol stress-test каждого ADR до approval. Повторные проверки ограничены и расширяются при изменении поверхности риска.
- **Гибкие режимы** — `$qtim-team-lazy` для точечных задач и `$qtim-team-up` для эпиков с циклами implement -> test -> review.
- **Cross-dialog mission** — явный `$qtim-mission` координирует несколько видимых
  задач Codex App как проверяемый DAG: read-only analysis, bounded node-local lazy
  team и isolated writer worktrees сходятся через transactional topological
  integration: affected gate проходит до `--ff-only` promotion, затем отдельный
  clean-context verifier закрывает mission.

`$qtim-minimal-diff` не означает «сделать меньше требований». Brainstorm
формирует варианты, prototype проверяет развилку одноразовым артефактом, а
minimal-diff выбирает объём решения, которое останется в проекте. Согласованный
scope, trust-boundary validation, защита данных, security/access, базовая
accessibility и документированные инварианты не сокращаются.

## Требования

Нужен Codex с поддержкой plugins, skills и subagents. Отдельный флаг Claude Agent Teams не нужен.

qtim запускает subagent workflow только по явной просьбе или вызову соответствующего skill. Основную задачу для qtim открой на `gpt-5.6-sol` + `Ultra`: main thread остаётся team-lead и получает proactive delegation внутри уже разрешённого scope. Плагин не переключает уже открытую задачу скрыто, не расширяет scope и не поднимает рекурсивные команды из child agents.

Full `$qtim-mission` требует callable peer-task tools Codex App. На CLI/IDE без
этой surface skill честно предлагает `$qtim-team-up` как single-task fallback.
Writer mode дополнительно требует callable follow-up control: задача сначала
возвращает no-edit READY, coordinator снимает baseline всей wave и только exact
follow-up разрешает запись. Также нужны отдельные clean integration/state worktrees, Approved
base/integration target и отдельный worktree на node; portable mission evidence
получает scoped checkpoint commits в state branch. Dirty state, scope violation, lost
handle, conflict и exhausted budget блокируются fail-visible; auto-stash, force
overwrite и auto-archive запрещены.

## Модели и reasoning

В qtim 2.13.0 оркестратор и роли разведены по явным GPT-5.6 профилям:

| Роль | Model / reasoning |
|---|---|
| main team-lead | `gpt-5.6-sol` + `ultra` |
| architect, reviewer | `gpt-5.6-sol` + `xhigh` |
| database, frontend, product | `gpt-5.6-sol` + `high` |
| testing | `gpt-5.6-terra` + `medium` |
| built-in explorer | `gpt-5.6-luna` + `medium` |
| clean-context ADR adversary | `gpt-5.6-sol` + `xhigh`; `max` для необратимого решения, задевающего инвариант |

Ролевые пары атомарны: `model` и `model_reasoning_effort` задаются вместе. Setup/update сверяет exact slug с runtime catalog, не угадывает alias и сохраняет пользовательские overrides через diff-подтверждение. Если pair недоступна, миграция остаётся pending до обновления Codex или подтверждённого override.

Каждый ADR получает два прохода: `$qtim-grill` и независимого read-only Sol-оппонента в новом thread без истории. Результат остаётся в самом ADR строкой `adr-stress-test: ...`; этот design gate работает даже когда optional risk-based review кода выключен.

## Установка

Из GitHub marketplace-репозитория:

```bash
codex plugin marketplace add JesusLeto/qtim-agent-team-codex
codex plugin add qtim@qtim-agent-team
```

Локально из клона репозитория:

```bash
codex plugin marketplace add .
codex plugin add qtim@qtim-agent-team
```

После установки открой новую задачу Codex, чтобы она подхватила skills плагина.

## Обновление и версии

Обновить сам плагин (Git-marketplace):

```bash
codex plugin marketplace upgrade qtim-agent-team   # обновить snapshot маркетплейса
codex plugin add qtim@qtim-agent-team              # переустановить плагин
```

После переустановки открой новую задачу Codex — только она подхватит обновлённые skills.

Обновить команду в проекте: `$qtim-update` — сверяет версию установленного плагина с версией сгенерированной команды и мигрирует `.codex/team-charter.md`, `.codex/agents/*.toml` и qtim-owned hooks по upgrade notes, сохраняя пользовательские hook groups, соседний track, ручной текст и atomic model overrides. Неоднозначный target остаётся `pending`, а stamp повышается только после полного version-step.

Если `$qtim-update` изменил `.codex/agents/*.toml`, после миграции открой ещё одну новую задачу Codex перед `$qtim-team-up`, `$qtim-team-lazy` или `$qtim-feature`: уже открытая задача не перезагружает custom-agent definitions на лету.

Если изменились hooks, открой `/hooks` и заново review/trust изменённые definitions.

Где смотреть версии:

- плагин — `codex plugin list`;
- команда в проекте — stamp `<!-- qtim-version: ... -->` первой строкой `.codex/team-charter.md` (plugin-bundled SessionStart показывает её при старте сессии);
- `$qtim-update` печатает обе версии и вердикт.

## Быстрый старт

1. Открой Codex в корне своего проекта — в ChatGPT desktop app, CLI или IDE extension.
2. Разверни команду (первым вопросом setup спросит твою роль: Developer, PM/Analyst или обе):

   ```text
   $qtim-setup
   ```

3. После setup используй режим под задачу:

   ```text
   $qtim-onboard          # dev: один раз наполнить память картой, инвариантами и конвенциями
   $qtim-product-onboard  # PM: один раз собрать продуктовую память из кода
   $qtim-kb-refresh       # актуализировать память и артефакты фич по проверенному diff
   $qtim-feature          # PM: fast brief или полный PRD -> decomposition -> plan
   $qtim-mission          # App: видимый DAG, writer worktrees, integration + verification
   $qtim-team-up          # полный эпик с циклами implement -> test -> review
   $qtim-team-lazy        # роли по мере надобности
   $qtim-team-retro       # после эпика: дистиллировать уроки в память
   $qtim-team-down        # закрыть активные agent threads и зафиксировать память
   $qtim-debug-loop       # сложный баг: красный repro -> гипотезы -> тест -> фикс
   $qtim-minimal-diff     # перед нетривиальным решением: минимальный полноценный объём
   $qtim-brainstorm       # варианты и trade-offs до ADR/design brief
   ```

## Skills

| Skill | Когда использовать |
|---|---|
| `$qtim-setup` | Один раз в новом проекте: выбрать роль, сгенерировать charter, custom agents и memory; при выборе добавить optional project PostToolUse |
| `$qtim-feature` | PM/аналитик: выбрать fast-path brief или полный grounded pipeline и подготовить handoff |
| `$qtim-mission` | Явно запустить Approved DAG видимых Codex App задач: read-only/lazy/writer nodes, topological integration, bounded verification/fixes и `status/resume/stop` без auto-archive |
| `$qtim-team-up` | Крупная задача/эпик с обратной связью между implement/test/review |
| `$qtim-team-lazy` | Быстрая или средняя задача без полного прогрева команды |
| `$qtim-onboard` | После setup на существующей кодовой базе: наполнить dev-память картой, инвариантами и конвенциями с устойчивыми `path#Symbol` |
| `$qtim-product-onboard` | После setup с PM-дорожкой: собрать продуктовую память из кода — разделы, акторы, словарь домена, события аналитики |
| `$qtim-kb-refresh` | Проверить дрейф `memory/` от выбранной Git-базы, инвентаризовать `docs/features/`, ограниченно обновить устаревшее и проверить отсутствие потерь |
| `$qtim-kb-format` | При записи базы знаний: сжатые факты, устойчивые ссылки на код и проверяемый `checked` |
| `$qtim-team-retro` | После завершённого эпика (до team-down): дистиллировать уроки и классифицировать epic-scoped `minimal-diff:` markers; durable follow-up создаётся только для доказанно сработавшего trigger |
| `$qtim-team-down` | Завершить активные agent threads и сохранить durable state; незавершённый эпик фиксируется в `memory/epic-state.md` |
| `$qtim-doctor` | «Что-то не работает» или после обновления: read-only диагностика charter/агентов, hooks, памяти и advisory roster drift (`repository signal -> responsibility gap -> safe action`) |
| `$qtim-update` | Проверить версии плагина/команды и мигрировать сгенерированные файлы на текущую версию |
| `$qtim-debug-loop` | Нетривиальный/плавающий баг или perf-регрессия: воспроизводимый красный сигнал, 3-5 гипотез, inventory root seam/call sites и coverage gaps до фикса, regression test, cleanup |
| `$qtim-minimal-diff` | Перед нетривиальным design/implementation или новой абстракцией/зависимостью: семь ступеней до минимального полноценного решения, protected zones и одна минимальная breaking check для нетривиальной логики |
| `$qtim-prototype` | Разрешить UX/behavior-развилку одноразовым терминальным или UI-прототипом |
| `$qtim-brainstorm` | До ADR/design brief: интерпретации, факты, 2-3 жизнеспособных варианта, trade-offs и open questions |
| `$qtim-grill` | Стресс-тестировать нетривиальный план по одному вопросу с рекомендованным ответом или в self-play |

## Что появится в проекте после setup

- `.codex/team-charter.md` — контракт команды с track-блоками под выбранные роли, инварианты и правила работы.
- `.codex/agents/*.toml` — Codex custom agents под стек проекта (включая `qtim-product` для PM-трека).
- `.codex/hooks.json` — создаётся только для явно выбранного project `PostToolUse` или сохраняет уже существующие пользовательские hooks; `SessionStart` / `SubagentStop` поставляет плагин.
- `memory/` — карта проекта, команды, решения, инварианты, баги и review reports; при работе команды сюда добавляются `epic-state.md` (handoff незавершённого эпика между сессиями), `retro-log.md` и `lessons.md` (уроки ретроспектив). Retro поднимает только доказанно сработавшие epic-scoped `minimal-diff:` markers в durable follow-up с source, trigger evidence, owner и next action.
- `memory/missions/<slug>/` — появляется при `$qtim-mission`: portable spec,
  validated/integrated receipts, локальные решения и final verification;
  opaque runtime handles остаются в gitignored `.codex/qtim-runtime/`.
- `AGENTS.md` — указатель для Codex на qtim-команду и локальные правила проекта.
- `docs/features/<slug>/` — появляется при `$qtim-feature`: `intake.md` + единый fast-path `feature-brief.md` или полный трек PRD/decomposition/plan с условным `estimate.md`; PRD-only может быть конечным результатом.

## Как это выглядит

```text
Ты:   $qtim-team-up, добавь раздел избранного: БД, API и UI
qtim: architect проектирует -> database делает схему -> frontend пишет UI ->
      testing проверяет браузером -> reviewer даёт APPROVED / NOT APPROVED
Ты:   получаешь результат, verification summary и обновлённую память проекта
```

PM/аналитик:

```text
Ты:   $qtim-feature, хотим избранное для товаров
qtim: intake + выбор трека -> для простой версии один feature-brief и один checkpoint;
      при развилках — PRD -> selective dev-consult -> decomposition -> plan
      (оценка по необходимости; после PRD можно завершить как PRD-only)
Ты:   получаешь docs/features/favorites/ и topology-based команду direct,
      $qtim-team-lazy, $qtim-team-up или $qtim-mission
```

Cross-dialog mission:

```text
Ты:   $qtim-mission, запусти Approved план: A (lazy) проверяет контракт,
      B в worktree реализует его после validated A, C проверяет integrated revision.
qtim: A агрегирует локальные роли -> coordinator проверяет B no-edit READY
      и даёт exact follow-up -> B возвращает
      scoped commit -> cherry-pick в transaction worktree -> affected gate -> ff-only promotion ->
      clean-context C -> APPROVED / NOT APPROVED
Ты:   видишь все peer tasks; можешь вызвать status, resume или stop без auto-archive
```

## Лицензия

MIT. Уведомления для адаптированных bundled disciplines — в [`plugins/qtim/THIRD_PARTY_NOTICES.md`](plugins/qtim/THIRD_PARTY_NOTICES.md).
