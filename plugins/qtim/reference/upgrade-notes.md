# Upgrade notes qtim для Codex

> Этот файл читает `$qtim-update` (и `$qtim-setup` при обнаружении устаревшего состояния). Для каждой версии описано, что меняется в **сгенерированном состоянии проекта** (`.codex/*`, `memory/`, `AGENTS.md`) и как мигрировать с предыдущей версии, не затирая правки пользователя. Изменения самого плагина живут в CHANGELOG репозитория и сюда не дублируются.

Правило ведения: при каждом релизе, меняющем сгенерированное состояние, добавляй секцию сверху. Секции хранятся newest-first, но `$qtim-update` всегда применяет попавшие в диапазон шаги oldest -> newest (снизу вверх по файлу). Если релиз не меняет сгенерированное состояние, добавляй секцию с пометкой «миграция не требуется».

## 2.15.1

Что нового в сгенерированном состоянии: явная GPT-6 матрица сохраняет прежнюю
иерархию ролей. Team-lead, architect, reviewer и ADR adversary используют
`gpt-6-astra`; database, frontend и product — `gpt-6-sol`; testing и built-in
explorer — `gpt-6-luna`. Reasoning не меняется: lead `ultra`, architect/reviewer
`xhigh`, database/frontend/product `high`, testing/explorer `medium`, adversary
`xhigh` или `max` по прежнему правилу риска.

Миграция с 2.15.0:

1. До записи покажи scoped diff и проверь доступность **каждой exact pair** в
   текущем Codex runtime. Если нужной пары нет, предложи обновить Codex или
   согласовать поддерживаемый atomic override; не удаляй поля модели, не
   подставляй alias и оставь миграцию `pending`. CLI catalog и App runtime могут
   различаться: проверяй поверхность, где команда будет работать.
2. Сопоставь только однозначно qtim-owned role TOML со stamp `2.15.0`, строкой
   roster charter, filename и `name`. Меняй только узнаваемую прежнюю default
   atomic pair: architect/reviewer `gpt-5.6-sol`+`xhigh` →
   `gpt-6-astra`+`xhigh`; database/frontend/product `gpt-5.6-sol`+`high` →
   `gpt-6-sol`+`high`; testing `gpt-5.6-terra`+`medium` →
   `gpt-6-luna`+`medium`. Отличающаяся полная пара — пользовательский override:
   сохрани её после проверки catalog и подтверждения владельца. Half-pair и
   неоднозначный файл оставь `pending`; foreign agents не меняй.
3. В распознанном ADR region `qtim-architect` точечно замени прежний
   `gpt-5.6-sol`+`xhigh|max` на `gpt-6-astra`+`xhigh|max`, а
   `adr-stress-test: sol-adversary` — на `astra-adversary`. Сохрани смысл
   обязательного clean-context stress-test и ручной текст вне region.
4. В общей model matrix и рабочих правилах charter замени только qtim-owned
   defaults: team-lead `gpt-6-astra`+`ultra`, присутствующие роли по пункту 2,
   explorer `gpt-6-luna`+`medium`, adversary `gpt-6-astra`+`xhigh|max` и
   marker `astra-adversary`. Dev/PM track и ручные колонки/строки сохрани.
   В `AGENTS.md` меняй только qtim-managed строку между
   `qtim:contract:start/end`: новый lead `gpt-6-astra`+`ultra` и
   clean-context Astra stress-test. Пользовательский текст вне markers не трогай.
5. Не меняй `memory/`, `docs/features/`, hooks, screenshot policy, `.gitignore`
   или runtime registry: смена моделей не мигрирует их содержимое. Проверяй
   TOML, полные пары, read-only reviewer, язык, парность track/contract markers,
   отсутствие GPT-5.6 в **текущей qtim-owned policy** и отсутствие plugin-internal
   путей в generated state. Исторические записи этого файла остаются историей.
6. Только после всех применимых `applied` или `compatible override confirmed`
   обнови charter stamp и stamps сопоставленных role TOML до `2.15.1`. При
   `pending` оставь stamps на `2.15.0`; после смены TOML открой новую задачу
   Codex, чтобы роли загрузились заново.

## 2.15.0

Что нового в сгенерированном состоянии:

- charter и managed block `AGENTS.md` задают ограниченный review loop, приоритет
  Approved scope, продолжение утверждённых фаз без повторного стартового запроса и
  условное правило `$qtim-kb-format` перед записью `memory/` или `docs/features/`;
- PM track допускает терминальный PRD-only результат и пропуск `estimate.md`,
  определяет `Archived` после проверенного `Done`, свидетельства слияния и
  решения владельца; хранит временные материалы в игнорируемой
  `docs/features/<slug>/.work/`;
- generated роли читают `memory/` только если файл есть и применяют
  `$qtim-kb-format` перед записью; reviewer получает scoped recheck и аккуратное
  ведение `memory/review-report.md`. Содержимое уже созданных `memory/` и
  `docs/features/` не мигрируется автоматически.

Миграция с 2.14.0:

1. До записи покажи scoped diff по charter, managed `AGENTS.md`, каждому
   затрагиваемому role TOML и `.gitignore`. Докажи qtim ownership charter stamp,
   парными `qtim:track:*` markers и `qtim:contract` markers. Для role TOML
   требуй согласованные charter row, filename, `name = "qtim-..."` и исходный
   stamp `2.14.0` по fail-closed правилам 2.13.0–2.14.0. Foreign/ambiguous
   файлы, ручные правки внутри target region и неединственные anchors оставь
   `pending`; не заменяй файл целиком. Уже полный target region — `applied`.
2. В общей working-rules части charter добавь точечно: явные ограничения
   пользователя и Approved scope старше рекомендаций review; находку вне scope
   вынеси в отдельную задачу, а невозможность выполнить обязательную приёмку или
   security gate пометь `Blocked` для решения владельца. Approved plan
   авторизует следующие фазы без повторного стартового запроса, кроме явно
   выбранного phase-by-phase режима или новой существенной развилки. Если
   independent code review включён, добавь первый reviewer pass на фазу и
   максимум два fix-and-recheck раунда: recheck охватывает исправленный риск и
   затронутые gates; полный повтор нужен только при расширении поведения за
   проверенный diff или изменении risk surface. Сохрани прежнюю canonical
   high-risk matrix, обязательный security/ADR review и выбранный review toggle.
