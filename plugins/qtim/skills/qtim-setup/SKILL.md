---
name: qtim-setup
description: Use when the user wants to install or bootstrap qtim for the current Codex project. Asks for the user role, then generates charter, custom agents, memory, a platform-loaded qtim contract in AGENTS.md, optional blocking screenshot policy, and only when selected a project-local PostToolUse hook without duplicating plugin-bundled hooks.
---

# qtim Setup For Codex

Ты bootstrap-инженер qtim для Codex. Твоя задача — развернуть в текущем проекте Codex-native команду субагентов: charter, custom agents, memory baseline, автоматически загружаемый qtim contract в `AGENTS.md`, optional blocking screenshots gate и optional project PostToolUse. Plugin-bundled lifecycle hooks не копируй.

Не создавай legacy `.claude/*`, не пиши `CLAUDE.md`, не используй legacy Agent Teams primitives. Codex-цель — `.codex/*`, `AGENTS.md`, skills и Codex subagent workflows.

## Plugin Resources

Перед генерацией прочитай только нужные ресурсы:

- Role templates: `../../agents/architect.toml`, `../../agents/database.toml`, `../../agents/frontend.toml`, `../../agents/testing.toml`, `../../agents/reviewer.toml`, `../../agents/product.toml`.
- Model policy: `../../reference/model-profiles.md`.
- Shared mechanics: `../../reference/intake-protocol.md`, `../../reference/orchestration-patterns.md`, `../../reference/independent-review.md`, `../../reference/feature-pipeline.md`.
- Bundled disciplines: `../qtim-debug-loop/SKILL.md`, `../qtim-prototype/SKILL.md`, `../qtim-brainstorm/SKILL.md`, `../qtim-grill/SKILL.md`, `../qtim-minimal-diff/SKILL.md`; role templates invoke them directly. Перед генерацией `memory/` прочитай `../qtim-kb-format/SKILL.md`.
- Hooks: `../../hooks/hooks.json` для plugin-bundled событий; `../../reference/project-hooks.json` читай только при выборе project-level `PostToolUse`.
- Plugin version для stamps: поле `version` из `../../.codex-plugin/plugin.json`.

## Phase 1: Discovery

Сначала только читай проект. Не записывай файлы и не задавай вопросов.

Собери за 5-10 tool calls:

- root structure: `ls -la`;
- top-level `AGENTS.md`, `README.md`, legacy `CLAUDE.md` if present;
- package/workspace markers: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, `composer.json`;
- frontend/backend/database/test/CI markers;
- commands: dev, build, typecheck, test, migrations;
- existing `.codex/agents`, `.codex/hooks.json`, `.codex/team-charter.md`, `memory/`; существующий hooks-файл классифицируй как canonical, legacy qtim или foreign/mixed, ничего не исполняя;
- existing `docs/features/` и track-маркеры `qtim:track:dev` / `qtim:track:pm` в существующем charter.

Сведи placeholders role templates к фактам проекта:

- `{{FRONTEND_FRAMEWORK}}`
- `{{BACKEND}}`
- `{{DATABASE}}`
- `{{FILE_STORAGE}}`
- `{{BUILD_CMD}}`
- `{{DEV_CMD}}`
- `{{TYPECHECK_CMD}}`
- `{{TEST_RUNNER}}`
- `{{E2E_TOOL}}`

Если технологии нет, вырежи стек-условные требования из соответствующего agent template при генерации.

## Phase 1b: Codex Skills, Plugins, MCP Matching

Layer 0 уже поставляется qtim и доступен во всех проектах: `$qtim-debug-loop`, `$qtim-prototype`, `$qtim-brainstorm`, `$qtim-grill`, `$qtim-minimal-diff`, `$qtim-kb-format`. Не проверяй их как внешние зависимости, не проси установить и не вписывай в колонку optional `skills`. `$qtim-kb-format` нужен только при записи `memory/` или `docs/features/`; он не добавляет отдельный gate к реализации. `$qtim-kb-refresh` вызывается вручную при устаревшей памяти, а не после каждого изменения кода.

В mandatory practices charter зафиксируй единый contract:

- architect — `$qtim-brainstorm` до ADR, `$qtim-minimal-diff` при сравнении design-вариантов и обязательный clean-context Astra stress-test каждого созданного ADR;
- database/frontend — `$qtim-minimal-diff` до нетривиальной реализации и `$qtim-debug-loop` для нетривиального бага;
- testing — `$qtim-debug-loop` для flaky repro;
- reviewer — ревью результата по `$qtim-minimal-diff`: чистая избыточность идёт в рекомендации, а scope/protected-zone/invariant/gate violations остаются blockers;
- любая дополнительно сгенерированная роль, которая пишет код (например devops или impl-роль нестандартного стека), — `$qtim-minimal-diff` до нетривиальной реализации; read-only/product/explorer роли эту practice не получают автоматически.

Prototype/grill остаются условными инструментами architect; `$qtim-grill` — первый pass только при созданном ADR, не замена независимому adversary. Minimal-diff не сокращает согласованный scope, protected zones или verification gates и не вводит собственную схему отчёта.

Отдельно подбери уже доступные внешние Codex skills из текущего контекста под стек и роли. Не устанавливай ничего сам.

Приоритеты:

- frontend: frontend/design/framework skills;
- backend/API: backend/API/security/error-handling skills;
- database: database/query/security skills;
- testing: browser/e2e/accessibility skills;
- reviewer: code review/security/performance skills.

Плагины и MCP только рекомендуй в финале. Для приватных систем и live-data источников предпочитай Codex connectors/MCP вместо веб-поиска.

Best-effort проверь exact model pairs role templates по локальному catalog, который показывает текущий Codex (`codex debug models`, если команда доступна, или model controls текущего runtime). Не делай сетевой lookup частью setup. Pair недоступна -> предложи обновить Codex или подтвердить catalog-supported override; не удаляй поля и не переходи на inheritance молча. Catalog недоступен -> пометь pair `unverified` в плане и попроси подтверждение перед генерацией.

## Phase 2: Decisions

Задай пользователю короткий набор вопросов. Если доступен структурированный question tool, используй его; иначе спроси обычным сообщением и дождись ответа.

**Первый вопрос — роль пользователя:**

- **Developer** — команда разработки: architect/database/frontend/testing/reviewer, workflow `$qtim-team-up` / `$qtim-team-lazy`;
- **PM/Analyst** — продуктовый трек: роль `qtim-product`, независимый read-only reviewer и `$qtim-feature`: интервью -> один spec с SPEC_REVIEW -> одно approval -> handoff;
- **Оба** — обе дорожки в одном charter.

Роль гейтит остальные вопросы. Если charter уже существует и содержит только другой track, предложи дописать недостающий track, не пересоздавая существующий.

Нужные решения (Developer и Оба — полный набор; PM/Analyst — только project name, autonomy, memory baseline, hooks):

- project name for charter;
- team shape: Compact, Standard, Extended (только dev track);
- autonomy: design approval first (default: Approved scope разрешает предусмотренные фазы), phase-by-phase confirmation только по явному выбору пользователя, or full autonomy; PM track использует одно финальное approval проверенной спецификации;
- memory baseline: project map, commands, safety, domain invariants;
- independent review gate: enabled or disabled (только risk-based code review dev track; disabled вырезает только CODE_REVIEW-требования, сохраняет обязательный SPEC_REVIEW PM track и ADR stress-test; включить code review позже — повторный `$qtim-setup`);
- hooks: plugin-bundled `SessionStart` / `SubagentStop` уже поставляются qtim и управляются через `/hooks`; отдельно спроси про optional project-level `PostToolUse` reminder после edits;
- screenshots gate: advisory по умолчанию или blocking opt-in. При blocking зафиксируй repo-relative каталог скриншотов; plugin-bundled `SubagentStop` вернёт `qtim-testing` в работу максимум один раз, если свежих tester-снимков нет. Для задачи без UI повторный stop пропускается;
- external skill recommendations: write selected stack skills into charter/agent instructions or keep roles standalone; bundled qtim disciplines не отключаются этой опцией.

PM/Analyst-состав определяется стеком: `qtim-product`, `qtim-architect`, профильные `qtim-database`/`qtim-frontend`/`qtim-testing` для read-only consult и `qtim-reviewer` для обязательного SPEC_REVIEW; broad search выполняет built-in `explorer`. Наличие роли не требует её запуска: main thread сам ведёт интервью и пишет одну spec, consult получает конкретный незакрытый вопрос. Reviewer в PM-only setup механически read-only и не зависит от code-review toggle. PM reviewer не означает готовность к разработке: перед team-up/lazy/mission implementation проверь dev track и нужных исполнителей; добавляй их повторным `$qtim-setup`, сохраняя существующие файлы.

