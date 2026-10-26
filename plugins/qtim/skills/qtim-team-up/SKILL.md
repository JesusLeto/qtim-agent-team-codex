---
name: qtim-team-up
description: Use when the user explicitly asks to run a full qtim team in Codex for a substantial task or epic. Reads .codex/team-charter.md, spawns the selected role agents in parallel when subagent tools are available, coordinates implementation/test/review loops, and reports results.
---

# qtim Team Up

Invocation of this skill is explicit permission to run a Codex subagent workflow for the roles defined in `.codex/team-charter.md`.

Use Codex subagent threads and custom agents. Do not assume a hidden persistent team object.

## Preconditions

1. Read `.codex/team-charter.md`.
2. If it does not exist, stop and ask the user to run `$qtim-setup`.
   Для реализации feature проверь dev-track и нужных исполнителей;
   один PM reviewer не означает dev-ready.
3. Read only the needed shared references:
   - `../../reference/intake-protocol.md`;
   - `../../reference/orchestration-patterns.md`;
   - `../../reference/independent-review.md`;
   - `../../reference/model-profiles.md`.
   Проверь профиль main task, если runtime exposes metadata: qtim team-lead должен работать на `gpt-6-astra` + `ultra`. Если профиль другой, остановись до fan-out и попроси пользователя открыть новую задачу с Astra/Ultra; qtim не переключает текущий task скрыто.
4. Проверь `memory/epic-state.md` (его пишет `$qtim-team-down` при незавершённом эпике): если файл есть и эпик не закрыт — после подъёма команды покажи резюме и предложи продолжить с зафиксированного места, восстановив задачи из «В полёте» в видимом плане с их ролями.
5. Для `docs/features/<slug>/` сначала прочитай `spec.md` и
   `../../reference/feature-pipeline.md`: проверь текущие Reviewed revision,
   Approved revision и готовность handoff; незакрытый spec gate возвращает к
   `$qtim-feature` до реализации. Main thread — единственный редактор
   spec; до работы он ставит `In Development`, после обязательных gates — `Done`.
   Существенная дельта требует revision contract, остальные результаты идут в
   `.work/validation.md`. При отсутствии spec читай legacy `plan.md` + `prd.md`
   или `feature-brief.md` как контракт без автоматических правок/конвертации.
   Прогресс legacy-фичи сохраняй в `.work/validation.md`.

Approved spec/legacy-контракт вместе с явными ограничениями пользователя — граница реализации.
При явном запуске выполняй утверждённые work items подряд; новый checkpoint нужен только для новой
продуктовой развилки, необратимого действия вне approval, изменения scope или
исчерпанного бюджета доработок. Старт следующего work item уже разрешён запуском.

## Decision Matrix

Use full team-up only for mode D:

- there is an epic or substantial change;
- implementation crosses roles;
- there will likely be loops: implement -> test -> fix -> retest -> review.

If the task is a single pass without feedback loops, switch to `$qtim-team-lazy`. If it is trivial, handle it directly.

## Liveness Model

Codex subagents are task-scoped agent threads, not durable named team members.

- Track the current roster in your own context: `role -> agent id`.
- Before spawning after resume or context loss, inspect descendants when the runtime exposes Active/Done agent threads; reuse the matching reachable thread and spawn only missing roles.
- If you still have a live agent id, send follow-up input to that thread.
- Never assume a remembered handle is live or a missing handle is gone: verify through the current runtime, then recover or respawn.
- Close completed threads when no longer needed so the next batch has capacity.

## Spawning

Spawn only currently needed roles in parallel when the subagent tool is available; batch the roster when independent work exceeds the available thread slots.

Use custom agent types from `.codex/agents/*.toml` when Codex exposes them. If the current task has not loaded custom agents yet, either ask the user to start a new Codex task or use `worker` / `explorer` fallback with the role instructions embedded in the prompt.

При ошибке model pair используй политику fallback и task-local сведения о
недоступности из `model-profiles.md`; сохрани override и отправь системную
починку в `$qtim-update`. Уже разрешённый совместимый fallback используй повторно.

## Model And Reasoning Policy

- Не переключай модель, reasoning или Fast уже открытого task. qtim team-lead prerequisite — `gpt-6-astra` + `ultra`; этот профиль выбирает пользователь при старте task.
- Используй exact role pair из загруженных TOML. Built-in `explorer` запускай на `gpt-6-luna` + `medium`. Не повышай role agents до `max`/`ultra`; `max` разрешён только отдельному clean-context ADR adversary по правилу риска.
- `Ultra` у main task разрешает Codex proactively делегировать внутри scope этого вызова, но не означает «спавнить все роли». Execution depth A/B/C/D, roster и write scopes по-прежнему определяет main thread.
- Child agents не спавнят qtim-команду рекурсивно. Дополнительные роли спавнит main thread; fan-out ограничивай доступными slots и разбивай на batches, если независимых работ больше.

