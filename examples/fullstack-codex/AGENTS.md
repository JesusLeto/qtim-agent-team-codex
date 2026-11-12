# Example project

Пользовательские правила примера сохраняются вне managed block.

<!-- qtim:contract:start -->
## Команда qtim

Подробный контракт: `.codex/team-charter.md`; роли: `.codex/agents/`; решения: `memory/`.
qtim workflow запускается только явным skill/delegation request. Main thread владеет fan-out,
проверяет advisory outputs и запускается на `gpt-6-astra` + `ultra`. Каждый ADR проходит
clean-context Astra adversary. `$qtim-mission` с глаголом исполнения или недвусмысленная
просьба провести несколько Codex peer tasks как одну mission создаёт видимые задачи
только после явного запуска Approved graph; mission workers не создают descendants;
writers изолированы worktree, commits integrate topologically через transaction
affected gate до locked exact-old ff-only promotion; portable state checkpoint-ится
отдельно, затем отдельный verifier закрывает общий gate.
После обновления используй `$qtim-update`, при сбое — `$qtim-doctor`.
Новые feature используют spec.md с этапами и `tickets/Txx-<slug>.md`; SPEC_REVIEW
предшествует approval. Исполнение — через `$qtim-feature`: один coordinator,
отдельный чат на тикет; worker возвращает proposal. Approval само не запускает работу.
Правила ревизий, gates и durable receipts — в charter.
Перед записью `memory/` или `docs/features/` вызови `$qtim-kb-format`;
при обнаруженном дрейфе предложи `$qtim-kb-refresh`.

## Language

Reason internally and message peer agents in **English**. Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

<!-- qtim:contract:end -->
