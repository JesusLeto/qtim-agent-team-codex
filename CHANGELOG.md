# Changelog

Версии соответствуют `version` в `plugins/qtim/.codex-plugin/plugin.json` (semver).

## 2.15.0 — 2026-10-02

Исправления по аудиту использования qtim: ограниченные повторные проверки и
управляемая актуализация проектной памяти.

### Добавлено

- `$qtim-kb-refresh` проверяет дрейф `memory/` относительно выбранной Git-базы,
  инвентаризует `docs/features/`, предлагает ограниченный объём обновления и
  сверяет сохранность информации перед завершением.
- `$qtim-kb-format` задаёт единый компактный формат фактов и проверяемых ссылок
  на код; `$qtim-doctor` сообщает о признаках устаревания базы знаний.

### Изменено

- После первого reviewer pass фазы допускаются не больше двух целевых
  fix-and-recheck раундов. Полное повторное review требуется при изменении
  поверхности риска; нерешённый blocker получает явный `Blocked` и решение
  владельца. Обязательные security, acceptance и ADR gates сохранены.
- Approved scope и явные ограничения пользователя имеют приоритет над
  расширением по находкам review. Intake проверяет ключевую доменную
  предпосылку; утверждённый план разрешает последующие фазы без повторных
  стартовых подтверждений.
- Полный PM-трек допускает результат PRD-only; `estimate.md` создаётся при
  практической необходимости или по запросу. Завершённые фичи получают
  контролируемый статус `Archived`, одноразовые материалы живут в `.work/`.
- Onboard и retro записывают сжатые факты, обновляют существующие записи и
  направляют устаревшие evidence в `$qtim-kb-refresh`.

### Совместимость

- Изменения generated charter, managed `AGENTS.md` и reviewer role применяются
  через `$qtim-update` по секции 2.15.0 в upgrade notes. После обновления
  agent TOML нужна новая задача Codex.
- Форк публикуется из `JesusLeto/qtim-agent-team-codex`; ссылки установки и
  репозитория указывают на него.

## 2.14.0 — 2026-08-17

Обязательный language contract для всей qtim-команды: internal reasoning и
peer-agent communication на English, user-facing результаты на Russian.

### Изменено

- Все шесть канонических agent TOML получили дословный `## Language` block;
  `$qtim-setup` переносит его также в project-specific Extended-роли, общий charter
  и managed qtim contract в `AGENTS.md`.
- `$qtim-update` мигрирует существующие qtim TOML/charter/`AGENTS.md` без замены
  целых prompts и оставляет конфликтующее пользовательское language rule pending
  до явного подтверждения.
- Team-up, lazy, feature/onboard и mission fan-out теперь явно составляют prompts
  и follow-ups на English; документы, findings и клиентский handoff остаются на
  Russian.
- `$qtim-doctor` и repository validation проверяют contract во всех слоях
  generated state.

## 2.13.0 — 2026-07-30

Семантический Codex-порт Claude qtim 1.13.0: дисциплина минимального
полноценного объёма, её generated-state migration и operational feedback loops.

### Добавлено

- `$qtim-minimal-diff` с Codex UI metadata: семиступенчатая лестница
  `нужно ли вообще -> уже есть в проекте -> standard library -> platform/framework
  primitive -> установленная dependency -> одна операция -> минимальная
  реализация`. Skill остаётся role-agnostic practice без fan-out и собственной
  схемы отчёта.
- Protected zones нельзя срезать лестницей или marker'ом: trust-boundary
  validation, обработка ошибок против потери данных, security/access,
  accessibility, explicit user behavior, approved acceptance criteria и
  документированные инварианты. Для нетривиальной логики обязательна одна
  минимальная breaking check на существующем runner или executable assertion.
- Architect сравнивает объём design-вариантов; database/frontend применяют
  лестницу до нетривиальной реализации; reviewer отправляет чистую избыточность
  в рекомендации, но сохраняет blockers по scope, protected zones, инвариантам
  и gates.
- `$qtim-doctor` read-only сопоставляет roster с наблюдаемыми CI/data/public/
  monorepo signals. Drift всегда `warn`: supported role ведёт в отдельный
  additive `$qtim-setup`, unsupported responsibility — к decision owner.
- `$qtim-team-retro` классифицирует epic-scoped `minimal-diff:` markers как
  triggered/not-triggered/unknown/malformed/protected. Только доказанно
  triggered marker получает durable follow-up в `memory/retro-log.md` с source,
  evidence, одним owner и next action.
- `$qtim-debug-loop` до production fix называет root seam, все обнаружимые call
  sites/adjacent paths и явные dynamic/generated/external coverage gaps.
- Fail-closed `.github/scripts/check_skill_refs.py`: полный `$qtim-*` token,
  фиксированные scan surfaces, ненулевой coverage и self-tests для typo,
  invalid suffix, zero references и missing surface.
- Полный MIT notice Dietrich Gebert / ponytail и maintainer rule для следующих
  third-party MIT adaptations.

### Generated state и совместимость

- `$qtim-setup` считает minimal-diff Layer 0 practice, показывает additions до
  записи и остаётся additive на re-run: роли не удаляются, соседний track,
  manual regions и atomic model overrides сохраняются.
- `$qtim-update` получает region-aware migration `2.12.0 -> 2.13.0`.
  Роль сопоставляется только по charter/filename/TOML evidence; ambiguity,
  missing or renamed target остаётся `pending`, без duplicate/whole-file
  overwrite. QTIM-generated Extended/code-writing role без bundled template
  получает отдельный additive self-contained contract; foreign agents, manual
  text, track blocks и atomic model override сохраняются. Stamps всех
  сопоставленных qtim roles повышаются только после всех applicable steps.
- Repo-local Extended migration fixture фиксирует positive preservation path:
  custom `qtim-devops`, foreign agent/hook, ручная инструкция, оба track block
  и user model override; negative oracles отклоняют потерю любого manual byte,
  qtim-looking foreign near-miss и преждевременный target stamp при ambiguous/
  partial custom role.
- Без project migration новый skill доступен после plugin update и новой задачи
  Codex, но старые generated roles его не вызывают. После `$qtim-update`,
  изменившего role TOML, также требуется новая задача.
