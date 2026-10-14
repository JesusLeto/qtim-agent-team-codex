# Independent Review Protocol For Codex

> In Codex, qtim does not call "Codex as an external second opinion." Codex is the host. Independence is created by a separate read-only agent thread with a narrow prompt and clean context. For ADR stress-test qtim also fixes a quality floor: GPT-6 Astra.

## Principles

1. Advisory, not authoritative.
2. Main thread verifies every finding against opened code.
3. Domain invariants in `.codex/team-charter.md`, `AGENTS.md`, and `memory/` win over reviewer opinion.
4. Review threads are mechanically read-only when the runtime supports a sandbox override.
   The generated `qtim-reviewer` enforces `sandbox_mode = "read-only"`; a request for fixes
   goes to a separate write-enabled worker, never by relaxing the reviewer in place.
5. Advisory code review fails soft unless project policy requires fail-closed.
   Mandatory `SPEC_REVIEW` follows its fail-closed contract below. A skipped review
   is never reported as passed.
6. Use only at gate points and proportionally to the actual diff risk, not on every tiny edit.

## SPEC_REVIEW — Before Feature Approval

Каждая новая feature specification получает независимое review до approval и
handoff, даже если optional code review выключен. Main thread запускает
существующего `qtim-reviewer` в режиме `SPEC_REVIEW`: `sandbox_mode = "read-only"`,
`fork_turns = "none"` или эквивалент clean context; default pair —
`gpt-6-astra` + `xhigh`, с сохранением явно разрешённых user overrides.
Prompt-only read-only не выдаётся за механическую независимость.

Source pack содержит текущую ревизию `spec.md`, raw требования и ответы владельца,
принятые `D-*`, затронутые инварианты и точные источники для проверки. Авторская
история, chain-of-thought и резюме рассуждений не передаются. При recheck добавь
исходные findings/dispositions, конкретную дельту и затронутые `AC-*`/`D-*`/`WI-*`.

Reviewer проверяет соответствие требованиям и принятым решениям, проверяемость
AC, ownership/реализуемость/зависимости work items, gates, rollback, внешние
блокеры и условия Done. Чтение кода для grounding допустимо; build/tests/browser
и обязательные execution gates на этой стадии не запускаются. Статический
контракт review не означает, что будущая реализация проверена.

Выход: `Reviewed revision`, `READY_FOR_APPROVAL` или `CHANGES_REQUESTED`, findings
с источниками и affected IDs. Main thread проверяет findings, отклоняет
неподтверждённое с причиной и сохраняет короткий результат в spec по
[feature-pipeline.md](feature-pipeline.md). Предпочтения reviewer не открывают
принятые решения и не расширяют scope. Если меняется настоящий ADR, его
обязательный adversary остаётся отдельным gate.

Бюджет — **один полный проход и максимум один раунд исправления/целевого recheck**.
Он записывается в spec и сохраняется через restart, compaction, смену reviewer
и номера ревизии. Recheck подтверждает исправленные findings и затронутый
контракт. Если существенная дельта требует нового полного прохода сверх бюджета
или подтверждённый blocker остаётся, spec сохраняется Draft, workflow — `Blocked`;
владельцу предъявляются факты и решение о scope/дополнительном бюджете.

Недоступность роли: учти известную runtime capability, используй явно
поддерживаемый независимый fallback с теми же границами или сообщи отсутствие
review. Без состоявшегося gate нет ready handoff. Исключение — только явный
owner waiver на точную ревизию после сообщения причины и риска, с ручной проверкой
перед исполнением: `Review verdict: WAIVED`, `Reviewed revision: none`, scope и
owner evidence в spec. Это не `READY_FOR_APPROVAL`, не PASS и не автоматический
fallback. Self-review автора независимый проход не заменяет.

## Bounded Code Review And Remediation

Keep the first `qtim-reviewer` pass for each implementation phase. For a
`NOT APPROVED` verdict, main thread verifies findings against the code and the
Approved scope, then gives the owning role a bounded fix. A finding outside the
ticket or an explicit user constraint becomes a separate task; it does not
silently enlarge the current phase. If it blocks an acceptance criterion or a
required security gate, report the conflict as `Blocked` for an owner decision.

Allow at most **two fix-and-recheck rounds per phase** after the first reviewer
pass. Bind that budget to the stable WI/phase review boundary: restarting a task,
renaming a phase or replacing a reviewer does not reset it. In each round, run affected tests and a targeted check of the confirmed
findings and changed lines. Repeat the **full** reviewer gate only when the fix
changes the risk surface: new or broadened behavior beyond the reviewed diff,
security/authorization or data visibility, a public contract or documented
invariant, migration/data transformation, critical user flow, or another
high-risk category below. Any independent high-risk review
required for the phase remains required: recheck its findings after a fix, and
repeat its full scope when the fix changes that risk boundary. In particular,
a changed security boundary requires a full security re-review.