Рекомендованный default для большинства fullstack проектов: Standard, design approval first, project map + commands + safety + invariants, independent review enabled, plugin-bundled SessionStart + SubagentStop enabled, screenshots gate advisory (blocking выключен), project-level PostToolUse disabled.

Модельный профиль не является отдельным обязательным вопросом: используй явную GPT-6 матрицу из `../../reference/model-profiles.md`. Team-lead workflow рассчитан на `gpt-6-astra` + `ultra`; setup не переключает уже открытый task, а фиксирует prerequisite в плане/charter и просит открыть новую задачу с этим профилем. Роли: architect/reviewer — Astra+xhigh; database/frontend/product — Sol+high; testing — Luna+medium; built-in explorer — Luna+medium. Спрашивай только при пользовательском override или недоступности exact pair.

## Phase 3: Plan Confirmation

Покажи компактный план до записи файлов:

- detected stack and project name;
- selected tracks (dev / pm / оба) и что будет добавлено или обновлено между track-маркерами charter, а что останется нетронутым;
- files to create or update;
- selected roles and custom agent filenames;
- обязательный language contract: internal reasoning и сообщения peer agents — на English, любой user-facing output — на Russian;
- main-thread prerequisite `gpt-6-astra` + `ultra`, model/reasoning pair каждой роли и clean-context ADR adversary (Astra+xhigh; max для необратимого + инвариант), плюс план при недоступной pair;
- memory files только с подтверждённым содержимым; `$qtim-kb-format` как условное правило записи и `$qtim-kb-refresh` для обнаруженного дрейфа;
- plugin-bundled hooks, режим screenshots gate и отдельно optional project `PostToolUse`;
- selected external skills per role и гарантированные qtim disciplines в mandatory practices;
- any collisions in existing `.codex/agents` or `memory/`;
- при re-run — какие поддерживаемые роли/managed practices будут добавлены или точечно обновлены, какие существующие роли, соседний track, ручной текст и atomic model overrides останутся без изменений.

Ничего не записывай до явного подтверждения пользователя. Если пользователь просит правки, обнови план и переспроси.

## Phase 4: Generation

### `.codex/team-charter.md`

Первой строкой charter поставь version stamp с версией плагина: `<!-- qtim-version: <semver> -->`. По нему `$qtim-update` и SessionStart hook определяют версию команды.

Создай проектный контракт команды. Общие секции (вне track-блоков):

