# User instructions
MANUAL-AGENTS-STAGES: preserve byte-for-byte.

<!-- qtim:contract:start -->
## Команда qtim
Подробный контракт: `.codex/team-charter.md`.
После обновления используй `$qtim-update`, при сбое — `$qtim-doctor`.
Новые feature используют spec.md с этапами и `tickets/Txx-<slug>.md`; SPEC_REVIEW
предшествует approval. Исполнение — через `$qtim-feature`: один coordinator,
отдельный чат на тикет; worker возвращает proposal. Approval само не запускает работу.
Правила ревизий, gates и durable receipts — в charter.
MANUAL-MANAGED-STAGES: preserve byte-for-byte.

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.
<!-- qtim:contract:end -->

User text after the managed region stays unchanged.