- Rollback не удаляет пользовательские роли, memory или `minimal-diff:`
  comments; корректировка delivered contract идёт следующим semver и
  region-aware migration.

### Не перенесено из Claude runtime

- `.claude/*`, slash commands, Agent Teams/`Task*`, agent-memory,
  Standalone-copy и Claude command namespace. Codex использует `$qtim-*`,
  `.codex/*`, explicit atomic model pairs, task-scoped threads и общий
  `memory/`.

## 2.12.0 — 2026-07-28

Полный Mission Plan Codex: shape-based routing после `$qtim-feature` и App-first
cross-dialog DAG с read-only/lazy/writer nodes, проверяемой интеграцией,
verification loop и recovery.

### Добавлено

- `$qtim-mission` с UI metadata и implicit loading только для fail-closed
  activation classifier. Явный запуск через skill с глаголом исполнения и
  Approved source/multi-peer shape,
  недвусмысленную просьбу провести несколько Codex peer tasks как одну mission
  или referential approval непосредственно предшествующего полного Approved
  preview создаёт только ready peer-задачи. Одна обычная задача/диалог,
  planning-only запрос, `PREVIEW`, `RECOMMEND`, SessionStart advisory, любой
  quote/code marker, условие/отсрочка, вопрос и отрицание не вызывают
  `create_thread`.
- Portable mission evidence в `memory/missions/<slug>/`, opaque runtime hints в
  gitignored `.codex/qtim-runtime/`, worker/integration receipts, dependency
  context pack и node state machine до `validated | integrated | verified`.
- App capability preflight для `list_projects`/thread tools, fail-visible
  `clientThreadId` reconciliation, batches до восьми wait targets и честный
  `$qtim-team-up` fallback без обещания peer tasks на CLI/IDE.
- `execution: lazy`: Approved Sol/Ultra node lead запускает `$qtim-team-lazy` в
  mission-child mode, выбирает minimum-sufficient roles и возвращает один
  агрегированный receipt; explicit writer/read-only policy, canonical
  read/write scopes, Approved role allowlist, pairwise write-scope disjointness
  и product-fork flag проверяются, а feedback loop/new role/scope conflict/product
  fork возвращают только `BLOCKED` + `ESCALATION_REQUEST`; любой escalation
  marker также требует `BLOCKED`.
- Isolated git writer contract: отдельные clean integration/state worktrees,
  монотонные scoped portable checkpoints, один non-merge writer commit,
  detached App writer worktree без shared attempt ref, detached
  transaction-worktree cherry-pick без shared transaction ref, affected gate и только затем fenced
  promotion под exclusive lock из clean integration worktree: full commit ids,
  ff-only ancestry, atomic exact-old `update-ref`, exact tree sync и exact-final
  clean status с проверяемым rollback.
  Red gate/conflict/scope violation/foreign drift не сдвигают Approved HEAD и
  блокируются без auto-stash/force. После final `APPROVED` один scoped evidence
  bundle доставляется тем же gate, затем отдельный clean checkpoint фиксирует
  `Done`, новый sequence и exact delivered revision; crash-window reconciliation
  идемпотентна.
- Clean-context final verifier с exact full-line `APPROVED | NOT APPROVED`
  parser (literal spacing/no indentation, последняя exact запись authoritative),
  проверкой findings, bounded fix
  nodes и последним completion marker `Done`.
- `status`, `resume`, `stop`, single-owner takeover через exclusive ownership
  lock, generation re-read, file `fsync + atomic replace` и parent-directory
  fsync, классификации
  `live/pending/stale/orphan/ambiguous/unavailable` и пассивный SessionStart
  advisory без auto-resume/auto-archive. Scan ограничен 50 candidates/5 records;
  portable `Verifying` подавляется при authoritative `Done` на exact state ref.
- `.github/scripts/check_missions.py`: semantic activation/routing/DAG fixtures,
  reserved terminal verifier, edge contracts, state transitions, writer/lazy
  receipts, monotonic multi-checkpoint/crash-blocked и post-delivery recovery с
  zero side effects, competing ownership/promotion locks, stale promotion, red
  gate, conflict abort, единый fail-closed writer/lazy scope parser с
  Unicode controls, env/home, extended globs, case-folded `.git` и Windows
  reserved aliases, NFC/case-fold overlap и symlink/junction containment,
  immutable read-only raw type/mode/inode/link/bytes filesystem +
  `GIT_OPTIONAL_LOCKS=0`, common refs/config/control, exact `.git` identity,
  full common-worktree registry и per-worktree index/admin guard; hard
  50 000-entry/512-MiB budget, special-file и hardlink rejection. Writer guard
  требует detached `expectedBase -> commit` без shared ref, frozen admin/config,
  canonical index flags, single-link content и nested submodule
  config/control/hooks/packed-refs baseline. Root/directory junction
  отвергается до traversal и проверяется реальным Windows CI fixture. Writer startup
  двухфазный: no-edit READY, coordinator baseline всей wave и exact follow-up
  authorization. Coordinator journals
  отдельно ограничивают exact state checkpoint, App worktree additions и
  current-mission registry before/after transition; state delete/recreate и
  integration/foreign drift запрещены. Runtime/portable paths проходят
  component-wise lstat/realpath/same-filesystem containment; ownership/promotion
  используют разные deterministic `<slug>.*.lock` с owner/generation binding.
  First-run runtime/portable parents создаются component-by-component с
  containment revalidation; initial registry публикуется под ownership lock
  через exclusive temp + fsync + atomic no-clobber, поэтому collision не
  перезаписывает чужое состояние. Takeover делает exact regular/single-link
  final read до снятия ownership lock; promotion держит canonical locks только
  `ownership -> promotion` и перечитывает generation под обоими до CAS.
  Complete terminal verifier
  и exact full-subtree final evidence delivery с
  deletion/APPROVED/durable-Done gates; hook tests проверяют passive
  unfinished-mission advisory.

### Изменено

- `$qtim-feature` всегда завершает Approved artifact блоком «Что запускать дальше»:
  рекомендация, причина, topology, готовая команда и альтернатива. Direct,
  team-lazy, team-up и mission выбираются по outcomes/dependencies/context
  isolation/feedback loops, а не только по S/M/L/XL. Полностью Approved graph
  получает `запусти`, unresolved writer/lazy/runtime choice — `preview`.