- purpose and project context;
- fixed stack and commands;
- roles table: role, Codex custom agent name, mission, triggers, do-not-touch, read-on-start, external skills, mandatory practices; bundled practices из Layer 0 записываются по ролям, но не смешиваются с optional external skills. Значения minimal-diff возьми из Phase 1b: design-варианты у architect, решение до реализации у code-writing roles, recommendation-only review у reviewer;
- model matrix отдельным блоком под roles table: team-lead `gpt-6-astra` + `ultra`; architect/reviewer `gpt-6-astra` + `xhigh`; database/frontend/product `gpt-6-sol` + `high`; testing `gpt-6-luna` + `medium`; built-in explorer `gpt-6-luna` + `medium`; ADR adversary `gpt-6-astra` + `xhigh` (`max` для необратимого решения, затрагивающего документированный инвариант). Для ролей с TOML источником истины служит файл; для explorer и ephemeral adversary — charter;
- отдельный общий блок `## Language` вне track markers с дословным обязательным правилом: `Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.`;
- domain invariants;
- ADR stress-test — отдельный обязательный блок независимо от настройки code review: каждый ADR до approval проходит `$qtim-grill`, затем новый read-only thread без истории на Astra+xhigh; необратимое + документированный инвариант -> Astra+max; итоговая строка `adr-stress-test:` в ADR, технический пропуск записывается как `skipped` и не считается pass;
- independent code-review gates — при включённом гейте перенеси в charter без сокращений canonical high-risk matrix из `../../reference/independent-review.md`: security/auth/tenant-scope visibility; money/billing/account state; documented domain invariants/public contracts; data-transform/destructive migrations; critical browser flows; high-risk performance/reliability; другое доказанно hard-to-rollback изменение. Добавь bounded review contract: первый reviewer pass на фазу, максимум два fix-and-recheck раунда, затронутые проверки и full rerun только при изменении risk surface или расширении поведения за пределы проверенного diff; обязательный security review сохраняется. При выключенном — секция из одной строки-заглушки «independent review кода выключен (выбор setup); включить — повторный `$qtim-setup`». Рядом явно напиши, что ADR stress-test и SPEC_REVIEW PM track остаются включены;
- working rules: qtim subagent workflows авторизуются явным вызовом skill или прямой просьбой, а сами subagents остаются task-scoped agent threads без скрытой постоянной команды; team-lead работает на Astra+Ultra и может делегировать внутри разрешённого scope, но не меняет execution depth A/B/C/D и не разрешает child agents рекурсивно поднимать команду; main thread проверяет доступные descendants перед повторным spawn и уважает runtime thread cap; qtim не переключает модель/reasoning уже открытого task; Approved plan авторизует последующие фазы без повторных стартовых запросов, кроме явно выбранного phase-by-phase режима и новых существенных развилок; явные ограничения пользователя и Approved scope старше рекомендаций review, blocker вне scope требует решения владельца; use custom agents when loaded, otherwise `worker` fallback with inline role instructions, а built-in `explorer` spawn с Luna+medium; mission — отдельный App-first workflow, где только coordinator создаёт peer tasks и владеет DAG/runtime/integration/final verdict, Approved lazy node получает ровно один local `$qtim-team-lazy` level, writers работают в отдельных worktrees и возвращают один commit; topological integration выполняется так: coordinator cherry-pick-ит commit в disposable transaction worktree, запускает affected gate и только затем под exclusive promotion lock повторно проверяет exact old HEAD, делает ff-only и final-head check в отдельном clean integration worktree; portable evidence получает scoped checkpoint commits в отдельной state worktree и доставляется final bundle commit после APPROVED, resume требует единственного owner/generation; status/resume/stop fail-visible, SessionStart только advisory, auto-archive запрещён; session handoff: незавершённый эпик фиксируется в `memory/epic-state.md` (`$qtim-team-down` пишет, `$qtim-team-up` читает и предлагает продолжить), уроки retro — в `memory/retro-log.md` и `memory/lessons.md`; при записи `memory/` или `docs/features/` используется `$qtim-kb-format`, при обнаруженном дрейфе предлагается `$qtim-kb-refresh`; runtime assumptions проверяются по `../../reference/runtime-compat.md`, но plugin-internal путь в generated charter не переносится;
- verification evidence: один owner каждого gate, сначала проверь существующий receipt и живой процесс; сравни реальные relevant inputs (код/tests/config/lock/fixtures), command/scope и platform/toolchain/backend/SFU environment. PASS переиспользуется при неизменных входах, новый факт требует затронутой проверки. Whole build не нужен только из-за test teardown или текста отчёта. Process handle/liveness/unique log/cleanup остаются task-local; input-релевантность неясна — повтори affected gate. Одна корректная clean-context code-review может закрывать phase и risk gate; money-critical две трассы сохраняются; внешние пользовательские правила review имеют приоритет.
- memory layout: read-first пути в `memory/` условны, если файла ещё нет;
  `decisions.md`, `review-report.md` и `bug-log.md` создаются только при первой
  реальной записи по `$qtim-kb-format`, не как пустые шаблоны.

Track-блоки — между HTML-маркерами, по выбранным ролям:

```text
<!-- qtim:track:dev:start -->
...dev track: intake/autonomy mode, специфичные dev-правила...
<!-- qtim:track:dev:end -->

<!-- qtim:track:pm:start -->
...pm track: feature pipeline...
<!-- qtim:track:pm:end -->
```

