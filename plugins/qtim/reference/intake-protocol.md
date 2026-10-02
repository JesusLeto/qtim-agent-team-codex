# Intake-протокол qtim для Codex

> Generic reference qtim. Проектные инварианты и роли живут в `.codex/team-charter.md`; здесь — переносимая механика принятия задач.

## Принцип

Участие пользователя асимметрично:

- анализ и проектирование — пользователь в контуре;
- реализация, тесты и ревью — автопилот после approval;
- необратимые или неоднозначные развилки возвращаются пользователю даже во время реализации.

Явные ограничения пользователя и Approved scope старше рекомендаций reviewer'а,
памяти и process defaults. Находку вне scope предложи отдельной задачей; если без
неё нельзя выполнить согласованную приёмку или обязательный security gate,
поставь `Blocked` и верни владельцу конкретную развилку. Проверка не даёт
автоматического права расширить задачу.

Codex main thread остаётся team-lead. qtim subagent workflow авторизуется явной просьбой пользователя или вызовом qtim skill. Agent threads живут в scope текущего task и могут быть восстановлены только когда runtime их показывает; скрытой постоянной команды нет. qtim workflow рассчитан на main thread `gpt-5.6-sol` + `Ultra`: этот профиль даёт proactive delegation внутри уже разрешённого scope, но не расширяет задачу и не выбирает execution depth вместо main thread.

## Pipeline

1. Classify task: feature, bug, refactor, audit, design, support.
2. Pick execution depth:
   - A Direct: main thread handles it.
   - B Single subagent: one bounded agent for isolated work.
   - C Lazy team: several roles, one-pass pipeline.
   - D Full team-up: iterative implement/test/review loops.
3. Отдельно проверь execution topology: два самостоятельных outcomes,
   producer -> consumer или разные isolated contexts/worktrees означают
   `$qtim-mission`, а не «режим E». Внутри Approved mission node остаётся direct
   либо получает один bounded mission-child `$qtim-team-lazy`; node-local team-up
   и третий уровень запрещены. Recommendation ничего не запускает.
4. Decide whether design approval is required.
5. For non-trivial work, run `$qtim-brainstorm` and produce a design brief. Create a separate ADR only when the ADR filter is satisfied; otherwise record the decision as one registry line.
6. Если создан ADR, до user approval проведи обязательный clean-context stress-test: main thread поднимает read-only `gpt-5.6-sol` + `xhigh` adversary без истории; для необратимого решения, затрагивающего документированный инвариант, — `max`. Architect верифицирует findings и фиксирует `adr-stress-test:` в ADR. Эта проверка не зависит от optional risk-based code review.
7. Проверь доменную предпосылку, от которой зависит весь план: подтверди её
   кодом, данными или владельцем до approval. Техническая проверка не заменяет
   ответ владельца на невыводимое из репозитория бизнес-правило.
8. Get approval for irreversible, ambiguous, product-visible, public API, security, money, or data migration decisions. Approved plan авторизует все его фазы; новый стартовый запрос перед каждой фазой не нужен, кроме явно выбранного пользователем phase-by-phase режима.
9. Execute with selected roles.
10. Verify with affected tests/browser and the bounded review contract in `independent-review.md`.
11. Record durable decisions and findings in `memory/` по `$qtim-kb-format`; approved decisions and features get a short pointer in the `memory/decisions.md` registry. Если evidence устарело, предложи `$qtim-kb-refresh`, не дописывай поверх сомнительного факта.
12. Report outcome, not agent chatter.

## Fork Test

Bring a decision to the user when any condition is true:

- hard or expensive to roll back;
- data deletion or transformation;
- public API contract change;
- money/billing/account state;
- authorization, tenant/scope visibility, or security boundary;
- product behavior can reasonably mean two different things;
- ключевая доменная предпосылка Approved scope не подтверждается доступными источниками и известна только владельцу;
- conflict with `memory/` or `AGENTS.md`;
- new actor, role, channel, or externally visible surface.

Do not ask for:

- role selection;
- file naming when project conventions cover it;
- equivalent implementation details;
- reversible internal refactors;
- order of tool calls;
- report formatting.

## Fact Vs Decision

A fact available from the environment is the team's job: read code, `memory/`, git history and available documentation before asking. Bring the user only decisions that evidence cannot resolve: product intent, choice between viable trade-offs, irreversible scope and acceptable risk.

Do not disguise missing research as a clarifying question. When evidence conflicts or is incomplete, show what was found and ask for the decision explicitly.

## Design Brief

For non-trivial work, use `$qtim-brainstorm` to separate interpretations, evidence, viable options, open questions and labeled assumptions before selecting a design. Use `$qtim-grill` to stress-test a consequential plan; use `$qtim-prototype` when a UX or behavioral fork is cheaper to resolve with a concrete disposable example than with prose.

Найди одну-две предпосылки, ошибочность которых заставит переделать весь план
(например, кто владеет сущностью и какой доступ разрешён). Сверь их с кодом и
документами; если это невыводимое доменное правило, спроси владельца до approval.

Produce:

- goal in user language;
- affected layers;
- relevant invariants;
- risks and reversibility;
- 2-3 approach options if meaningful;
- recommended option;
- open questions that block safe execution;
- проверенные и ещё непроверенные доменные предпосылки, влияющие на scope;
- proposed roles and verification gates.

Use plan/approval features when available. Otherwise ask for direct confirmation in chat.

## ADR Stress-Test

`$qtim-grill` — self-play/decision-owner pass. Он полезен, но не независим: модель и контекст уже заякорены на выбранном решении.

Для каждого настоящего ADR main thread перед approval запускает второй pass по `independent-review.md`: отдельный read-only thread, `fork_turns = "none"` или эквивалент, model `gpt-5.6-sol`, effort `xhigh` (`max`, если решение одновременно необратимо и затрагивает документированный инвариант). Передавай только ADR, инварианты и проверяемые пути, не историю рассуждений. Итоговая строка:

`adr-stress-test: sol-adversary (xhigh|max) — N findings, M учтено`

Если runtime не дал запустить оппонента, запиши `skipped — <reason>` и явно сообщи пользователю: попытка обязательна, пропуск не считается пройденным гейтом.

## Implementation Silence

After approval, keep moving until completion unless a new fork appears. Do not drip-feed low-value questions.
Первый проход reviewer на фазу обязателен по выбранному workflow; после него —
не больше двух раундов fix-and-recheck. Повторяй полное review только при
изменении поверхности риска, как определено в `independent-review.md`.
Непреодолённый blocker после бюджета — `Blocked` с фактами попыток и решением,
которое требуется от владельца.

## Anti-Patterns

- Coding a non-trivial feature before design approval.
- Spawning full team for a one-file obvious fix.
- Letting subagents decide product requirements.
- Treating independent reviewer output as authoritative without verification.
- Leaving durable decisions only in conversation instead of `memory/`.