- Runtime/model/orchestration/doctor references знают границы peer tasks,
  configured-default model для direct nodes, Approved Sol/Ultra lazy lead,
  worktree integration и mission recovery.
- Setup и migration 2.12 синхронизируют PM track charter, managed qtim block в
  project `AGENTS.md`, on-demand mission entry в `memory/MEMORY.md` и exact
  `.codex/qtim-runtime/` ignore, сохраняя чужой track и пользовательский текст.
- ADR-001 фиксирует split checkpoint-state/integration worktrees, atomic
  coordinator ownership и transaction gate + locked full-OID ancestry/atomic
  exact-old ref CAS/exact-final clean-tree promotion вместо shared checkout или
  handoff-as-merge.

### Совместимость

- Full mission mode доступен только на App surface с callable peer tools.
  CLI/IDE получают честный `$qtim-team-up` fallback.
- Runtime handles остаются last-known hints; недоказанный worktree/host/base
  блокирует конкретную операцию. Новая задача Codex после переустановки нужна,
  чтобы увидеть skill и обновлённый lifecycle hook.

## 2.11.0 — 2026-07-28

Семантический Codex-порт общих принципов Claude-релиза 1.12: надёжная доставка
runtime-контракта, fail-safe quality gates, атомарный resume и проверяемые миграции.

### Добавлено

- `$qtim-setup` пишет компактный managed block в корневой `AGENTS.md`, который Codex
  загружает автоматически; подробный charter и memory остаются self-contained источниками.
- Reviewer механически ограничен `sandbox_mode = "read-only"` и явно сообщает, какой
  adversary использован. Tester владеет запуском сохранённой `DEV_CMD`.
- Opt-in `SubagentStop` screenshot gate для `qtim-testing`: свежие tester-артефакты,
  исключение `front-selfcheck-*`, максимум один controlled retry через `stop_hook_active`.
- `reference/runtime-compat.md`, migration gate и semantic golden full-stack project в CI.

### Исправлено

- Stage 6 PM-конвейера теперь пишет plan/brief/prompts до последнего completion marker в
  `memory/decisions.md`; Approved без pointer корректно возобновляет handoff.
- Разведены владельцы PM-контрактов: skill управляет сессией, reference — долговечными
  артефактами, charter содержит производную самодостаточную сводку.

### Не портировано

- Claude-only `.claude/rules`, Agent Teams flags, `Task*` API и agent-memory: Codex использует
  `AGENTS.md`, custom agents, task-scoped threads и `memory/`.

## 2.10.0 — 2026-07-27