PM track block начни пометкой: «Производная self-contained сводка; долговечный канон артефактов принадлежит установленному `$qtim-feature` reference, ручные изменения сверять через `$qtim-update`». Перенеси компактный self-contained контракт из `../../reference/feature-pipeline.md` и SPEC_REVIEW из `../../reference/independent-review.md`:
- интервью -> одна `docs/features/<slug>/spec.md` -> независимый SPEC_REVIEW -> одно approval -> handoff; main thread — единственный редактор, consult только по незакрытым фактам;
- одна таблица вертикальных work items: AC, DRI, contributing роли/слои, файлы, существенные зависимости и стабильная граница review; expand-contract для широкого rename/retype, оценка только по запросу;
- `Revision`, `Reviewed revision`, `Approved revision`, `Review verdict`; semantic revision охватывает scope/AC/решения/границы WI/gates/rollback/handoff, status и receipts её не повышают; новая семантика возвращает Draft, принятые решения пересматриваются только по новым фактам;
- SPEC_REVIEW: отдельный clean-context read-only `qtim-reviewer`, Astra+xhigh или подтверждённый atomic override; spec, источники требований и инварианты без истории автора; `READY_FOR_APPROVAL`/`CHANGES_REQUESTED`, одна полная проверка и один fix-recheck, budget не сбрасывается при resume; build/tests/browser до реализации не запускаются. Подтверждённый blocker или недоступный reviewer блокирует готовность, исключение только явное recorded owner waiver без ложного PASS;
- handoff требует проверенной текущей ревизии и её approval, готового блока `Что запускать дальше`; recommendation ничего не запускает. Topology выбирает direct / `$qtim-team-lazy` / `$qtim-team-up` / `$qtim-mission`; отдельный mission preview сохраняется. Dev readiness проверяется по dev track/исполнителям, не по наличию PM reviewer;
- указатель на spec в `memory/decisions.md` пишется последним completion marker; отсутствующий указатель означает resume handoff без нового интервью/review. Status: Draft -> Approved -> In Development -> Done -> Archived; Done после acceptance/gates, Archived после merge evidence и решения владельца;
- результаты и process handles временно в `.work/`, один `.work/validation.md` с gate/scope/input fingerprint/environment/result/log/limits; reuse только подходящего evidence, UNKNOWN не PASS; `.work/` игнорируется. Raw logs/handles не копируются в memory или spec;
- legacy `intake.md`/`prd.md`/`decomposition.md`/`plan.md`/`estimate.md`/`feature-brief.md` остаются readable и не удаляются/конвертируются setup/update. При mixed sources требуется явное `Canonical: spec.md`; конфликт не разрешается по имени или дате файла.

Переход `Done -> Archived` и удаление `.work/` требуют evidence влития и
решения владельца, если оно ещё не дано в сессии. Одно сворачивание команды
не запускает очистку; `Done` остаётся допустимым статусом до архивации.

Re-run rule: при повторном setup заменяй содержимое только между маркерами своего track; чужой track block и ручные правки пользователя вне маркеров не трогай. В общей roles table добавляй недостающие поддерживаемые роли и точечно дополняй распознанные qtim-owned mandatory-practice cells; неизвестные строки, дополнительные колонки и ручной текст сохраняй. Роли не удаляй. Неоднозначную строку или локально изменённый managed block покажи как collision/pending в плане, не угадывай и не заменяй весь charter.

### `.codex/agents/*.toml`

Для каждой выбранной роли создай custom agent TOML из template. Первой строкой каждого сгенерированного файла добавь комментарий `# qtim-version: X.Y.Z` с версией плагина. Каждый файл должен иметь:

- `name`;
- `description`;
- `developer_instructions`;
- optional `model`, `model_reasoning_effort`, `nickname_candidates`, `sandbox_mode`.

**Model policy копируй из template дословно, не подставляй значения из собственных знаний.** Все постоянные роли имеют явную atomic pair. Переопределяй только по явному выбору пользователя; override всегда задаёт оба поля. Если catalog не подтверждает template pair, не угадывай замену и не удаляй pair молча: покажи проблему и предложи обновить Codex либо подтвердить catalog-supported override/fallback. Одинокий model/reasoning, `model = "inherit"`, догаданный alias вроде `gpt-6`, `ultra` в role TOML или `service_tier = "fast"` без явного выбора запрещены.

**Language contract копируй из template дословно.** Блок `## Language` не stack-conditional и не gate-conditional: не вырезай его при compact/PM-only setup, отключённом independent review или пользовательском model override.

**Gate-условные блоки шаблонов:** code-risk блоки «Independent review gate», canonical high-risk matrix и code-отчёт «Independent review» переноси только при включённом code gate. При disabled вырезай только эти CODE_REVIEW строки. SPEC_REVIEW, его read-only/clean-context границу, fail-closed готовность и budget никогда не вырезай; ADR stress-test тоже сохраняется независимо от toggle. Reviewer получает оба режима, PM track использует SPEC_REVIEW.

Имена по умолчанию:

- `qtim-architect`;
- `qtim-database`;
- `qtim-frontend`;
- `qtim-testing`;
- `qtim-reviewer`;
- `qtim-product` (PM track).

Состав по трекам: Developer — architect/database/frontend/testing/reviewer по team shape; PM/Analyst — product/architect, профильные consult-роли по стеку и read-only reviewer для SPEC_REVIEW; Оба — объединение без дублей. Explorer встроен в Codex, отдельный TOML не нужен; main thread передаёт `gpt-6-luna` + `medium`. Devops/auditor — узкие custom roles при выбранном Extended.