3. В PM track charter, если он есть, замени только распознанную qtim-owned сводку
   full/fast pipeline: после PRD возможен терминальный `PRD-only` без
   decomposition/estimate/plan и рекомендации запуска; decomposition остаётся
   обязательной для планируемой реализации, `estimate.md` нужен только по
   запросу либо для выбора исполнителя, срока или бюджета; XL work item всё
   равно разрезается. Добавь `Archived` после проверенного `Done` и
   свидетельства слияния, по решению владельца. Долговечные PRD/plan/brief
   сохраняются; очистка `docs/features/<slug>/.work/` — отдельное решение
   владельца в том же пакете. Существующие `Done` остаются валидными.
   Не трогай dev track и ручной текст вне PM markers.
4. В managed block `AGENTS.md` добавь короткое условное правило: «Перед записью
   `memory/` или `docs/features/` вызови `$qtim-kb-format`; при обнаруженном
   дрейфе предложи `$qtim-kb-refresh`». Дополнительно назови
   `$qtim-kb-refresh` среди доступных команд. Сохрани текст вне markers
   byte-for-byte; не запускай refresh автоматически после каждого edit.
5. В однозначно сопоставленных qtim role TOML пометь каждый `memory/*` в
   `Read first` как «если создан»: setup больше не создаёт пустые файлы.
   Пишущим в `memory/` или `docs/features/` ролям добавь вызов
   `$qtim-kb-format` перед записью и сжатие вместо append-only истории;
   product role получает PRD-only, optional estimate и лимит истории.
   В `qtim-reviewer` добавь additive contract: Approved scope, отдельные
   out-of-scope рекомендации, первый полный pass, scoped recheck с лимитом
   двух fix-and-recheck раундов, полный повтор только при изменении risk
   surface, read-only память через main thread. Не меняй `sandbox_mode`,
   model pair, ручные инструкции и неизвестные роли.
6. Только для PM track добавь в корневой `.gitignore` ровно одну активную строку
   `docs/features/**/.work/`, сохранив остальное содержимое и порядок. Если
   `.work/` уже отслеживается Git, не удаляй файлы автоматически: оставь
   migration pending и покажи точные пути. Для dev-only проекта шаг не нужен.
7. Не создавай пустые `memory/decisions.md`, `review-report.md` или
   `bug-log.md`; не переписывай существующие memory, feature artifacts, ADR,
   `.work/` и внешние хранилища. Их приведение к `$qtim-kb-format` выполняется
   отдельным, явно выбранным refresh после read-only отчёта и проверки базы.
   В `memory/MEMORY.md` добавляй только проверенный указатель на существующий
   файл, если он отсутствует и действительно нужен; иначе не меняй индекс.
8. Проверь TOML parse, парность markers, high-risk/review toggle, full/fast/PRD-only
   PM contract, одну `.work/` ignore-строку при PM track и сохранение ручного
   текста/model pairs. Только когда применимые шаги имеют status `applied`,
   `not applicable` или `compatible override confirmed`, обнови charter и
   stamps однозначно сопоставленных qtim role TOML до `2.15.0`. При `pending`
   оставь весь version range незавершённым. После изменения agent TOML открой
   новую задачу Codex перед следующим qtim workflow.

## 2.14.0

Что нового в сгенерированном состоянии:

- каждый qtim custom agent, включая project-specific Extended-роли, получает
  обязательный `## Language` contract: internal reasoning и сообщения peer agents
  идут на English, user-facing документы, review findings и всё передаваемое
  пользователю — на Russian;
- общий charter и автоматически загружаемый managed block `AGENTS.md` несут тот же
  contract для team-lead, built-in `explorer`/`worker`, fallback-ролей и mission
  peers, а orchestration prompts/follow-ups составляются на English.

Миграция с 2.13.0:

1. Классифицируй agent TOML по тому же fail-closed ownership contract, что и в
   migration 2.13.0: bundled qtim role либо qtim-generated custom role доказывается
   согласованными charter row, filename, TOML `name = "qtim-..."` и исходным stamp
   `2.13.0`; foreign/ambiguous file не меняй и оставь шаг pending.
2. В `developer_instructions` каждой однозначно сопоставленной qtim role точечно
   добавь следующий блок, не заменяя весь TOML и не меняя model pair, sandbox,
   project substitutions, minimal-diff regions или остальные ручные инструкции:

   ```markdown
   ## Language

   Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.
   ```

   Exact block уже есть -> region applied. Если внутри prompt есть другое правило о
   языке internal/peer или user-facing output, не объявляй его compatible override:
   покажи точный конфликт и оставь migration pending до подтверждения пользователя.
   После подтверждения убери только конфликтующие строки и сохрани остальной prompt.
3. В общей части `.codex/team-charter.md` вне `qtim:track:*` markers добавь один
   `## Language` с тем же дословным абзацем. Существующий exact block не дублируй;
   оба track block, roles table и другой текст charter сохрани.
4. Между `qtim:contract:start/end` project `AGENTS.md` добавь тот же `## Language`
   и абзац. Текст до/после managed markers сохрани byte-for-byte; существующий exact
   block не дублируй.
5. Проверь TOML parse и наличие полного contract во всех сопоставленных qtim agent
   TOML, charter и managed `AGENTS.md`. Foreign agents, hooks, memory,
   feature/mission artifacts, `.gitignore` и screenshots config не меняй.
6. Обнови charter и stamps всех сопоставленных qtim role TOML до `2.14.0` только
   после шагов 1–5 без `pending`. Так как меняются agent TOML, перед следующим qtim
   workflow обязательна новая задача Codex.

## 2.13.0

Что нового в сгенерированном состоянии:

- `$qtim-minimal-diff` стал Layer 0 practice: architect сравнивает объём
  design-вариантов, database/frontend проходят лестницу до нетривиальной
  реализации, reviewer относит чистую избыточность к рекомендациям, не ослабляя
  blockers по scope, protected zones, инвариантам и обязательным gates;
- roles table charter фиксирует те же mandatory practices; у database/frontend/
  testing сохраняются прежние `$qtim-debug-loop` practices;
- generated role TOML содержат role-specific contract, но atomic model pairs,
  ручные инструкции и optional external skills не меняются;
- `memory/MEMORY.md` объясняет on-demand ownership `memory/retro-log.md` для
  доказанно сработавших `minimal-diff:` follow-up.

Миграция с 2.12.0:

1. До записи покажи отдельный plan/diff по charter, каждому role TOML и
   `memory/MEMORY.md`. Роль сопоставляй только когда charter row, имя файла и
   `name = "qtim-..."` дают один и тот же supported target. Переименованный
   файл, несколько кандидатов, roster role без файла или несовпадающий `name`
   оставляют конкретный шаг `pending`: не создавай дубликат, не переименовывай и
   не заменяй весь файл. Роль, которой нет в выбранном roster, — not applicable.
