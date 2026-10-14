<!-- qtim-version: 2.16.0-experimental.1 -->
# qtim team charter — fullstack golden

## Roles and model matrix

| Role | Agent | Mandatory practices |
|---|---|---|
| architect | `qtim-architect` | `$qtim-brainstorm` before ADR; compare design options with `$qtim-minimal-diff`; clean-context Astra ADR stress-test |
| database | `qtim-database` | `$qtim-minimal-diff` before non-trivial implementation; `$qtim-debug-loop` for non-trivial bugs |
| frontend | `qtim-frontend` | `$qtim-minimal-diff` before non-trivial implementation; `$qtim-debug-loop` for non-trivial bugs |
| testing | `qtim-testing` | `$qtim-debug-loop` for flaky reproduction |
| reviewer | `qtim-reviewer` | mandatory clean-context SPEC_REVIEW; `$qtim-minimal-diff` excess is recommendation-only; protected-zone/invariant/gate violations block |
| product | `qtim-product` | evidence-grounded vertical slicing |

Team-lead `gpt-6-astra` + `ultra`; architect/reviewer `gpt-6-astra` + `xhigh`;
database/frontend/product `gpt-6-sol` + `high`; testing/explorer `gpt-6-luna` + `medium`.

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

## Working rules

Main thread owns fan-out. Role outputs are advisory until verified. Reviewer is mechanically
read-only. Tester owns `npm run dev`. ADRs receive a clean-context Astra adversary.
Only an explicit executable `$qtim-mission` or an unambiguous request to conduct
multiple Codex peer tasks as one mission may authorize visible tasks; a single
ordinary task/dialog or planning-only request may not. Mission workers do not
create descendants. Read-only and isolated
writer nodes use validated receipts. Writers integrate topologically in disposable
transaction worktrees; affected gates pass before locked exact-old ff-only
promotion to the clean integration worktree. Portable state uses scoped checkpoint
commits in a separate state worktree; a clean-context verifier owns
APPROVED/NOT APPROVED.
`status/resume/stop` fail-visible; SessionStart is advisory and never auto-resumes
or auto-archives mission tasks.
Явные ограничения пользователя и Approved scope старше рекомендаций review;
out-of-scope finding идёт в отдельную задачу, обязательный blocker возвращается
владельцу. Approved plan авторизует следующие фазы без повторного стартового
запроса, кроме явно выбранного phase-by-phase режима или новой развилки.
Перед записью `memory/` или `docs/features/` вызови `$qtim-kb-format`; при
обнаруженном дрейфе предложи `$qtim-kb-refresh`.
Проверки имеют одного владельца и receipts в `.work/validation.md`: scope/AC,
команда, входы/WIP/dependencies/config/окружение, результат, лог и ограничения.
Перед повтором назови изменённые входы; сохрани process handles и cleanup.
CI не заменяет browser/native evidence; одинаковый risk gate не требует второго reviewer.

<!-- qtim:track:dev:start -->
## Dev track

Implement → test → independent review. Первый reviewer pass на фазу полный;
затем максимум два fix-and-recheck раунда с затронутыми gates. Полный повтор
нужен при изменении risk surface или расширении поведения за проверенный diff;
обязательный security/ADR review сохраняется. Blocking browser evidence is
configured in `.codex/screenshots-gate.json`.
<!-- qtim:track:dev:end -->

<!-- qtim:track:pm:start -->
## PM track

Производная self-contained сводка канона `reference/feature-pipeline.md`:
интервью → одна `docs/features/<slug>/spec.md` с SPEC_REVIEW → approval → handoff.
Main thread — единственный редактор; consult получает конкретный незакрытый вопрос.
Одна WI-таблица содержит AC, DRI, contributing роли/слои, файлы, зависимости и
стабильные review boundaries. Оценка optional по запросу; XL item разрезается.
Revision / Reviewed revision / Approved revision фиксируют точный контракт.
Принятые D-* меняет новый подтверждённый факт, не reviewer preference;
семантическая правка возвращает Draft/pending, status и receipts ревизию не меняют.
SPEC_REVIEW обязателен и при disabled code review: отдельный clean-context read-only
reviewer, один полный проход и максимум один targeted fix-recheck с бюджетом через resume.
Build/tests/browser до реализации не запускаются. READY_FOR_APPROVAL и текущие
review/approval revisions нужны для handoff; открытый blocker или недоступная роль
блокирует готовность. Явный owner waiver хранит revision/scope/reason/risk/evidence,
не обозначается PASS и требует ручной проверки перед исполнением.
Done требует acceptance/gates; Archived — merge evidence и решение владельца.
Legacy PRD/plan/feature-brief.md читаются без автоматической конвертации/удаления;
mixed sources требуют явного Canonical: spec.md. Временные материалы живут в `.work/`.
Каждая spec заканчивается блоком «Что запускать дальше»: recommendation,
why, topology, command, alternative. Direct/team-lazy/team-up/mission выбираются по
execution topology, а не размеру; recommendation ничего не запускает. Одновременное
approval и явное исполнение показанной команды не требуют второго запроса.
Dev track и нужные writers проверяются отдельно от наличия PM reviewer.
Approved graph с готовыми base/integration target, scopes,
budgets и gates получает `запусти`; unresolved writer/lazy/runtime choice —
`preview`, а один связный feedback loop — team-up fallback.
Handoff сначала готовится в spec; одну строку в `memory/decisions.md` обнови
последним completion marker. Approved spec без pointer — interrupted handoff:
resume передачи сохраняет решения, review и approval.
<!-- qtim:track:pm:end -->

## Memory layout

См. `memory/MEMORY.md`.