Default Standard roster:

- `architect` -> `qtim-architect`;
- `db` -> `qtim-database`;
- `front` -> `qtim-frontend`;
- `tester` -> `qtim-testing`;
- `reviewer` -> `qtim-reviewer`;
- `explorer` -> built-in `explorer`.

Compact and Extended rosters come from the charter, not this file.

## Prompt Template Per Role

Write every peer-agent prompt and follow-up in English. Use a compact prompt. Do not paste the whole charter into every subagent. The role's user-facing artifacts and anything relayed to the user remain in Russian under the project language contract.

```text
You are the <role> role in the qtim team for <project>.

Read first:
1. AGENTS.md
2. .codex/team-charter.md: sections for <role>, domain invariants, working rules
3. Role-specific read-on-start files from the charter
4. Your role section in memory/lessons.md, if that file exists

Mission: <role mission from charter>.
Do not touch: <do-not-touch from charter>.
Skills/practices: <skills and mandatory practices from charter>.
Feature contract: <spec path, WI and accepted decisions; legacy path when applicable>.
Verification: <assigned gates/owner, existing receipts and evidence/reuse reference path>.
Review budget: <stable WI/batch id and completed passes/remaining rounds>.

Reason internally and communicate with peer agents in English. Write user-facing artifacts and anything intended for the user in Russian.
Return concise artifacts, changed files if any, verification performed, blockers, and memory updates needed.
```

For implementation agents, remind them that other agents may edit in parallel and they must not revert unrelated changes.

## Coordination Flow

1. Для Approved spec используй принятые решения и ограниченный CONSULT
   architect при необходимости. DESIGN нужен для конкретной новой развилки с
   evidence; для задачи без утверждённого контракта следуй `intake-protocol.md`.
2. Если architect создал ADR, **до** user approval main thread запускает отдельного read-only adversary без истории (`fork_turns = "none"` или runtime-эквивалент) на `gpt-6-astra` + `xhigh`; необратимое решение, затрагивающее документированный инвариант, -> `max`. Передай только ADR, инварианты и проверяемые paths. Верни findings architect для верификации и не продолжай к approval, пока в ADR нет `adr-stress-test:` со счётчиком или честным `skipped — <reason>`. Optional independent code review не выключает этот шаг.
3. Ask for user approval before irreversible or ambiguous work not covered by the Approved plan, following `intake-protocol.md`.
4. Parallelize only disjoint work scopes; `Ultra` не отменяет этот gate и не является причиной увеличить fan-out.
5. Route implementation by ownership.
6. Назначь владельцев gates и проверь receipts/активные процессы по
   `orchestration-patterns.md`. Общие проверки выполняй после завершения
   соответствующих writers. Tester закрывает реальное browser acceptance для UI
   актуальным evidence; self-check frontend остаётся отдельным покрытием.
7. Для предусмотренного code-review gate reviewer делает первый проход на
   стабильную границу WI/пакета и проверяет
   актуальность receipts; отсутствующие или устаревшие gates выполняет их
   назначенный владелец. Подтверждённые блокеры проходят не больше двух
   fix-and-recheck раундов по `independent-review.md`; resume, смена агента и
   lazy → team-up сохраняют уже выполненные passes и бюджет. Остался блокер —
   `Blocked` с evidence и решением владельца. Находки вне Approved scope передай
   как отдельные задачи; конфликт с acceptance/security gate — `Blocked`.
   При активном code review в charter применяй canonical high-risk matrix из
   `independent-review.md`: текущий независимый reviewer закрывает тот же scope,
   отдельная трасса нужна только по фактическому риску/контракту. Low-risk diff
   допускает `skipped (low-risk diff)`. Выключенный code review не выключает
   обязательные SPEC_REVIEW и ADR stress-test.
8. Main agent integrates and checks all results. Subagent output is input, not authority.
9. Commit durable decisions to `memory/`.

## Reporting

Каждый промежуточный отчёт начни строкой `сделано: ... / в работе: ... /
дальше: ... / коммитов: N`. Покажи фактическое состояние фаз, чтобы статус
реализации был виден даже во время review.

Final report should be result-first:

- files changed and user-visible outcome;
- gates run and status;
- findings fixed or left open;
- memory files updated;
- для feature — выполненные WI и Status `spec.md`, существенные дельты и
  `.work/validation.md`; для legacy — прогресс в `.work/` без правок контракта;
- если в preconditions найден незавершённый epic-state — его резюме и предложение продолжить;
- active agent threads closed or still running.

Do not report a raw transcript of agent chatter.