В self-contained `developer_instructions` любой code-writing custom role без
bundled template добавь тот же minimal-diff contract: `$qtim-minimal-diff` до
нетривиальной реализации, protected zones и approved scope не сокращаются,
спорный scope возвращается main thread, нетривиальная логика получает одну
минимальную breaking check без новой test infrastructure. Read-only auditor,
product и explorer этот implementation block не получают.
Каждая custom role без bundled template независимо от responsibility получает
дословный `## Language` contract; это правило не `not applicable` для read-only,
product или auditor роли.

При re-run недостающий файл поддерживаемой роли создавай только после показанного plan/approval. Существующий TOML не удаляй и не заменяй целиком: покажи scoped diff, сохрани подтверждённую atomic model pair и ручные инструкции вне распознанного qtim-owned region; при неоднозначности оставь collision/pending. Setup не переименовывает роли и не создаёт дубликат для похожего имени без решения пользователя.

### `.codex/hooks.json`

Plugin-bundled `SessionStart` и `SubagentStop` не дублируй: Codex складывает plugin и project hook layers, поэтому копия даст двойной анонс/ремайндер или gate. Их канон — `../../hooks/hooks.json`.

Blocking screenshots gate тоже plugin-bundled и управляется отдельным generated config,
а не копией hook:

- по умолчанию `.codex/screenshots-gate.json` не создавай — reviewer остаётся advisory gate;
- при explicit opt-in создай `.codex/screenshots-gate.json`:

```json
{
  "mode": "blocking",
  "directory": "repo-relative/screenshots",
  "freshnessMinutes": 180
}
```

- `directory` только repo-relative и без `..`; absolute/machine-specific path запрещён;
- существующий config не удаляй при re-run без показанного diff и подтверждения;
- hook касается только `qtim-testing`, проверяет реальные image files, исключает
  `front-selfcheck-*` и использует `stop_hook_active`, поэтому блокирует максимум один раз.

Project `.codex/hooks.json` создавай только если пользователь выбрал optional `PostToolUse` или файл уже содержит пользовательские hooks. Для qtim `PostToolUse` дословно возьми matcher group из `../../reference/project-hooks.json`: это nested Codex schema `hooks -> PostToolUse[] -> hooks[] -> type: command`, а команда возвращает JSON `hookSpecificOutput.additionalContext`. Plain stdout у `PostToolUse` игнорируется.

При merge:

- сохраняй `description`, порядок и содержимое всех пользовательских events/groups/handlers;
- добавляй только отсутствующий qtim `PostToolUse` group, не заменяй весь event;
- не создавай `type: reminder`, поле `message` или плоский event array — Codex исполняет `type: command` внутри matcher group;
- legacy top-level events или qtim `type: reminder` нормализуй только после показанного в Phase 3 diff; неоднозначные пользовательские entries не переписывай без подтверждения;
- если optional `PostToolUse` не выбран и project hooks отсутствуют, `.codex/hooks.json` не создавай.

Codex hooks требуют trust review через `/hooks`; упомяни это в handoff.

### `.gitignore` для временного состояния

Убедись, что корневой `.gitignore` содержит ровно одну активную строку
`.codex/qtim-runtime/`. Если файла нет — создай только с этой строкой; если есть —
добавь строку, сохранив весь пользовательский текст и порядок. Уже tracked runtime
files не удаляй автоматически: покажи их и оставь cleanup пользователю.

Runtime registry хранит opaque thread/host/cursor handles и никогда не коммитится.
Portable `memory/missions/<slug>/` под это правило не попадает.
При PM track добавь одну строку `docs/features/**/.work/`: здесь живут только
временные процессные файлы фичи. Существующие tracked файлы не удаляй при
setup; покажи их в плане миграции.

### `memory/`

Создай `memory/MEMORY.md` как короткий индекс и только выбранные файлы с
подтверждённым содержимым по `$qtim-kb-format`:

- `memory/project-map.md`;
- `memory/commands.md`;
- `memory/safety.md`;
- `memory/invariants.md`;
- `memory/decisions.md`;
- `memory/review-report.md`;
- `memory/bug-log.md`.

Не создавай пустые шаблоны или ссылки индекса на несуществующие файлы.
`memory/decisions.md` — краткий реестр указателей, не пересказ ADR/фич.
Повторный setup обновляет проверенный факт на месте, а не добавляет вторую
версию. Метка `checked` меняется только после проверки файла целиком.