2. Мигрируй перечисленные ниже **regions независимо**. Target markers делают
   `applied` только свой region, а не всю роль. Частичный target, неуникальный
   anchor или ручной текст внутри предполагаемой замены — `pending` со scoped
   diff. Повторный `$qtim-update` распознаёт уже applied regions и не дублирует
   их.
3. В общей roles table charter точечно дополни только распознанные qtim-owned
   mandatory-practice cells:
   - architect — `$qtim-minimal-diff` при сравнении design-вариантов;
   - database/frontend — `$qtim-minimal-diff` до нетривиальной реализации и
     существующий `$qtim-debug-loop` для нетривиального бага;
   - testing — существующий `$qtim-debug-loop` для flaky repro;
   - reviewer — `$qtim-minimal-diff`: чистая избыточность в рекомендации,
     protected-zone/invariant/gate violations остаются blockers;
   - распознанная qtim-generated code-writing роль без bundled template —
     minimal-diff в mandatory-practice cell и self-contained TOML contract из
     шага 8; неизвестную responsibility оставь `pending` и верни decision owner.
   Сохрани неизвестные rows/columns, соседний track, optional external skills и
   ручной текст вне этой ячейки byte-for-byte.
4. В сопоставленном role file с `name = "qtim-architect"` target group:
   `$qtim-minimal-diff`, `Новый слой и новая зависимость — архитектурное решение`
   и `Чистая избыточность — рекомендация`. Первый region вставь после
   единственного DESIGN-абзаца с `$qtim-brainstorm`/`$qtim-prototype`, второй —
   после единственного REVIEW-абзаца с `expand-contract`.
5. В сопоставленном role file с `name = "qtim-database"` target group:
   `$qtim-minimal-diff`, `constraint, index или trigger`, `не сокращай и не
   откладывай`, плюс checklist marker `обязательная минимальная проверка`.
   Вставляй process/guard region между обязательным процессом и единственным
   `$qtim-debug-loop` block; checklist line — только в существующий `Checklist:`.
6. В сопоставленном role file с `name = "qtim-frontend"` target group:
   `$qtim-minimal-diff`, `Trust-boundary validation`, `одну минимальную проверку`
   и handoff marker `Confirm the solution scope`. Основной region вставляй перед
   единственным `$qtim-debug-loop` paragraph, handoff line — в существующий
   `Before handoff:` list.
7. В сопоставленном role file с `name = "qtim-reviewer"` target group:
   `Minimal-diff review (recommendations, not automatic blockers)`,
   `$qtim-minimal-diff`, `pure excess` и `protected-zone`. Вставляй единый region
   перед `Independent review gate:`. Минимальную breaking check нетривиальной
   логики не считай избыточностью; новый test framework сверх нужного сигнала
   может остаться рекомендацией.
8. Для custom role без bundled template сначала докажи qtim ownership всей
   совокупностью fingerprints: первая строка `# qtim-version: 2.12.0`, ровно
   одна charter row с тем же custom-agent name, совпадающие filename и TOML
   `name = "qtim-..."`. Отсутствие любого fingerprint, несколько rows/files или
   переименование — `pending`; foreign agent не меняй. По charter mission/
   responsibility и self-contained instructions однозначно классифицируй роль:
   - code-writing role — в единственный multiline `developer_instructions`
     additive-вставкой перед его closing delimiter добавь target group:
     `$qtim-minimal-diff` до нетривиальной реализации; approved scope и
     protected zones не сокращаются; disputed scope возвращается main thread;
     нетривиальная логика получает одну минимальную breaking check без новой
     test infrastructure;
   - явно read-only auditor/product role — `not applicable`, TOML body не меняй;
   - неоднозначная responsibility, неединственный multiline block, partial target
     group или ручной текст внутри предполагаемой вставки — `pending` со scoped
     diff, без whole-file overwrite.
   Уже полный target group — `applied`; повторный update его не дублирует.
9. Atomic `model` + `model_reasoning_effort` каждой роли не меняй. Exact current
   pair и подтверждённый catalog-supported override — `compatible override
   confirmed`. Для qtim-generated custom role без template сохраняй существующую
   полную pair byte-for-byte. Half-pair, `model = "inherit"` или недоступная pair
   остаются `pending`. Не угадывай замену.
10. В `memory/MEMORY.md` добавь одну qtim-managed строку: файл
   `memory/retro-log.md` создаёт `$qtim-team-retro` по мере надобности; только
   доказанно сработавший `minimal-diff:` marker получает follow-up с source,
   trigger evidence, одним owner и проверяемым next action. Сам retro-log не
   создавай, остальные memory entries не меняй.
11. Обнови charter и stamps всех сопоставленных qtim role TOML — включая
    qtim-generated custom roles без bundled template — до `2.13.0` только когда
    шаги 1–10 для текущего roster имеют status `applied`, `not applicable` или
    `compatible override confirmed`. При первом обязательном `pending` останови
    range: charter и все qtim role stamps остаются `2.12.0`, более новые sections
    не применяются. После изменения agent TOML открой новую задачу Codex; foreign
    custom agents и их stamps не меняй. Без миграции новый skill доступен после
    plugin update, но generated roles его не вызывают.

Rollback не удаляет роли, memory или `minimal-diff:` comments. Уже применённый
managed contract корректируется следующей region-aware migration; published
semver не переиспользуется.

## 2.12.0

Что нового в сгенерированном состоянии:

- PM track charter заканчивает Approved feature обязательным topology-based блоком
  «Что запускать дальше» для direct / team-lazy / team-up / mission; recommendation
  ничего не запускает без нового явного разрешения;
- managed qtim contract в project `AGENTS.md` фиксирует, что `$qtim-mission` с
  глаголом исполнения или недвусмысленная просьба провести несколько Codex peer
  tasks как одну mission создаёт видимые задачи, а одна обычная задача/диалог и
  planning-only запрос — нет; workers не создают descendants, writers
  изолированы worktrees, affected gate проходит до locked exact-old ff-only
  promotion, portable state checkpoint-ится отдельно и общий gate закрывает
  отдельный verifier;
- `memory/MEMORY.md` упоминает on-demand `memory/missions/<slug>/`; сам каталог
  setup/update не создают;
