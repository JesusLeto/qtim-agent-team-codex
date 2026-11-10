<!-- qtim-version: 2.17.0 -->
# Stages migration fixture

## Roles
| Role | Agent |
|---|---|
| product | qtim-product |
| reviewer | qtim-reviewer |

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

## Working rules
code-review: disabled
Approved plan авторизует следующие standalone-фазы; feature-sequential advance принадлежит исходному coordinator через $qtim-feature.
MANUAL-CHARTER-STAGES: preserve byte-for-byte.

<!-- qtim:track:dev:start -->
MANUAL-DEV-STAGES: preserve byte-for-byte; implement/test/review stays unchanged.
<!-- qtim:track:dev:end -->

<!-- qtim:track:pm:start -->
Feature workflow: interview -> spec.md + SPEC_REVIEW -> approval -> Stage/WI/Ticket handoff.
Stable S*/WI-*/Txx link tickets/Txx-<slug>.md with AC/DRI/contributing/technical prerequisites and stage/final gates; one stage/ticket is valid.
Execution via $qtim-feature has one original coordinator and one chat per ticket; worker returns proposal. Approval alone starts nothing; owner acceptance and advance are explicit.
Durable receipts/Txx-aN.md differ from .work/Txx/ raw/proposals; cleanup preserves contracts/receipts/runtime. Legacy/spec-only need an explicit owner adapter.
SPEC_REVIEW remains mandatory when code-review: disabled; this setting controls code review only.
Reviewed revision and Approved revision identify the current approved spec revision.
MANUAL-PM-STAGES: preserve byte-for-byte.
<!-- qtim:track:pm:end -->