Файлы `memory/epic-state.md`, `memory/retro-log.md` и `memory/lessons.md` setup не создаёт — их создают `$qtim-team-down` и `$qtim-team-retro` по мере надобности; упомяни их назначение в `MEMORY.md`. Для `memory/retro-log.md` зафиксируй, что retro также пишет туда только доказанно сработавшие `minimal-diff:` follow-up с source, trigger evidence, одним owner и проверяемым next action. Каталог `memory/missions/<slug>/` setup также не создаёт: его заводит только явно запущенная mission через `$qtim-mission` с глаголом исполнения или недвусмысленную просьбу провести несколько Codex peer tasks как одну mission для portable spec, validated receipts, локальных решений и final verification.

При PM track уточни в `MEMORY.md`, что `decisions.md` служит также реестром указателей на утверждённые фичи в `docs/features/<slug>/`. Саму директорию `docs/features/` setup не создаёт — её создаёт `$qtim-feature` per-slug. Продуктовую память (`memory/product-map.md`, `product-actors.md`, `product-glossary.md`, `product-metrics.md`) setup тоже не создаёт — её наполняет `$qtim-product-onboard`; упомяни эти файлы в PM track block charter как read-on-start роли `product` («если созданы»).

### `AGENTS.md`

Если `AGENTS.md` есть, добавь секцию `Команда qtim`. Если нет — создай. Внутри неё
qtim-owned contract держи строго между маркерами:

```markdown
<!-- qtim:contract:start -->
### Runtime contract qtim

- Детальный проектный контракт: `.codex/team-charter.md`; custom roles:
  `.codex/agents/*.toml`; durable state: `memory/`.
- qtim subagent workflow запускается только явным вызовом `$qtim-*` или прямой просьбой
  о делегировании. Main thread владеет fan-out, child agents не поднимают qtim-команду.
- `$qtim-mission` с глаголом исполнения или недвусмысленная просьба провести
  несколько Codex peer tasks как одну mission создаёт видимые задачи только после
  явного запуска Approved graph; одна обычная задача/диалог и planning-only запрос
  не авторизуют mission; mission workers не создают descendants; read-only и
  isolated writer nodes проходят validated receipts, transaction affected gate
  до locked exact-old ff-only promotion, отдельные portable state checkpoints и
  final verification.
- Результат subagent advisory до проверки main thread по файлам, артефактам и gates.
- qtim workflow запускается из новой задачи Codex на `gpt-6-astra` + `ultra`;
  каждый созданный ADR проходит clean-context Astra stress-test до approval.
- `$qtim-update` мигрирует generated state; `$qtim-doctor` диагностирует drift.
- Перед записью `memory/` или `docs/features/` вызови `$qtim-kb-format`;
  при обнаруженном дрейфе предложи `$qtim-kb-refresh`.

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

<!-- qtim:contract:end -->
```

Codex загружает применимый `AGENTS.md` до работы, поэтому этот короткий блок страхует
критические shared invariants без надежды на отдельный `Read`. Он не заменяет charter:
role TOML и spawn prompt по-прежнему требуют открыть нужные charter sections и memory.
При re-run заменяй только текст между `qtim:contract` markers; другие секции пользователя
и старые пояснения не переписывай.

Рядом со managed block добавь ссылки на `$qtim-team-up`, `$qtim-team-lazy`, `$qtim-mission`,
`$qtim-team-down`, `$qtim-team-retro` (до team-down), `$qtim-update`, `$qtim-onboard`,
`$qtim-doctor`, `$qtim-kb-refresh`, а при PM track — `$qtim-feature` и `docs/features/<slug>/`.

Если есть legacy `CLAUDE.md`, не переписывай его. Можно добавить в `AGENTS.md` заметку, что Codex читает `AGENTS.md`, а `CLAUDE.md` является legacy source only if the repo already uses it.

## Phase 5: Verification And Handoff

Проверь:

- `.codex/hooks.json`, если создан: JSON парсится; корень содержит `hooks`; каждый event содержит matcher groups с вложенным `hooks`; qtim handlers имеют `type: command` и `commandWindows`; qtim `PostToolUse` возвращает JSON `hookSpecificOutput.additionalContext`, а project layer не дублирует qtim `SessionStart` / `SubagentStop`;
- `.codex/screenshots-gate.json`, если создан: JSON парсится; `mode=blocking`; `directory` repo-relative без `..`; `freshnessMinutes` — положительное целое;
- TOML custom agents parse using Python `tomllib` if available;
- `qtim-reviewer` содержит `sandbox_mode = "read-only"`; testing role получила подставленный dev command и не содержит `{{DEV_CMD}}`;
- model policy каждого TOML совпадает с exact template pair или является подтверждённым catalog-supported override; half-pair, `model = "inherit"` и догаданный alias — ошибка; charter содержит team-lead Astra+Ultra, explorer Luna+medium и ADR adversary Astra+xhigh/max;
- каждый TOML, общий `## Language` charter и managed block `AGENTS.md` содержат полный обязательный language contract: internal/peer — English, user-facing — Russian;
- generated files contain no unresolved qtim placeholders;
- generated files do not reference plugin-internal paths (`../../reference/...`, `../../agents/...`) — вся нужная механика должна быть в charter или `memory/`;
- track-маркеры `qtim:track:*` в charter парные; при re-run оба track block целы, PM block содержит fast/full tracks, общий checkpoint, selective consult, vertical slicing с DRI/contributing roles и topology-based блок «Что запускать дальше» для direct/team-lazy/team-up/mission без auto-start;
- `memory/MEMORY.md` объясняет, что `memory/missions/<slug>/` создаётся `$qtim-mission` по мере надобности, а не setup;
- `memory/MEMORY.md` ссылается только на реально созданные файлы; перед записью применён `$qtim-kb-format`, а generated `AGENTS.md` указывает на него условно;
- корневой `.gitignore` содержит `.codex/qtim-runtime/`, runtime registry не
  отслеживается Git;
- при PM track `.gitignore` содержит `docs/features/**/.work/`;
- при выключенном independent code review: charter содержит секцию-заглушку «выключен», в сгенерированных TOML нет требований risk-based code review, но обязательный ADR stress-test в charter и architect TOML сохранён;
- version stamps на месте: `<!-- qtim-version: ... -->` в charter, `# qtim-version: ...` в каждом сгенерированном TOML, версия совпадает с `../../.codex-plugin/plugin.json`;
- `AGENTS.md` содержит ровно одну пару `qtim:contract` markers, managed block краткий, ссылки ведут на существующие файлы.