- корневой `.gitignore` исключает machine-local `.codex/qtim-runtime/`, а portable
  mission evidence остаётся отслеживаемым.

Миграция с 2.11.0:

1. В PM track между `qtim:track:pm:start/end` обнови только engine-managed handoff
   summary: добавь блок «Что запускать дальше» с полями recommendation, why,
   topology, command, alternative; выбор по outcomes/dependencies/context isolation/
   feedback loops, а не размеру; `RECOMMEND` не запускает tasks. Approved mission
   graph с зафиксированными base/integration target, scopes, budgets и gates
   использует `запусти`; unresolved writer/lazy/runtime choice — `preview`;
   `$qtim-team-up` остаётся fallback для одного связного feedback loop. Dev track
   и текст вне PM markers не трогай. Для dev-only проекта шаг not applicable.
2. В общей working-rules секции charter, не трогая track blocks, добавь mission
   ownership: только coordinator создаёт peer tasks и владеет DAG/runtime/
   integration/final verdict; Approved lazy node получает ровно один local
   `$qtim-team-lazy` level; writers работают в отдельных worktrees и возвращают
   один commit, который проходит topological transaction affected gate до
   exclusive-lock exact-old/ff-only promotion в отдельный clean integration
   worktree; portable evidence получает scoped commits в отдельной state worktree
   и final bundle delivery, resume требует одного owner/generation; status/resume/stop
   fail-visible, SessionStart только advisory, auto-archive запрещён.
3. В managed region project `AGENTS.md` между `qtim:contract:start/end` добавь
   `$qtim-mission`: peer tasks только после явного запуска Approved graph через
   skill с глаголом исполнения или недвусмысленную просьбу провести несколько
   Codex peer tasks как одну mission; одна обычная задача/диалог и planning-only
   запрос не авторизуют mission. Mission workers не создают descendants;
   read-only и isolated writer nodes используют validated receipts, writer
   commits проходят transaction affected gate до locked exact-old ff-only
   promotion, portable evidence checkpoint-ится в отдельной state worktree,
   итог закрывает separate verifier. Пользовательский текст вне markers сохрани
   byte-for-byte.
4. В `memory/MEMORY.md` добавь одну строку без ссылки на несуществующий path:
   `memory/missions/<slug>/` создаёт только явно запущенная mission через
   `$qtim-mission` с глаголом исполнения или недвусмысленную просьбу провести
   несколько Codex peer tasks как одну mission для portable spec,
   validated/integrated receipts, локальных решений и final verification;
   opaque runtime handles живут только в gitignored `.codex/qtim-runtime/`.
   Остальные memory files и их содержимое не переписывай; каталог missions заранее
   не создавай.
5. В корневом `.gitignore` добавь ровно одну активную строку
   `.codex/qtim-runtime/`, сохранив все существующие строки и порядок. Если runtime
   files уже tracked, не удаляй их автоматически: оставь migration pending и
   покажи точные paths пользователю.
6. Role TOML content кроме version stamp, project hooks и существующие
   mission/feature artifacts не меняй. Обнови charter/TOML stamps до `2.12.0`
   только после applicable шагов 1–5.

## 2.11.0

Что нового в сгенерированном состоянии:

- `AGENTS.md` содержит один компактный qtim runtime contract между
  `<!-- qtim:contract:start/end -->`; пользовательский текст вне markers сохраняется;
- reviewer получил `sandbox_mode = "read-only"` и секцию `Adversary`;
- testing получил фактическую `DEV_CMD` и владеет запуском dev-server;
- PM block — производная self-contained сводка; Stage 6 pointer в `memory/decisions.md`
  записывается последним и является completion marker;
- blocking screenshots остаётся opt-in через `.codex/screenshots-gate.json`.

Миграция с 2.10.0:

1. Нормализуй qtim-секцию project `AGENTS.md` в одну marker pair. Замени только managed
   region; весь текст пользователя до/после сохрани byte-for-byte. В блоке оставь указатели
   на charter/agents/memory, explicit workflow scope, main-owned fan-out, advisory outputs,
   Sol/Ultra prerequisite, ADR adversary и update/doctor.
2. В `qtim-reviewer.toml` добавь `sandbox_mode = "read-only"` и report section `Adversary`.
   Любой write-enabled user override покажи как diff и оставь migration pending до решения;
   reviewer не превращай в fix worker.
3. В `qtim-testing.toml` подставь фактическую dev-команду из `memory/commands.md` или
   проверенного project script. Если команда неизвестна, не угадывай: оставь шаг pending.
   Добавь владение long-running server session и поле status в handoff.
4. Только в PM track замени engine-managed сводку: пометь её производной от durable
   feature-pipeline contract и добавь правило «handoff artifacts first, decisions pointer
   last». Approved brief/plan без pointer означает resume Stage 6.
5. Не включай blocking screenshots существующим проектам автоматически. По явному opt-in
   создай `.codex/screenshots-gate.json` с `mode=blocking`, безопасным repo-relative
   `directory` без `..` и положительным `freshnessMinutes`; отсутствие config = advisory.
6. Обнови stamps до `2.11.0` только когда обязательные шаги 1–4 applied или compatible
   override confirmed. Optional screenshot config не влияет на stamp. После изменения TOML
   открой новую задачу Codex.

## 2.10.0

Что нового в сгенерированном состоянии:

- постоянные роли получили явные GPT-5.6 pair вместо inheritance: architect/reviewer — `gpt-5.6-sol` + `xhigh`; database/frontend/product — `gpt-5.6-sol` + `high`; testing — `gpt-5.6-terra` + `medium`;
- charter фиксирует отдельные профили team-lead (`gpt-5.6-sol` + `ultra`), built-in explorer (`gpt-5.6-luna` + `medium`) и ephemeral ADR adversary (Sol+xhigh; Sol+max для «необратимо + документированный инвариант»);
- каждый созданный ADR до user approval проходит self-play `$qtim-grill` и обязательный independent stress-test новым read-only Sol thread без истории; итог виден в строке `adr-stress-test:` самого ADR;
- ADR stress-test не зависит от setup-toggle risk-based independent review кода: выключенный code-review gate больше не оставляет архитектурное решение без второй пары глаз.

Миграция с 2.9.0:

1. Для каждой role pair обрабатывай `model` + `model_reasoning_effort` атомарно:
   - `qtim-architect` и `qtim-reviewer` target — `gpt-5.6-sol` + `xhigh`;
   - `qtim-database`, `qtim-frontend`, `qtim-product` target — `gpt-5.6-sol` + `high`;
   - `qtim-testing` target не меняется — `gpt-5.6-terra` + `medium`.
   Exact target -> `applied`. У intelligence-heavy роли 2.9.0 отсутствие обоих полей было qtim-default, но могло стать осознанным user override: покажи добавление pair и один раз спроси «применить явный профиль 2.10 или сохранить inheritance как compatible override». При прямом upgrade с 2.7/2.8 известны прежние defaults: architect/database/reviewer/product — Sol+high, frontend — Sol+medium; если такая pair отличается от target, покажи замену и один раз спроси, не была ли она закреплена пользователем. Любую другую atomic pair сохрани как override до показанного diff. Half-pair и `model = "inherit"` оставь `pending`. Если exact target отсутствует в local catalog, не угадывай замену и не удаляй pair: предложи обновить Codex или подтвердить catalog-supported override.
2. В `qtim-architect.toml` обнови ADR region по current template. Target group: `ADR готов к независимому stress-test`, `gpt-5.6-sol` + `xhigh`, escalation `gpt-5.6-sol` + `max`, `adr-stress-test: sol-adversary`, `adr-stress-test: pending`. Anchor — единственный блок между fallback `Если хотя бы одного условия нет` и `ADR format:`. Если target group partial, anchor не уникален или в region есть ручной текст, не заменяй его целиком: покажи diff и оставь region `pending`. Этот region применяется **даже когда independent code review выключен**; из architect можно вырезать только отдельную строку про canonical high-risk matrix.
3. В общей roles table charter обнови mandatory practice architect: `$qtim-brainstorm` до ADR + clean-context Sol stress-test каждого созданного ADR. Optional external skills и ручные колонки не трогай.
4. Под roles table добавь/обнови engine-managed model matrix с точными профилями: team-lead Sol+Ultra; architect/reviewer Sol+xhigh; database/frontend/product Sol+high; testing Terra+medium; built-in explorer Luna+medium; ADR adversary Sol+xhigh/max. Существующие документированные user overrides перенеси в этот блок, не перетирая.
5. Добавь общий блок `ADR stress-test` вне track-маркеров: main thread спавнит новый read-only thread без истории (`fork_turns = "none"` или runtime-эквивалент), передаёт только ADR/инварианты/проверяемые paths, получает findings, architect их верифицирует, ADR фиксирует `adr-stress-test: ...` или честный `skipped — <reason>`. Блок обязателен при любом состоянии optional independent code review.
6. В working rules charter зафиксируй team-lead prerequisite `gpt-5.6-sol` + `ultra`, main-owned fan-out и explorer Luna+medium. Не меняй execution depth A/B/C/D, track blocks и пользовательские правила.
7. Если risk-based independent code review выключен, оставь его заглушку, но уточни «выключен review фактического diff; ADR stress-test остаётся включён». Не возвращай code-review blocks reviewer/database/architect. Если gate включён, canonical high-risk matrix 2.9 остаётся без изменений.
8. В секцию `Команда qtim` проектного `AGENTS.md` добавь краткое правило: qtim workflows запускать из новой задачи Codex на Sol+Ultra; каждый ADR требует clean-context Sol stress-test до approval. Остальные правила проекта не переписывай.
9. Обнови stamps charter и всех qtim TOML до `2.10.0` только когда model decisions и все applicable regions имеют status `applied` или `compatible override confirmed`. При любом `pending` оставь stamps `2.9.0`. После изменения agent TOML открой новую задачу Codex на `gpt-5.6-sol` + `ultra` перед `$qtim-team-up`, `$qtim-team-lazy`, `$qtim-feature`, `$qtim-onboard` или `$qtim-product-onboard`.

## 2.9.0

Что нового в сгенерированном состоянии:

- intelligence-heavy роли (`qtim-architect`, `qtim-database`, `qtim-frontend`, `qtim-reviewer`, `qtim-product`) наследуют model/reasoning текущей Codex session: оба поля отсутствуют; `qtim-testing` сохраняет явную более дешёвую pair `gpt-5.6-terra` + `medium`;
- architect использует `$qtim-brainstorm` до ADR, `$qtim-prototype` для UX/behavior fork, `$qtim-grill` для stress-test, тройной ADR filter и expand-contract; database/frontend/testing получили `$qtim-debug-loop`; product — vertical slicing; reviewer — risk-based independent review;
- roles table charter фиксирует bundled mandatory practices по ролям (`brainstorm` у architect, `debug-loop` у database/frontend/testing), не смешивая их с optional external skills;
- включённый independent-review block различает обязательные high-risk gates и явный low-risk skip;
- PM track charter стал двухтрековым: fast-path `feature-brief.md` с main-thread evidence fallback или полный pipeline с общим checkpoint decomposition + estimate, selective consult и vertical slices с DRI/contributing roles/layer estimates; широкий рефактор — expand-contract.

Миграция с 2.8.0:

1. Frozen template 2.8.0 в marketplace snapshot нет — Git history не считай частью migration contract. Мигрируй перечисленные ниже **regions независимо**: target markers делают `applied` только свой region, а не всю роль. Для группы из нескольких markers нужны все markers. Роль завершена, только когда каждый applicable region ниже имеет статус `applied` или `compatible override confirmed`; частично новый region оставляй `pending`, не дописывай его вслепую. Новый текст бери из current template, **кроме исторического architect / ADR filter region ниже**: current template 2.10 уже содержит более новый Sol-adversary block, которым владеет следующая section. 2.8 распознавай только по этим fingerprints и anchors:
   - architect / description: target — точное `description = "qtim architect role: explores design options, writes ADRs only for consequential trade-offs, protects domain invariants, and slices implementation work across database/frontend/testing/review roles."`; old — точное `description = "qtim architect role: plans feature architecture, writes ADRs, protects domain invariants, slices implementation work across database/frontend/testing/review roles."`. Отличающееся user-description сохрани как compatible override.
   - architect / DESIGN output: target — точная строка `- DESIGN: перед разработкой нетривиальной фичи. Выход: design brief, ADR или строка реестра решений, data flow, затронутые инварианты, задачи по ролям.`; old — точная строка `- DESIGN: перед разработкой нетривиальной фичи. Выход: ADR, data flow, затронутые инварианты, задачи по ролям.`.
   - architect / design start: target group — markers `В DESIGN сначала вызови \`$qtim-brainstorm\`:` и `UX- или поведенческую развилку предложи разрешить через \`$qtim-prototype\``; old region — абзац с точным prefix `В DESIGN первым делом проверь границу видимости данных:`.
   - architect / ADR filter: target group — `ADR создавай только когда одновременно выполняются все три условия:`, fallback `Если хотя бы одного условия нет` и `$qtim-grill`. Если target range заканчивается на 2.9.0, вставляй исторический 2.9 region: три условия из current template + строку `Если хотя бы одного условия нет, добавь короткую строку в \`memory/decisions.md\`, не создавай отдельный документ. Перед фиксацией нетривиального ADR проведи \`$qtim-grill\` в self-play или с decision owner.` перед единственным `ADR format:`. Если range включает 2.10.0, этот шаг проверяет только три marker, а Sol-adversary block добавляет section 2.10.0; не копируй current ADR region досрочно.
   - architect / expand-contract: target — marker `В REVIEW широкий механический rename/retype` вместе с `expand-contract`; вставляй current абзац после абзаца с prefix `Ты не пишешь SQL-миграции, UI-компоненты`.
   - architect / independent review: target — marker `Если решение срабатывает по canonical high-risk matrix`; old — строка с prefix `При security-critical или money-critical решениях`. Region applicable только при включённом gate.
   - database / debug: target group — `$qtim-debug-loop` и `Политику доступа, trigger или data-integrity правило не переписывай`; если обоих нет, вставь current debug block перед единственным `Checklist:`.
   - database / independent review: target — marker `сработавшие по canonical high-risk matrix charter`; old — точная checklist-строка `security-critical изменения прошли independent review gate`. Region applicable только при включённом gate.
   - frontend / debug: target group — `$qtim-debug-loop` и `Не чини перебором вариантов без repro`; если обоих нет, вставь current debug block перед единственным `Before handoff:`.
   - testing / flaky repro: target group — `$qtim-debug-loop` и `готовый красный сигнал для исполнителя`; если обоих нет, вставь current block перед единственным `UI acceptance не закрывается без:`.
   - product / ownership: target group — `один DRI` и `contributing роли/слои`; old — строка с prefix `work items привязывай к слоям и конкретным файлам` в единственной секции `Правила декомпозиции и оценки`.
   - product / vertical slice: target group — `проверяемый вертикальный срез` и `главной acceptance boundary`; вставь current строку в ту же секцию только когда обоих markers нет.
   - product / expand-contract: target group — `широкий механический rename/retype` и `expand-contract`; вставь current строку в ту же секцию только когда обоих markers нет.
   - product / estimation: target group — `каждая contributing dev-роль оценивает свой layer slice` и `DRI синтезирует один S/M/L/XL`; old — строка с prefix `размер work item (S/M/L/XL + confidence + риски) даёт профильный dev-агент`.
   - reviewer / risk gate: target group — `Canonical high-risk matrix` и `independent review: skipped (low-risk diff)`. Только когда обоих нет, замени блок между единственными `Independent review gate:` / `Report format:`, если он начинается `For security-critical, money-critical, public API, migration, or auth changes` и заканчивается `verify every file:line yourself.`; наличие ровно одного target marker означает partial region и остаётся pending.
   Если ожидаемый old fingerprint изменён, anchor найден не ровно один раз, target group присутствует частично или в заменяемом region есть ручные строки, не заменяй весь файл: покажи diff и оставь конкретный region pending.
2. Если target range заканчивается на 2.9.0: для `qtim-architect`, `qtim-database`, `qtim-reviewer`, `qtim-product` точная прежняя qtim-default pair — `gpt-5.6-sol` + `high`, для `qtim-frontend` — `gpt-5.6-sol` + `medium`. Совпадение с default по значению не доказывает, что user не закрепил его осознанно: покажи удаление pair и один раз спроси «inherit или сохранить pin». При inherit удали **оба** поля; подтверждённый catalog-supported pin сохрани как compatible override. Отличающуюся pair также считай override до показанного diff. Half-pair и `model = "inherit"` не оставляй. `qtim-testing` оставь на `gpt-5.6-terra` + `medium`, если это прежний default; недоступный slug -> удалить оба поля, не угадывать замену. Если target range включает 2.10.0, inheritance 2.9 superseded: не удаляй pair в этом шаге, перенеси её как input для классификации 2.10.0 и сразу примени/подтверди target pair следующей section.
3. Обнови agent templates точечно: architect — bundled design disciplines, ADR filter и expand-contract; database/frontend — debug-loop block; testing — flaky reproduction и красный сигнал исполнителю; product — vertical slices/expand-contract; reviewer — mandatory high-risk request и `independent review: skipped (low-risk diff)`. Если independent review выключен заглушкой charter, gate-блок reviewer/architect/database не возвращай.
4. В общей roles table обнови только qtim mandatory practices: architect — `$qtim-brainstorm до ADR`; database/frontend — `$qtim-debug-loop` для нетривиального бага; testing — `$qtim-debug-loop` для flaky repro. Bundled `$qtim-*` не добавляй в колонку optional external skills; существующие пользовательские/stack skills сохрани.
5. Если independent review включён, обнови его общий block точной canonical high-risk matrix: security/auth/tenant-scope visibility; money/billing/account state; documented domain invariants/public contracts; data-transform/destructive migrations; critical browser flows; high-risk performance/reliability; другое доказанно hard-to-rollback изменение. Любое совпадение требует read-only review request; low-risk diff допускает зафиксированный skip. При выключенном gate сохрани заглушку.
6. Только при наличии PM track замени engine-managed содержимое между `qtim:track:pm` markers: добавь full/fast tracks, `feature-brief.md`, общий checkpoint decomposition + estimate, consult только затронутых слоёв и vertical slicing с одним DRI и contributing roles. Layer estimates каждой contributing роли + DRI synthesis обязательны в полном треке; fast-path использует main-thread evidence fallback без обязательного fan-out. Широкий рефактор — expand-contract. Dev track и ручные правки вне markers не трогай.
7. `memory/`, существующие `docs/features/`, project hooks и секцию qtim в `AGENTS.md` не переписывай. Четыре новых skills поставляет сам plugin; копировать их в проект не нужно.
8. Обнови stamps charter и всех qtim TOML до `2.9.0` **только** когда все applicable шаги имеют status `applied` или `compatible override confirmed`. Если хотя один engine-managed block отложен, оставь все stamps на последней полностью завершённой версии (для обычного upgrade с 2.8.0 это 2.8.0): иначе следующий update ложно сочтёт миграцию завершённой. После изменения agent TOML перед следующим `$qtim-team-up`, `$qtim-team-lazy` или `$qtim-feature` обязательно открой новую задачу Codex.

