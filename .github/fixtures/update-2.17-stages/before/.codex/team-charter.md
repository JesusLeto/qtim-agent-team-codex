<!-- qtim-version: 2.16.1 -->
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
Approved plan авторизует следующие фазы.
MANUAL-CHARTER-STAGES: preserve byte-for-byte.

<!-- qtim:track:dev:start -->
MANUAL-DEV-STAGES: preserve byte-for-byte; implement/test/review stays unchanged.
<!-- qtim:track:dev:end -->

<!-- qtim:track:pm:start -->
Feature workflow: interview -> spec.md + SPEC_REVIEW -> approval -> handoff.
SPEC_REVIEW remains mandatory when code-review: disabled; this setting controls code review only.
Reviewed revision and Approved revision identify the current approved spec revision.
MANUAL-PM-STAGES: preserve byte-for-byte.
<!-- qtim:track:pm:end -->