Семантический Codex-порт Claude-релиза 1.11.0 из upstream-коммита [`93fd017`](https://github.com/toiiia/qtim-agent-team/commit/93fd017446cedc805ccd7f2ab1e0370372e87b17): явные профили ролей вместо inheritance и независимый stress-test каждого ADR. Codex-матрица сверена с актуальным runtime catalog и официальной GPT-5.6 guidance: [Sol/Terra/Luna](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6), [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents). Сгенерированное состояние меняется — миграция описана в `reference/upgrade-notes.md`, запись «2.10.0».

### Изменено

- **Оркестрация отделена от ролевой работы:** qtim team-lead запускается на `gpt-5.6-sol` + `ultra`; плагин не переключает уже открытый task, а setup/charter/doctor фиксируют профиль как prerequisite. `Ultra` разрешает proactive delegation только внутри явно вызванного qtim workflow и не меняет execution depth A/B/C/D.
- **Роли получили явные GPT-5.6 pair:** architect/reviewer — Sol+xhigh; database/frontend/product — Sol+high; testing — Terra+medium; built-in explorer без TOML — Luna+medium. Это возвращает quality floor гейт-ролям и не связывает их глубину с тем, какой профиль выбран для main task.
- **Fallback стал fail-visible:** недоступная qtim pair больше не удаляется молча ради inheritance. Setup/update предлагает обновить Codex или подтвердить catalog-supported override; миграция остаётся pending. Atomic user overrides сохраняются через diff.

### Добавлено

- **Независимый stress-test каждого ADR до approval:** после `$qtim-grill` main thread поднимает отдельного read-only оппонента без истории на Sol+xhigh. Для необратимого решения, затрагивающего документированный инвариант, effort повышается до `max`. Findings верифицирует architect; итог остаётся в ADR строкой `adr-stress-test: sol-adversary (xhigh|max) — N findings, M учтено`.
- **ADR gate не зависит от code-review toggle:** optional risk-based review фактического diff можно выключить, но clean-context Sol adversary для созданных ADR остаётся обязательным. Техническая недоступность thread фиксируется как `skipped — <reason>` и не выдаётся за пройденный review.
- **CI-контракт модели и ADR review:** `check_codex_agents.py` проверяет exact pairs всех templates и маркеры team-lead/explorer/adversary policy.

### Codex-специфичная адаптация

- В Claude second opinion может приходить из другого семейства моделей. В Codex независимость обеспечивается новым thread с `fork_turns = "none"` (или runtime-эквивалентом) и минимальным context pack; качество закреплено Sol, а самый рискованный ADR получает `max`.
- Искусственный dual-review двумя одинаковыми Sol agents по умолчанию не добавлен: при «необратимо + инвариант» усиливается reasoning одного чистого adversary. Дополнительные линзы остаются risk-based orchestration choice main thread.

## 2.9.0 — 2026-07-21

Семантический Codex-порт Claude-релизов 1.9.0 + 1.10.0 из upstream-коммита [`fc0f8e9`](https://github.com/toiiia/qtim-agent-team/commit/fc0f8e9b7a1bb2d9c4ab27f2dd14cef72331833a): frontier-model policy, риск-пропорциональный PM-конвейер и четыре собственные дисциплины qtim. Сгенерированное состояние меняется — миграция описана в `reference/upgrade-notes.md`, запись «2.9.0».

### Добавлено

- **`$qtim-debug-loop`** — красный автоматический feedback loop до гипотез, минимизация repro, 3-5 фальсифицируемых гипотез до первой проверки, один probe за раз, `[DEBUG-*]` cleanup, регрессионный тест до фикса. Database/frontend/testing templates используют дисциплину для нетривиальных и flaky-багов.
- **`$qtim-prototype`** — одноразовый terminal/UI prototype для конкретной design-развилки; решение фиксируется в design artifact, production-код реализуется заново, throwaway-код в main не остаётся.
- **`$qtim-brainstorm`** — обязательный разбор до ADR: минимум две интерпретации, факты из окружения, 2-3 жизнеспособных варианта с trade-offs, open questions отдельно от assumptions.
- **`$qtim-grill`** — stress-test плана по одному вопросу с рекомендуемым ответом; поддерживает жёсткий self-play.
- Новые skills имеют Codex UI metadata `agents/openai.yaml`; repo CI валидирует обязательные поля, длину description и `$skill` в default prompt.
- MIT notice источника входит в распространяемый plugin subtree как `THIRD_PARTY_NOTICES.md`.

`debug-loop`, `prototype` и `grill` — Codex-адаптации дисциплин из [mattpocock/skills](https://github.com/mattpocock/skills), MIT; `brainstorm` — qtim-выжимка intake protocol.

### Изменено

- **`$qtim-feature` стал двухтрековым:** S/M одной фазы без Fork Test triggers идёт через `feature-brief.md` с одним checkpoint вместо стадий 2-5; многофазные/рискованные задачи сохраняют полный PRD -> decomposition/estimate -> plan. Resume, handoff, team-up, team-lazy, retro и doctor понимают оба трека.
- **Полный трек компактнее:** decomposition и estimate утверждаются одним решением; consult запускается только для реально затронутых слоёв; production code/SQL/будущие диффы запрещены внутри PM-артефактов.
- **Vertical slicing:** work item и фаза — проверяемый вертикальный срез с одним DRI и contributing roles; в полном треке роли оценивают layer slices, DRI синтезирует item estimate, а fast-path использует main-thread evidence fallback. Широкий механический rename/retype планируется expand-contract.
- **Факт vs решение:** main thread и роли сами собирают факты из кода, `memory/`, git и документации; пользователю выносятся только решения, которые evidence не разрешает.
- **Architect:** `$qtim-brainstorm` до ADR, `$qtim-prototype` для UX/behavior fork, `$qtim-grill` для stress-test; ADR пишется только при одновременных «дорого откатить» + «будущий читатель спросит почему» + реальном trade-off, иначе — строка в `memory/decisions.md`.
- **Independent review пропорционален риску:** единая high-risk matrix покрывает security/auth/visibility, money/account state, documented invariants/public contracts, data-transform/destructive migrations, critical browser flows, high-risk performance/reliability и другие hard-to-rollback изменения; low-risk diff допускает `independent review: skipped (low-risk diff)`; main thread проверяет findings и владеет spawn.
- **Model inheritance:** architect/database/frontend/reviewer/product больше не приколочены к поколению модели — в их TOML отсутствуют оба model fields, поэтому они наследуют session profile. Testing сохраняет bounded pair `gpt-5.6-terra` + `medium`. В Codex строка `model = "inherit"` не используется; пользовательские overrides атомарной pair сохраняются.

### Codex-специфичная адаптация

- Claude slash calls `qtim:*` переписаны в Codex skills `$qtim-*`; standalone-копирование `.claude/skills/` и golden example не применимы.
- Claude Codex second-opinion адаптирован как отдельный read-only Codex agent thread по `independent-review.md`, а не внешний консультант.
- Компенсирующий пошаговый composable-рецепт не удалялся: Codex frontend template уже содержит только компактные инварианты.

## 2.8.0 — 2026-07-10

Исправлен Codex hook-контракт после Claude-порта. Bundled `hooks.json` уже имел правильную вложенную форму, но setup мог генерировать project-level `type: reminder`, дублировать bundled events, а event-specific stdout не соответствовал текущему runtime. Основание — официальная документация [Hooks](https://learn.chatgpt.com/docs/hooks): hook layers складываются, `PostToolUse` игнорирует plain stdout, `SubagentStop` при exit 0 ожидает JSON.

Сгенерированное состояние меняется — миграция описана в `reference/upgrade-notes.md`, запись «2.8.0».

### Исправлено

- **Bundled hooks**: `SubagentStop` теперь возвращает JSON `systemMessage`, не меняя continuation flow; обе команды находят charter от git root, поэтому работают при запуске Codex из подкаталога.
- **Windows**: для bundled и project hooks добавлены `commandWindows` с PowerShell/UTF-8 вместо POSIX-команд, которые не исполнялись в `cmd.exe`.
- **Разделение слоёв**: `$qtim-setup` больше не копирует `SessionStart` / `SubagentStop` в `.codex/hooks.json`; эти события принадлежат plugin layer, project layer содержит только явно выбранный `PostToolUse`.
- **Рабочий PostToolUse**: plain reminder заменён на JSON `hookSpecificOutput.additionalContext`, который действительно попадает в model-visible context.

### Добавлено

- `reference/project-hooks.json` — machine-readable канон optional project hook, который setup мержит без перезаписи пользовательских groups.
- `$qtim-doctor` проверяет schema, ownership и event-specific output; `$qtim-update` безопасно мигрирует только распознанные qtim handlers через показанный diff.
- `check_hooks.py` валидирует schema и выполняет POSIX/Windows-команды в temp git-проекте (включая путь с кириллицей и `[]`): no-charter no-op, versioned `SessionStart`, JSON `SubagentStop` и JSON `PostToolUse`; workflow запускает отдельный `windows-latest` job.

## 2.7.0 — 2026-07-10

Адаптация qtim под Codex CLI 0.144.1 и новый модельный/runtime-контракт: GPT-5.6 Sol/Terra/Luna, reasoning `Max`/`Ultra`, proactive delegation и task-scoped descendant threads. Основание — официальные [Models](https://developers.openai.com/codex/models), [Subagents](https://developers.openai.com/codex/subagents) и [Codex changelog](https://developers.openai.com/codex/changelog); точные пары дополнительно сверены с локальным model catalog Codex 0.144.1. Сгенерированное состояние меняется — миграция описана в `reference/upgrade-notes.md`, запись «2.7.0».

### Изменено

- **Ролевые модели обновлены до GPT-5.6**: architect/database/reviewer/product — `gpt-5.6-sol` + `high`, frontend — `gpt-5.6-sol` + `medium`, testing — `gpt-5.6-terra` + `medium`. Используются точные variant slugs из runtime catalog, чтобы не повторить инцидент с догаданным `gpt-5`.
- **Root reasoning отделён от role profiles**: `Max`, `Ultra` и Fast остаются пользовательскими controls главного task; qtim их не включает скрыто и не закрепляет в child agents. `Ultra` может proactively делегировать только внутри scope явно вызванного qtim workflow и не выбирает execution depth A/B/C/D.
- **Оркестрация учитывает новый agent graph**: main thread проверяет доступные Active/Done descendants перед повторным spawn, переиспользует reachable threads, владеет дополнительным fan-out и запускает batches при нехватке runtime slots. Child agents больше не должны рекурсивно поднимать qtim-команду; reviewer возвращает запрос на independent review main thread.
- **Fallback модели стал атомарным**: при недоступном slug setup/update/team-up удаляют пару `model` + `model_reasoning_effort`, наследуя корректный профиль главного task, а не оставляют pinned reasoning на неизвестной модели. Явные пользовательские overrides сохраняются через diff-подтверждение.
- **Терминология liveness уточнена**: agent threads task-scoped, но не являются скрытой постоянной командой; после resume сначала проверяется текущий runtime, и только затем спавнятся недостающие роли.

### Добавлено

- `reference/model-profiles.md` — единый контракт model/reasoning по ролям, правила `Max`/`Ultra`/Fast, pair fallback и связь с execution depth.
- `$qtim-doctor` диагностирует устаревшие qtim defaults, отсутствующие/retired модели по фактическому runtime catalog, разорванную model/reasoning пару и неожиданные `max`/`ultra`/Fast overrides.
- CI-проверка custom-agent templates теперь валидирует reasoning effort и точную матрицу профилей 2.7.0, а не только форму model slug.

### Осознанно не включено

- `max`, `ultra` и `service_tier = "fast"` не прописаны в role TOML: они меняют глубину/стоимость работы и требуют явного выбора пользователя.
- `gpt-5.6-luna` не назначена постоянной роли: текущие роли qtim требуют более широкого tool use и проверки; Luna остаётся кандидатом для будущих узких повторяемых workers.
- Рекурсивная делегация не включена: qtim сохраняет main-thread ownership agent graph и bounded fan-out.

## 2.6.0 — 2026-07-06

Порт улучшений Claude Code-версии 1.7.1 и 1.8.0 ([toiiia/qtim-agent-team](https://github.com/toiiia/qtim-agent-team), коммиты 1b122b6 и 6c4608f) под Codex-конвенции. Сгенерированное состояние проектов не меняется — `reference/upgrade-notes.md`, запись «2.6.0» (миграция не требуется).

### Изменено

Три точечных усиления PM-конвейера по мотивам «Слепых зон в промптинге» (Thariq Shihipar, перевод на Хабре): стадии конвейера — это систематическое сокращение неизвестных, и в трёх местах оно протекало.

- **Intake как интервью** (`$qtim-feature`, Stage 1): вместо «структурированные вопросы одним компактным блоком» — итеративное интервью порциями по 1-3 вопроса, где каждая следующая порция строится на полученных ответах, а первыми идут вопросы, сильнее всего меняющие постановку; остановка — когда новые ответы перестают менять понимание. Выравнивает стадию с каноном intake-протокола («анализ и проектирование — пользователь в контуре»).
- **Фиксация отклонений от плана** (handoff contract): реализующая сторона записывает отклонения от `plan.md` с обоснованием и всплывшие edge cases строкой в append-only «Историю изменений» `plan.md` — раньше они испарялись в чате реализующей сессии. Даёт готовый материал ретроспективе и resume многофазных фич. Правило доставлено по всей цепочке: строка в handoff-шаблоне `$qtim-feature`, дубль на реализующей стороне (`$qtim-team-up` preconditions + reporting, `$qtim-team-lazy` шаг 2), новый источник фактов в `$qtim-team-retro`, контракт и анти-паттерн «молчаливое отклонение» в `reference/feature-pipeline.md`.
- **Порядок фаз плана по неопределённости** (`$qtim-feature`, Stage 5 + `feature-pipeline.md`): решения, которые вероятнее всего изменятся (модель данных, контракты API, UX-развилки), — в ранние фазы, механическая доводка — в хвост; так самое дорогое для переделки проверяется раньше всего.

### Добавлено

- **`$qtim-doctor`, пункт «PM-трек»** — проверка продуктовой памяти: созданные `memory/product-*.md`, не вписанные в read-on-start роли `product` в charter, -> warn (роль слепа к готовой памяти); отсутствие файлов -> info с рекомендацией `$qtim-product-onboard` (канон «если созданы» — не ошибка). Порт их 1.7.1 (финдинг ревью PR #3).

### Не портировано (Claude-специфика)

- Бамп штампа golden-примера — в Codex-версии нет каталога `examples/`.
- Оговорка migrations про dev-only standalone (адаптация владельца при слиянии PR #3) — в Codex-версии нет standalone-режима.

## 2.5.0 — 2026-07-03

Порт аудит-фиксов Claude Code-версии 1.6.0 ([toiiia/qtim-agent-team](https://github.com/toiiia/qtim-agent-team), коммит 92985d1) под Codex-конвенции + выравнивание с 1.5.0-адаптацией владельца (режим UX-AUDIT). Миграция сгенерированного состояния — `reference/upgrade-notes.md`, запись «2.5.0».

### Исправлено

- **Рецепты оркестрации стали fail-closed** (`reference/orchestration-patterns.md`, аналог их правок `ensemble-review.mjs`/`flaky-hunt.mjs` — у нас рецепты текстовые, исполняет main thread): в Ensemble Review сбой скептика или целой линзы больше не читается как «дефекта нет» — неопровергнутые findings идут в отчёт блоком «требуют ручной проверки», findings сверх лимита верификации не выбрасываются, а правило вердикта main thread применяет детерминированно сам (NOT APPROVED при любом подтверждённом **или неверифицированном** P0/P1 и при упавшей линзе — синтез может только ужесточить); в Flaky Hunt сбой прогона считается отдельно от зелёных, серия сбоев даёт честное «ни один прогон не состоялся» вместо ложного «стабильно».
- **Канон оси A/B/C/D**: Execution Depth явно меряется глубиной координации (петли implement -> test -> review), выбор режима подсчётом ролей — anti-pattern; в Classify And Act зафиксировано, что классификатору делегируется только слой/severity/владелец, а выбор execution depth — работа main thread (матрица субагенту недоступна).
- **Screenshots-gate различает tester и front**: self-check-скриншоты frontend получили префикс `front-selfcheck-`, tester именует sweep-скриншоты `<epic>-<phase>-<viewport>-<screen>` (падения — `-FAIL`), reviewer закрывает гейт только tester-скриншотами; маршрутизация блокеров reviewer'а явно ограничена ролями, реально существующими в charter (database/frontend/testing/devops при наличии).
- **Выключенный independent review согласован по конвейеру** (аналог их Q5=No): setup при disabled пишет в charter секцию-заглушку «выключен» и вырезает independent-review-требования из генерируемых агентов (reviewer/architect/database) как gate-условные блоки; `$qtim-team-up` не требует гейт при заглушке; `$qtim-doctor` ловит рассинхрон (заглушка в charter + требования гейта в TOML); Phase 5 setup проверяет согласованность.
- **PM-состав честен про реализацию**: setup и PM track block charter помечают, что PM-состав (без `qtim-reviewer`) рассчитан на конвейер документов — перед запуском handoff-плана в разработку состав дополняется dev-дорожкой повторным `$qtim-setup`; предупреждение продублировано в handoff `$qtim-feature` (Stage 6).
- **Реестр решений и фич канонизирован до конца**: `$qtim-onboard` (синтез) и `reference/intake-protocol.md` (шаг 8) ссылаются на `memory/decisions.md` по имени, как остальные потребители.
- **CI**: `check_placeholders.py` ловит несбалансированные скобки плейсхолдеров (`{{FOO}` / `{FOO}}`) в `*.md` и `*.toml`.
- **README**: шкала оценок PM-конвейера — S/M/L/XL (была занижена до S/M/L).

### Добавлено

- **Режим UX-AUDIT у роли `product`** (выравнивание с их 1.5.0: владелец сохранил UX-аудит из Extended-каркаса при слиянии PR #1): пост-релизный аудит UX и discoverability — findings P0-P3 в финальном отчёте, задачи исполнителям раздаёт team-lead (в Codex субагент не создаёт задачи сам).
- Запись «2.5.0» в upgrade-notes (миграция шаблонов ролей; для PM-only и disabled-review команд — правки charter).

### Не портировано (Codex-специфика)

- Правки Workflow-скриптов как код и CI-запреты `Date.now()`/`Math.random()` — в Codex нет Workflow-движка, семантика перенесена в текстовые рецепты (см. «Исправлено»).
- Standalone-ветки doctor/team-sync, локализация командных имён, Q7-дубли hooks — в Codex-версии нет standalone-режима.
- Проверка резолвинга абсолютных путей протоколов при переносе проекта — Codex-charter самодостаточен (протоколы инлайнятся, путей в charter нет).
- Якорение hooks на каталог проекта (`$CLAUDE_PROJECT_DIR`) — у Codex-рантайма нет подтверждённого аналога переменной; hooks остаются advisory echo и при запуске не из корня просто молчат.
- `sh -n` hook-скрипта и канон-grep по `examples/` — hooks инлайновые, каталога examples нет.
- `color: cyan` у tester — в Codex agent TOML нет поля `color`.

## 2.4.0 — 2026-07-02

Порт dev-улучшений Claude Code-версии плагина 1.3.0–1.4.0 ([toiiia/qtim-agent-team](https://github.com/toiiia/qtim-agent-team)) под Codex-конвенции. Аналоги `/qtim:team-sync` и `reference/migrations.md` не портировались — их роль уже закрывают `$qtim-update` и `reference/upgrade-notes.md` (2.2.0).

### Добавлено

- **Skill `$qtim-team-retro`** — ретроспектива эпика (порт `/qtim:team-retro`): анализ петель/блокеров/повторяющихся классов проблем по фактам сессии и дистилляция уроков «триггер -> действие» в `memory/retro-log.md` и в секции ролей `memory/lessons.md`. Вместо Claude agent-memory (в Codex нет per-role памяти) уроки ролей живут в `memory/lessons.md`, а prompt template `$qtim-team-up` включает секцию роли в read-first — уроки доживают до следующей сессии, хотя agent threads — нет.
- **Epic-state / handoff между сессиями** (порт из 1.4.0): `$qtim-team-down` при незавершённом эпике пишет `memory/epic-state.md` (фаза, сделано, «в полёте», следующий шаг) и удаляет его после завершённого; `$qtim-team-up` в новой сессии читает его и предлагает продолжить. Team-down перед сворачиванием напоминает про `$qtim-team-retro`.
- **Skill `$qtim-onboard`** — глубокий онбординг dev-памяти (порт `/qtim:onboard`): план -> подтверждение объёма -> fan-out read-only исследователей по подсистемам -> синтез карты/инвариантов/конвенций в `memory/` с прецедентами `file:line`. Дополняет `$qtim-product-onboard`: тот смотрит глазами пользователя, этот — инженера.
- **Skill `$qtim-doctor`** — read-only диагностика (порт `/qtim:doctor`, чеклист переписан под Codex): манифест плагина, stamp и track-маркеры charter, целостность `.codex/agents/*.toml` (TOML parse, плейсхолдеры, plugin-internal пути), hooks.json и trust, память и устаревший epic-state, артефакты PM-трека, доступность skills из charter. Вывод — таблица pass/warn/fail с конкретными фиксами; безопасные фиксы по подтверждению.
- **Рецепты оркестрации** в `reference/orchestration-patterns.md` (адаптация Workflow-скриптов 1.4.0 — в Codex нет Workflow-движка, рецепты исполняет main thread явными subagent threads): Ensemble Review (линзы -> скептик-верификация каждого finding -> синтез-вердикт), Access Audit (fan-out по сущностям -> карта видимости + щели на стыках), Flaky Hunt (loop-until-trace со stop-условиями).
- Setup: working rules charter описывают session handoff (epic-state, retro-log, lessons); генерируемая секция `AGENTS.md` и handoff упоминают новые skills; на существующей кодовой базе рекомендуется `$qtim-onboard` / `$qtim-product-onboard`, при проблемах — `$qtim-doctor`.
- Запись `-> 2.4.0` в upgrade-notes.

### Исправлено

- **Setup мог сгенерировать несуществующий `model` в агентах** (боевой инцидент: `model = "gpt-5"` — субагенты не стартовали, в шаблонах при этом корректный `gpt-5.5`/`gpt-5.4`): setup теперь обязан копировать `model` из template дословно, при сомнении в доступности слага — удалять поле (наследуется модель сессии); Phase 5 проверяет совпадение с template. `$qtim-team-up` при падении спавна из-за невалидной модели чинит TOML и продолжает эпик; `$qtim-update` проверяет слаги при миграции; CI (`check_codex_agents.py`) отклоняет слаги без минорной версии в шаблонах.

## 2.3.0 — 2026-07-02

### Добавлено

- **Skill `$qtim-product-onboard`** — глубокое наполнение продуктовой памяти из кодовой базы: fan-out read-only исследователей (разделы/экраны из роутера, акторы/права из auth, словарь домена из схемы, события аналитики и фичефлаги) + синтез материалов ПМа из опциональной `docs/product-context/` (интервью, тикеты, метрики — каждый вывод со ссылкой на источник). Выход: `memory/product-map.md`, `product-actors.md`, `product-glossary.md`, `product-metrics.md`; пишет только main thread, факты с прецедентами `file:line`, гипотезы помечаются.
- **Роль `product` использует и пополняет память**: продуктовая память в Read first; термины из глоссария, метрики PRD привязываются к реальным событиям из `product-metrics.md` (отсутствующее событие — задача на трекинг, не факт); обновления памяти — через предложения в финальном выходе, пишет team-lead.
- **Интеграция с конвейером**: `$qtim-feature` Stage 1 читает продуктовую память до вопросов пользователю и предлагает прогнать `$qtim-product-onboard`, если памяти нет; setup рекомендует его после генерации PM-дорожки.
- Запись `-> 2.3.0` в upgrade-notes (миграция только для команд с PM track; dev-only не затронуты).

## 2.2.0 — 2026-07-02

### Добавлено

- **Версионирование сгенерированного состояния**: `$qtim-setup` штампует версию плагина в charter (`<!-- qtim-version: X.Y.Z -->` первой строкой) и в каждый сгенерированный `.codex/agents/*.toml` (`# qtim-version: X.Y.Z`); версию плагин берёт из собственного манифеста.
- **Skill `$qtim-update`** — двухуровневое обновление: печатает версии плагина и команды с вердиктом, даёт проверенные команды обновления плагина (`codex plugin marketplace upgrade qtim-agent-team` + `codex plugin add qtim@qtim-agent-team`, затем новая thread) и мигрирует сгенерированные файлы проекта на текущую версию строго по upgrade notes — с diff-подтверждением для файлов, правленных пользователем; `memory/` и `docs/features/` не трогаются; даунгрейд запрещён.
- **`reference/upgrade-notes.md`** — журнал миграций сгенерированного состояния по версиям (2.0.0 -> 2.1.0 -> 2.2.0) + общие правила; ведение закреплено в release-чеклисте `AGENTS.md`.
- **Версия в SessionStart hook**: анонс показывает `[qtim vX.Y.Z]` из stamp charter (или `legacy` для команд, сгенерированных до 2.2.0) и упоминает `$qtim-update`.
- Раздел «Обновление и версии» в README: где смотреть версии (`codex plugin list`, stamp в charter) и как обновляться.

## 2.1.0 — 2026-07-02

### Добавлено

- **Ролевой вход**: `$qtim-setup` первым вопросом спрашивает роль пользователя (Developer / PM-Analyst / Оба) и генерирует команду под неё; charter стал track-aware — dev и PM треки живут между маркерами `qtim:track:*`, повторный setup обновляет только свой трек.
- **Skill `$qtim-feature`** — PM-конвейер: intake -> PRD -> декомпозиция -> оценка -> план -> handoff в `$qtim-team-up`/`$qtim-team-lazy`; checkpoints у пользователя на каждой стадии; resume по статусам артефактов при существующем slug.
- **Шаблон `agents/product.toml`** (`qtim-product`) — product/analyst роль: PRD, декомпозиция, сведение оценок, план; production code не пишет.
- **`reference/feature-pipeline.md`** — контракт конвейера: артефакты и статусная машина, правила grounded-оценки (S/M/L/XL + confidence + evidence, без выдуманных часов), handoff contract. Setup переносит суть в charter (self-contained).
- **Конвенция `docs/features/<slug>/`** — intake/prd/decomposition/estimate/plan версионируются в docs; в `memory/decisions.md` — только строки-указатели.
- **Dev-consult на декомпозиции и оценке**: точность описания задачи обеспечивают профильные dev-агенты (architect + database/frontend/testing по слоям, read-only) — размер work item даёт владелец слоя, PM-роль сводит; поэтому PM-only setup тоже генерирует dev-роли по стеку (без reviewer).

### Изменено

- SessionStart hook упоминает `$qtim-feature` (текст остался статическим: grep-условие по track-маркеру спрятало бы skill в charter'ах 2.0.0 без маркеров).
- `$qtim-team-up` / `$qtim-team-lazy` читают `docs/features/<slug>/plan.md` и `prd.md` как источник scope и acceptance criteria и обновляют Status артефактов по завершении.
- README и plugin.json переписаны под двух-ролевую концепцию; `defaultPrompt` включает feature pipeline.
- Публичные repository/homepage/install-ссылки указывают на `trushhh777/qtim-agent-team`.

## 2.0.0 — 2026-07-02

### Исправлено (pre-release ревью)

- **Невалидный YAML frontmatter `qtim-team-lazy`** — незакавыченное `description` с `:` внутри роняло ingestion-валидатор Codex; значение взято в кавычки.
- **`reviewer.toml` ссылался на `../../reference/independent-review.md`** — шаблон копируется setup'ом в `.codex/agents/` целевого проекта, где внутренние пути плагина не резолвятся (регрессия бага, чинившегося в 1.2.0); теперь ссылка на independent review gates в `.codex/team-charter.md`. В `qtim-setup` добавлено требование самодостаточности генерируемых файлов (Phase 4, Phase 5, Critical Rules).
- **CI не ловил оба класса багов**: добавлен `check_skills.py` (frontmatter всех SKILL.md, PyYAML с fallback-парсером), `check_codex_agents.py` теперь парсит TOML через `tomllib` (Python 3.11+) и запрещает `../`-пути в шаблонах агентов.

### Изменено

- Плагин полностью перенесён на Codex packaging: `.agents/plugins/marketplace.json` + `plugins/qtim/.codex-plugin/plugin.json`.
- Claude slash-команды `/qtim:*` заменены на Codex skills: `$qtim-setup`, `$qtim-team-up`, `$qtim-team-lazy`, `$qtim-team-down`.
- Claude Agent Teams runtime заменён на Codex subagent workflow: explicit spawn, session-local agent threads, custom agents в `.codex/agents/*.toml`.
- Шаблоны ролей перенесены из Claude agent Markdown/frontmatter в Codex custom agent TOML templates.
- `codex-consult.md` заменён на `independent-review.md`: в Codex больше нет внешнего "Codex second-opinion", review делает отдельный read-only agent thread.
- Generated project state теперь живёт в `.codex/team-charter.md`, `.codex/agents`, `.codex/hooks.json`, `memory/` и `AGENTS.md`; `.claude/*` больше не генерируется.
- README и repo instructions переписаны под Codex install/use flow.

### Удалено

- `.claude-plugin/*`, `plugins/qtim/.claude-plugin/*`, `plugins/qtim/commands/*` и Claude-only role templates.

### Добавлено

- Codex plugin manifest validation target.
- CI-проверка Codex custom agent TOML templates.
- Repo `AGENTS.md` с правилами поддержки Codex-native версии.

## 1.2.0 — 2026-07-02

### Исправлено

- **Workflow-примеры теряли данные между стадиями** (`reference/orchestration-patterns.md`): judge/synth/filter/classifier в паттернах 1, 3, 4, 5, 6 теперь получают результаты предыдущих стадий интерполяцией в промпт; добавлены жёсткое правило движка B и anti-pattern «судья вслепую».
- **Субагенты не находили протокол codex-consult**: setup теперь записывает в charter абсолютный путь к `reference/codex-consult.md` (плейсхолдер плагин-рута вне файлов плагина не резолвится); промпт спавна в team-up и шаблоны ролей ссылаются на путь из charter; в Standalone — на локальную копию.
- **Невалидный `permissions.deny` baseline** в setup: голые glob'ы (`.env*`, `~/.ssh/**`) заменены на формат `Tool(паттерн)` — `Read(./.env*)`, `Edit(./.env*)`, `Read(~/.ssh/**)`, `Edit(~/.ssh/**)`.
- **SubagentStop-hook плагина** срабатывал во всех проектах — теперь, как и SessionStart, только при наличии `.claude/team-charter.md`; в description честно помечен как advisory для человека (stdout SubagentStop в контекст модели не инжектится).
- **`tools` шаблонов ролей**: убраны несуществующие/упразднённые `Computer`, `MultiEdit` и двусмысленный `Task`; добавлены `TaskCreate`/`TaskUpdate`/`SendMessage`, которых требуют промпты ролей (баг-флоу tester'а, маршрутизация reviewer'а, нотификации db→front), а по итогам независимого ревью — ещё `Skill` во все роли (промпты предписывают mandatory-invoke skills) и `Write` reviewer'у (пишет review-report в `memory/`).
- **Дубль hooks**: Q7 SessionStart/SubagentStop генерируются только при Q6=Standalone — в Plugin-linked их уже даёт `hooks.json` плагина.
- **Universal skills больше не захардкожены** в team-up: фактический список — из charter («Правила работы»), недоступные в окружении skills в промпты спавна не включаются (mandatory-invoke несуществующего skill ломал старт ролей); при пустом списке строка опускается целиком. `brainstorming`/`grill-me` в шаблоне architect помечены «если доступен».
- Из PostToolUse-примера setup убран упразднённый `MultiEdit`; указатель канона в charter — `/qtim:team-up` вместо пути файла; в Standalone команды указываются локальными именами, а путь к codex-протоколу — абсолютным и на локальную копию; в перечень сохраняемого frontmatter (setup 4.2) добавлен `color`.
- Удалён несуществующий `$schema` из `marketplace.json`.

### Добавлено

- **CI-валидация** (`.github/workflows/validate.yml` + `.github/scripts/`): JSON-манифесты, запрет call-синтаксиса упразднённых примитивов, плейсхолдеры по белому списку (включая детектор деформированных — пробелы/нижний регистр), целостность относительных ссылок; push-триггер только для `main`, чтобы PR не гонял job дважды.
- `CHANGELOG.md`.
- Секция **Intake-режим** (ответ Q3) в структуре charter — раньше ответ было некуда записывать, а `intake-protocol.md` читает дефолты именно из charter.
- **Каркасы cross-cutting ролей** `devops`/`product`/`auditor` в setup 4.2 — Extended-состав больше не генерируется «с нуля».
- **Стек-условные пометки** в шаблонах ролей + явный список условных блоков и безусловного ядра в setup 4.2 (шаблоны несут терминологию RLS/presign/realtime, нерелевантную части стеков).
- Setup создаёт `.claude/agent-memory/<role>-agent/MEMORY.md` для ролей с включённой памятью (первый спавн больше не шумит ошибкой чтения).
- Рекомендация по выбору `model` per-роль в setup 4.2.
- Чеклист «при обновлении Claude Code» в `CLAUDE.md`.

## 1.1.x и ранее

См. `git log` (conventional commits): автоподбор skills и плагинов/MCP под стек (1.1.x), исходный движок team-up/team-lazy/team-down + генератор setup + hooks (1.0.0).
