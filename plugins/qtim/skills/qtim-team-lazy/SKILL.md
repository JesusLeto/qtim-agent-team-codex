---
name: qtim-team-lazy
description: "Use when the user explicitly asks for qtim lazy mode in Codex: spawn only the role agents needed for the current task, without warming the full team."
---

# qtim Team Lazy

Invocation of this skill is explicit permission to spawn only the Codex subagents needed for the current task.

## Mission-child mode

Peer node lead может вызвать skill только когда Approved `$qtim-mission` prompt
явно содержит `execution: lazy`, exact lead profile, `rolePolicy:
minimum-sufficient`, allowed roles, concrete responsibilities и local write
scopes. Это разрешение действует только внутри одной node:

- node lead не создаёт peer tasks, новую mission или `$qtim-team-up`;
- local subagents не вызывают qtim orchestration skills и не делегируют дальше;
- выбираются все и только роли, реально нужные acceptance criteria; числовой
  plugin cap не вводится, overflow выполняется local waves по runtime capacity;
- все local claims, changed files и gates проверяет node lead;
- наружу возвращается один агрегированный `WORKER RECEIPT` с ролями,
  Approved allowlist, responsibilities, write scopes, outputs, pairwise scope
  check, product-fork flag и результатом проверки;
- implement -> test -> fix loop, новая роль вне Approved allowlist, пересечение
  scopes или продуктовая развилка возвращаются mission coordinator как
  `ESCALATION_REQUEST`.

Mission-child authorization не даёт local agents права управлять DAG, runtime
registry, integration branch, final verifier или другими peer nodes.

## When

Use lazy mode for mode C:

- the task crosses more than one concern but can complete in one pass;
- there is no expected implement -> test -> fix -> review loop;
- you want isolation or parallel read-heavy exploration without warming every role.

Use direct work for trivial tasks. В standalone lazy mode escalте to
`$qtim-team-up` if feedback loops appear. В mission-child mode team-up запрещён:
верни `ESCALATION_REQUEST` mission coordinator.

## Steps

1. Read `.codex/team-charter.md`. If missing, ask for `$qtim-setup`.
   Прочитай `../../reference/orchestration-patterns.md` для evidence/reuse и
   `../../reference/model-profiles.md` для pair/fallback. Для реализации feature
   проверь dev-track/нужных исполнителей; один PM reviewer не означает dev-ready.
   Read-only и mission-child roster задаёт их bounded authorization.
   Если runtime exposes profile main task и это не `gpt-6-astra` + `ultra`, остановись до fan-out и попроси открыть новый task на Astra/Ultra: текущий task плагин скрыто не переключает.
2. Для `docs/features/<slug>/` сначала читай `spec.md` и
   `../../reference/feature-pipeline.md`: проверь текущие Reviewed revision,
   Approved revision и готовность handoff; незакрытый spec gate возвращает к
   `$qtim-feature` до реализации (mission-child возвращает `ESCALATION_REQUEST`
   coordinator). Approved решения — условия работы;
   конкретное новое evidence открывает только затронутую развилку. Main thread
   единолично обновляет Status `In Development`/`Done`; существенная дельта
   следует revision contract, receipts идут в `.work/validation.md`.
   Без spec читай legacy `plan.md` + `prd.md` или `feature-brief.md` как контракт
   без автоматических правок/конвертации; прогресс сохраняй в `.work/validation.md`.
   Approval вместе с явным запуском разрешает предусмотренную реализацию.
   Новый checkpoint нужен для продуктовой развилки, необратимого действия вне
   approval, изменения scope или исчерпанного бюджета. В mission-child mode
   статусы feature и portable mission state пишет coordinator: node lead
   возвращает предлагаемый transition и существенную дельту в receipt.
3. Classify the task and choose only the needed role(s).
4. Spawn the needed custom agents when available; otherwise use `worker` fallback with inline role instructions. Built-in `explorer` запускай явно на `gpt-6-luna` + `medium`.
5. Give each subagent a concrete scope and expected output in an English prompt;
   передай spec/legacy path, WI/принятые решения, assigned gates, receipts,
   evidence/reuse reference и оставшийся review budget. All follow-ups between
   agents stay in English, while user-facing artifacts and relayed results stay in Russian.
6. Wait only when the next step is blocked on the result.
7. Integrate results locally, verify, and update `memory/` when durable knowledge was produced.
   Назначь одного владельца gate и проверь receipts/активные процессы по
   `orchestration-patterns.md`; общие проверки — после соответствующих writers.
   В mission-child mode не пиши portable mission state и integration branch:
   верни один receipt coordinator.

Если review возвращает `NOT APPROVED`, сначала проверь замечания по Approved
scope и коду. Внеплановые находки передай владельцу как отдельные задачи;
конфликт с acceptance/security gate верни как `Blocked`. Для подтверждённого
блокера, требующего цикла исправления, standalone mode переходит к
`$qtim-team-up`; передай принятые решения, актуальные review/gate receipts,
стабильные WI/пакеты и оставшийся бюджет. Уже проведённый reviewer pass
засчитывается; смена агента, compaction и эскалация бюджет не обнуляют.
Дальнейшие раунды ограничены `../../reference/independent-review.md`. В mission-child mode
верни `ESCALATION_REQUEST` с оставшимся бюджетом и не запускай team-up локально.

Модель, reasoning и Fast уже открытого main task не переключай; team-lead
prerequisite — Astra+Ultra. Используй exact pair из role TOML и fallback policy
`model-profiles.md`, включая известную недоступность в текущем runtime. `Ultra`
не повышает режим C до team-up; child agents не делегируют рекурсивно.

Если в lazy-flow появился настоящий ADR, до user approval проведи обязательный clean-context stress-test из `../../reference/independent-review.md`: новый read-only Astra+xhigh thread без истории, либо Astra+max при «необратимо + документированный инвариант»; строка `adr-stress-test:` обязательна независимо от optional code-review gate. После изменений действуют bounded раунды того же reference.

## Escalation

В standalone lazy mode escalate from lazy to full team-up when:

- tester finds bugs that require implementation rework;
- reviewer подтвердил in-scope blocker, требующий цикла исправления;
- more roles become necessary than originally expected;
- an irreversible or ambiguous product decision appears.

В mission-child mode все эти условия возвращаются coordinator как
`ESCALATION_REQUEST`; node lead не запускает `$qtim-team-up` и не расширяет
Approved allowlist. Do not restart already useful agent threads. Continue them
when possible; spawn missing roles only.

Каждый промежуточный user status начни строкой `сделано: ... / в работе: ... /
дальше: ... / коммитов: N`.

## Anti-Patterns

- Spawning every role in lazy mode.
- Asking an agent to do broad undefined work.
- Delegating the immediate critical-path task when you are blocked on it.
- Treating subagent conclusions as final without checking changed files and project invariants.
- Использовать mission-child mode без exact Approved authorization в node prompt.
- Создавать peer tasks, третий уровень descendants или скрытый node-local team-up.
