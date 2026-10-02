<!-- qtim-version: 2.15.0 -->
# qtim team charter — fullstack golden

## Roles and model matrix

| Role | Agent | Mandatory practices |
|---|---|---|
| architect | `qtim-architect` | `$qtim-brainstorm` before ADR; compare design options with `$qtim-minimal-diff`; clean-context Sol ADR stress-test |
| database | `qtim-database` | `$qtim-minimal-diff` before non-trivial implementation; `$qtim-debug-loop` for non-trivial bugs |
| frontend | `qtim-frontend` | `$qtim-minimal-diff` before non-trivial implementation; `$qtim-debug-loop` for non-trivial bugs |
| testing | `qtim-testing` | `$qtim-debug-loop` for flaky reproduction |
| reviewer | `qtim-reviewer` | `$qtim-minimal-diff` excess is recommendation-only; protected-zone/invariant/gate violations block |
| product | `qtim-product` | evidence-grounded vertical slicing |

Team-lead `gpt-5.6-sol` + `ultra`; architect/reviewer Sol+xhigh;
database/frontend/product Sol+high; testing Terra+medium; explorer Luna+medium.

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

## Working rules

Main thread owns fan-out. Role outputs are advisory until verified. Reviewer is mechanically
read-only. Tester owns `npm run dev`. ADRs receive a clean-context Sol adversary.
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

Производная self-contained сводка канона `reference/feature-pipeline.md`: fast
`feature-brief.md` или full PRD/decomposition/plan, vertical slices with DRI.
После PRD возможен терминальный `PRD-only` без плана запуска; `estimate.md`
нужен по запросу или когда выбираются исполнитель, срок или бюджет. XL item
разрезается. После проверенного `Done` и свидетельства слияния `Archived`
допустим по решению владельца без удаления долговечных PRD/plan/brief;
временные материалы живут в `.work/` и очищаются отдельно по его решению.
Каждый Approved plan/brief заканчивается блоком «Что запускать дальше»: recommendation,
why, topology, command, alternative. Direct/team-lazy/team-up/mission выбираются по
execution topology, а не размеру; recommendation ничего не запускает без нового
явного разрешения. Approved graph с готовыми base/integration target, scopes,
budgets и gates получает `запусти`; unresolved writer/lazy/runtime choice —
`preview`, а один связный feedback loop — team-up fallback.
Stage 6 сначала пишет handoff artifacts, затем строку в `memory/decisions.md` записывает
последним completion marker. Approved artifact без marker означает interrupted handoff и resume Stage 6.
<!-- qtim:track:pm:end -->

## Memory layout

См. `memory/MEMORY.md`.
