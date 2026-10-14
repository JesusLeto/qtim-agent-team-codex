<!-- qtim-version: 2.16.0-experimental.1 -->
# PM-only fixture charter

## Roles

| Role | Agent |
|---|---|
| product | qtim-product |
| reviewer | qtim-reviewer |

## Language

Reason internally and message peer agents in **English** — token economy (Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing output in Russian**: contract documents, review findings, and anything relayed to the client.

## Working rules

code-review: disabled
MANUAL-CHARTER-FEATURE: preserve byte-for-byte.

<!-- qtim:track:pm:start -->
## PM track

Feature workflow: interview -> spec.md + SPEC_REVIEW -> approval -> handoff.
SPEC_REVIEW remains mandatory when code-review: disabled; this setting controls code review only.
Reviewed revision and Approved revision identify the current approved spec revision.
MANUAL-PM-FEATURE: preserve byte-for-byte.
<!-- qtim:track:pm:end -->