If an in-scope blocker remains after two rounds, stop the phase as `Blocked`.
Report the blocker, changes and checks attempted, remaining risk, and the
specific owner decision needed to extend the budget or revise scope. A skipped
full rerun is never presented as a passed rerun.

## ADR Stress-Test — Always

Каждый ADR, прошедший ADR filter, получает независимый второй проход **до** user approval. Это отдельный gate от risk-based review кода и он не выключается setup-настройкой independent review.

Main thread, а не architect:

1. Получает draft ADR и минимальный context pack: сам ADR, затронутые инварианты из charter/`memory/`, точные file paths для проверки.
2. Поднимает новый read-only agent thread **без истории основного task** (`fork_turns = "none"` или ближайший runtime-эквивалент clean context). Используй runtime/custom-agent sandbox enforcement, если он доступен; prompt-only read-only не называй механическим gate.
3. Фиксирует модель `gpt-6-astra` и reasoning `xhigh`. Если решение одновременно необратимо и затрагивает документированный инвариант — `max`.
4. Просит исходить из презумпции «решение некорректно, пока обратное не подтверждено» и искать нарушения инвариантов, нерассмотренные альтернативы, rollback/data-loss/security failure modes и open questions.
5. Передаёт findings architect, который проверяет их по коду и обновляет решение.
6. Требует в ADR строку `adr-stress-test: astra-adversary (xhigh|max) — N findings, M учтено`. При технической недоступности thread — `adr-stress-test: skipped — <reason>`.

После исправлений architect сверяет замечания точечно. Если правка изменила
архитектурную гарантию, границу безопасности, документированный инвариант или
необратимость решения, main thread повторяет независимый stress-test. После
двух раундов доработки с неустранённым блокером остановись со статусом
`Blocked` и предъяви владельцу открытый вопрос и варианты решения.

Не передавай оппоненту chain-of-thought, резюме рассуждений architect или текущую conversation history: независимость здесь обеспечивается чистым контекстом, а не другим провайдером. Self-play `$qtim-grill` остаётся первым проходом, но не заменяет clean-context adversary.

## When To Use

Ниже — отдельная политика **для фактического code diff**. Independent code review is mandatory to request when the diff matches any item in this canonical high-risk matrix:

- security/auth/tenant-scope visibility;
- money/billing/account state;
- documented domain invariants or public contracts;
- data-transform or destructive migrations;
- critical browser flows before release;
- high-risk performance/reliability changes;
- another demonstrably hard-to-rollback decision.

For a low-risk diff limited to copy, styles, documentation or an internal refactor without contract/invariant changes, the reviewer may skip it and must record `independent review: skipped (low-risk diff)`. Setup, role templates and orchestration copy this matrix without adding or removing categories.

For money-critical work, require convergence of two independent traces when runtime review is available. If it cannot run, record the failure and follow the fail-open/fail-closed policy from the project charter; do not silently call the gate passed.

Один отдельный clean-context read-only reviewer может одновременно закрыть
обязательный phase review и risk-based independent code review, если его source
pack и рассмотренный scope действительно покрывают оба gate. Второй reviewer не
запускается только ради другого ярлыка того же прохода. Для money-critical
сохраняются две независимые трассировки; ADR stress-test и SPEC_REVIEW не
заменяются review кода.

## Prompt Shape

Use tight prompts:

```text
You are an independent read-only reviewer.

Scope: <files/diff/ADR/feature>.
Read first: AGENTS.md, .codex/team-charter.md, memory/invariants.md.
Do not edit files.

Find defects in:
- correctness;
- security/authorization;
- data visibility;
- migrations/idempotency;
- race conditions;
- missing tests;
- rollback and error states.

Return findings only when grounded in code or documented invariants.
For each finding: file:line, severity P0-P3, invariant/rule, concrete fix.
Mark hypotheses explicitly.
```

Для ADR добавь: `Do not assume the proposed decision is correct. Check every claimed invariant/file reference. Return finding, evidence, impact, and a concrete mitigation; list unresolved open questions separately.`

## Integration

1. Main thread reads the review result.
2. Open each referenced file/line.
3. Confirm or reject each finding.
4. Route confirmed blockers to the owning role.
5. Record code-review summary in `memory/review-report.md`:
   - findings confirmed;
   - findings rejected and why;
   - skipped reason for a low-risk diff or if review could not run.

## Anti-Patterns

- Blindly applying independent reviewer advice.
- Asking for broad "look at the whole project" review.
- Letting a review thread edit code during review.
- Treating an unavailable mandatory SPEC_REVIEW as passed advisory review.
- Keeping raw review conclusions out of memory when they affect future decisions.