## 2.8.0

Что нового в сгенерированном состоянии:

- plugin-bundled `SessionStart` / `SubagentStop` больше не копируются в project `.codex/hooks.json`, потому что Codex складывает оба hook layers и запускает дубли;
- optional project `PostToolUse` использует canonical nested command schema из `reference/project-hooks.json` и возвращает JSON `hookSpecificOutput.additionalContext` вместо игнорируемого plain stdout;
- hook definitions получили отдельные POSIX/Windows commands; изменённые definitions нужно заново review/trust через `/hooks`.

Миграция с 2.7.0 и более ранних версий:

1. Если `.codex/hooks.json` отсутствует, не создавай его: исправленные `SessionStart` / `SubagentStop` придут из plugin layer.
2. Если файл есть, сначала сохрани его порядок и классифицируй каждый handler. qtim ownership определяй по совокупности fingerprints: guard `.codex/team-charter.md`; `[qtim` / `$qtim-*`; `qtim-version:`; тексты про реальные артефакты, затронутый слой или typecheck/build/test. Одного event name недостаточно.
3. Удали распознанные qtim `SessionStart` / `SubagentStop` из project layer как bundled-дубли. Если в matcher group есть пользовательские handlers, сохрани group и удали только qtim handler. Неоднозначные entries покажи пользователю и не меняй без решения.
4. Распознанный qtim `PostToolUse` в legacy top-level форме, с `type: reminder` / `message` или plain `echo` / `printf` замени handler из соседнего [project-hooks.json](project-hooks.json). Если он находится внутри matcher group с пользовательскими handlers, замени только qtim handler; group удаляй лишь когда после удаления qtim entries в нём ничего не осталось. Остальные handlers, PostToolUse groups и events сохрани без изменений.
5. Если после удаления qtim-дублей файл пуст и optional `PostToolUse` не выбран, предложи удалить `.codex/hooks.json`, покажи diff и дождись подтверждения. Не удаляй пустой файл молча.
6. Проверь canonical schema (`hooks -> Event[] -> hooks[] -> type: command`) и JSON output qtim `PostToolUse`; открой `/hooks` и заново review/trust изменённые definitions.
7. Обнови stamps charter и всех qtim TOML до `2.8.0`. Содержимое agent TOML, track blocks, `memory/`, `docs/features/` и секцию qtim в project `AGENTS.md` не меняй.

При прямой миграции с версии ниже 2.8.0 исторический шаг 2.2.0 про добавление project `SessionStart` пропусти: его заменяет plugin-bundled hook 2.8.0.

## 2.7.0

Что нового в сгенерированном состоянии:

- role profiles перешли на точные GPT-5.6 catalog slugs: architect/database/reviewer/product — `gpt-5.6-sol` + `high`, frontend — `gpt-5.6-sol` + `medium`, testing — `gpt-5.6-terra` + `medium`;
- `model` + `model_reasoning_effort` теперь считаются одной парой: если точный профиль недоступен, оба поля удаляются и роль наследует профиль главного task;
- working rules charter разделяют execution depth A/B/C/D и root reasoning: `Max`/`Ultra`/Fast выбирает пользователь, `Ultra` может делегировать только внутри разрешённого qtim scope, child agents не спавнят qtim descendants, main thread учитывает runtime thread cap и сначала проверяет доступные descendant threads;
- reviewer просит main thread поднять independent review вместо попытки спавнить descendant самостоятельно.

Миграция с 2.6.0:

1. Для каждого `.codex/agents/qtim-*.toml` сравни текущую пару с прежним и целевым qtim-default. Целевая pair уже стоит -> шаг idempotently applied. Прежнюю default pair обнови: `qtim-architect` / `qtim-database` / `qtim-reviewer` / `qtim-product` с `gpt-5.5` + `high` на `gpt-5.6-sol` + `high`; `qtim-frontend` с `gpt-5.5` + `medium` на `gpt-5.6-sol` + `medium`; `qtim-testing` с `gpt-5.4` + `medium` на `gpt-5.6-terra` + `medium`.
2. Если присутствует ровно одно из полей `model` / `model_reasoning_effort`, это broken half-pair (в том числе возможный legacy fallback 2.6.0), а не готовый override. Покажи diff и после подтверждения либо установи доступную template pair 2.7.0, либо удали оставшееся поле для полного наследования.
3. Если **оба** поля присутствуют и пара отличается и от прежнего, и от целевого qtim-default, считай её пользовательским override: проверь по локальному catalog, покажи diff и не перезаписывай без подтверждения. Если выбранный GPT-5.6 profile недоступен в текущем Codex, удали **оба** поля вместо догаданной замены.
4. Обнови `qtim-reviewer` по template: independent review запрашивается у main thread; при выключенном гейте не возвращай вырезанный setup-ом gate-условный блок.
5. В общей working-rules секции `.codex/team-charter.md` добавь правила root reasoning/Ultra, task-scoped descendants, main-owned fan-out и batching по runtime cap. Ручные правки и оба track-блока не перезаписывай.
6. Обнови stamps charter и всех qtim TOML до `2.7.0`. `memory/`, `docs/features/` и секцию qtim в проектном `AGENTS.md` не меняй. Так как agent TOML изменились, перед qtim workflow обязательно открой новую задачу Codex.

## 2.6.0

Миграция не требуется — правки только движка (skills `qtim-feature` / `qtim-team-up` / `qtim-team-lazy` / `qtim-team-retro` / `qtim-doctor` и `reference/feature-pipeline.md`): intake-интервью, фиксация отклонений от `plan.md` в «Истории изменений», порядок фаз плана по неопределённости, проверка продуктовой памяти в doctor. Проекты получают их автоматически при следующем вызове skills; charter, шаблоны ролей и `memory/` не меняются. PM track block новых charter впитает обновлённый handoff contract сам — setup переносит суть `feature-pipeline.md`; в существующих charter дописывать ничего не нужно (правила доставляются движком в рантайме).

## 2.5.0

Что нового в сгенерированном состоянии:

- шаблоны ролей: у reviewer маршрутизация блокеров явно ограничена ролями из charter (database/frontend/testing/devops при наличии), screenshots-gate принимает только tester-скриншоты по конвенции `<epic>-<phase>-<viewport>-<screen>`; у frontend self-check-скриншоты получили префикс `front-selfcheck-` (гейт reviewer'а они не закрывают); у testing — конвенция имён скриншотов с суффиксом `-FAIL` для падений; у product — режим UX-AUDIT (пост-релизный аудит UX/discoverability);
- charter: при PM-only составе PM track block содержит пометку «перед реализацией дополнить состав dev-дорожкой повторным `$qtim-setup`»; при выключенном independent review — секция-заглушка «выключен», а independent-review-требования в сгенерированные агенты не переносятся.

Миграция с 2.4.0:

1. Обнови `.codex/agents/qtim-reviewer.toml`, `qtim-frontend.toml`, `qtim-testing.toml`, `qtim-product.toml` по текущим templates (diff-подтверждение при ручных правках пользователя).
2. PM-only команды (в charter нет dev-маркеров): добавь в PM track block пометку про доукомплектование dev-дорожкой перед реализацией handoff-плана.
3. Команды, собранные с выключенным independent review: добавь в charter строку-заглушку «independent review выключен; включить — повторный `$qtim-setup`» и вырежи требования гейта из сгенерированных TOML (reviewer/architect/database), если они там остались.
4. Dev-команды с включённым гейтом и без PM track — только шаг 1.

## 2.4.0

Что нового в сгенерированном состоянии:

- working rules charter описывают session handoff: `memory/epic-state.md` (пишет `$qtim-team-down`, читает `$qtim-team-up`), уроки retro в `memory/retro-log.md` и `memory/lessons.md`;
- секция `Команда qtim` в `AGENTS.md` проекта упоминает `$qtim-team-retro`, `$qtim-onboard`, `$qtim-doctor`;
- `memory/MEMORY.md` описывает назначение `epic-state.md` / `retro-log.md` / `lessons.md` (сами файлы создаются skills по мере надобности, не setup).

Миграция с 2.3.0:

1. Добавь в working rules charter (общая секция, вне track-маркеров) описание session handoff — аккуратно, не перезаписывая ручные правки пользователя.
2. Добавь `$qtim-team-retro`, `$qtim-onboard`, `$qtim-doctor` в секцию `Команда qtim` в `AGENTS.md`.
3. Допиши в `memory/MEMORY.md` строки про `epic-state.md` / `retro-log.md` / `lessons.md`; существующие записи памяти не трогай.

Новые skills и рецепты оркестрации живут в плагине и миграции файлов проекта не требуют.

## 2.3.0

Что нового в сгенерированном состоянии:

- продуктовая память `memory/product-map.md` / `product-actors.md` / `product-glossary.md` / `product-metrics.md` — наполняется новым skill `$qtim-product-onboard` (setup её не создаёт);
- PM track block charter упоминает эти файлы как read-on-start роли `product` («если созданы»);
- шаблон `product.toml`: продуктовая память в Read first + правило «метрики PRD привязывать к событиям из product-metrics».

Миграция с 2.2.0 (только для команд с PM track):

1. Добавь в PM track block charter упоминание продуктовой памяти как read-on-start роли `product`.
2. Обнови `.codex/agents/qtim-product.toml` по текущему template (diff-подтверждение при ручных правках).
3. Порекомендуй пользователю прогнать `$qtim-product-onboard` на существующей кодовой базе.

Dev-only команды миграции не требуют.

## 2.2.0

Что нового в сгенерированном состоянии:

- version stamp: charter начинается с `<!-- qtim-version: X.Y.Z -->`, каждый сгенерированный `.codex/agents/*.toml` — с комментария `# qtim-version: X.Y.Z`;
- секция `Команда qtim` в `AGENTS.md` проекта упоминает `$qtim-update`;
- рекомендованный SessionStart hook показывает версию команды из stamp.

Миграция с 2.1.0:

1. Добавь `<!-- qtim-version: 2.2.0 -->` первой строкой `.codex/team-charter.md`.
2. Добавь `# qtim-version: 2.2.0` первой строкой каждого `.codex/agents/qtim-*.toml`.
3. Добавь `$qtim-update` в секцию `Команда qtim` в `AGENTS.md`.
4. Только при target-версии ниже 2.8.0 предложи обновить project SessionStart на версионированный вариант. При target 2.8.0+ этот шаг superseded: project-дубль удаляется, версионированный SessionStart поставляет плагин.

## 2.1.0

Что нового в сгенерированном состоянии:

- charter стал track-aware: dev и PM треки между маркерами `<!-- qtim:track:dev:start/end -->` и `<!-- qtim:track:pm:start/end -->`;
- PM track: роль `qtim-product` (`.codex/agents/product -> qtim-product.toml`), механика feature pipeline в charter, конвенция `docs/features/<slug>/`.

Миграция с 2.0.0:

1. Оберни существующее dev-содержимое charter (roles table dev-ролей, intake/autonomy) в маркеры `qtim:track:dev`.
2. Спроси пользователя, нужен ли PM track; если да — добавь блок `qtim:track:pm` с механикой pipeline (стадии, статусы, правила grounded-оценки, handoff) и сгенерируй `qtim-product` из template.
3. Существующие правки пользователя в charter вне маркеров не трогай.

## 2.0.0

Baseline Codex-native упаковки: `.codex/team-charter.md`, `.codex/agents/*.toml`, `.codex/hooks.json`, `memory/`, `AGENTS.md`.

Миграция с 1.x (legacy `.claude/*`, `CLAUDE.md`): автоматической миграции нет — прогнать `$qtim-setup` заново; legacy-файлы не удалять без явной просьбы пользователя.

## Общие правила миграции

- Не даунгрейдить: если stamp проекта новее версии установленного плагина, обнови сам плагин, а не проект.
- `memory/` и `docs/features/` при миграции не переписываются.
- Изменённые пользователем файлы не перезаписывать молча: показать diff и спросить.
- Пользовательские hook events/groups/handlers не удалять и не переупорядочивать; менять только распознанные qtim entries после показанного diff.
- После каждой полностью завершённой version-section обнови оба stamp (charter и все qtim TOML) только до версии этой секции. При `pending` остановись на последней полностью завершённой версии; до текущей версии плагина stamps дойдут лишь после успешного применения всего диапазона.
- При любой миграции проверяй атомарную пару `model` + `model_reasoning_effort` в сгенерированных `.codex/agents/*.toml`: для target 2.10.0 это exact current template или явный catalog-supported пользовательский override; отсутствие обоих полей допустимо только как подтверждённый compatible override наследования. Боевой инцидент: setup сгенерировал несуществующий `model = "gpt-5"` (слаг без минорной версии), и все субагенты не стартовали. Фикс: доступная exact pair из template/подтверждённого override; одинокий pinned model/reasoning не оставлять, alias не угадывать.