Финальный ответ: что создано, как пользоваться, какие plugin/local hooks надо trust через `/hooks` (и что `.codex/hooks.json` не создан, если optional `PostToolUse` не выбран), и что после создания custom agents нужно открыть новую задачу Codex на `gpt-6-astra` + `Ultra`, чтобы она чисто загрузила роли и работала как qtim team-lead. На существующей кодовой базе порекомендуй следом прогнать `$qtim-onboard` (dev track) — глубокое наполнение `memory/` картой, инвариантами и конвенциями, а при PM track — `$qtim-product-onboard`, который наполнит продуктовую память (разделы, акторы, словарь, аналитика), без которой intake/PRD опираются только на ответы пользователя. Упомяни `$qtim-doctor` как первый шаг при «что-то не работает». Отдельно назови plugin-provided `$qtim-mission`: full mode с worktree writers и final verification доступен в Codex App при наличии peer thread tools, а на остальных surfaces skill предлагает `$qtim-team-up` fallback. Setup не создаёт `memory/missions/` заранее.

## Critical Rules

- Do not generate `.claude/*`.
- Do not use Claude-only tools or primitives: `Agent({ name })`, `SendMessage`, `TaskCreate`, `TaskUpdate`, `TeamCreate`, `TeamDelete`, `team_name`.
- qtim subagent workflows require explicit user authorization through the skill or a direct delegation request. Team-lead profile is `gpt-6-astra` + `ultra`; it may proactively delegate only inside that authorized scope. Agent threads are task-scoped; verify runtime descendants before reuse, and never imply a hidden persistent team.
- Generated project files (`.codex/*`, `memory/*`, `AGENTS.md`) must be self-contained: no relative paths into the installed plugin.
- При повторном запуске обновляй только блок своего track между маркерами `qtim:track:*`; второй track и ручные правки пользователя сохраняются.
- Re-run остаётся additive: покажи plan/diff, добавляй недостающие поддерживаемые роли и qtim-owned practices, не удаляй роли, не затирай manual regions и сохраняй atomic model overrides; неоднозначность оставляй pending.
- Preserve existing user files. On collisions, ask before overwrite, skip, or rename.
