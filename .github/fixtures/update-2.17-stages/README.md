# Stage/ticket migration snapshots

Documented 2.16.1 -> 2.17.0 targets for PM charter, product and the managed AGENTS summary.
Manual text inside/outside managed regions, the dev track, disabled code-review
setting and an atomic product model override remain unchanged. Foreign hooks/roles
and ambiguous/pending stamp controls remain covered by the historical fixtures.

`check_update_fixtures.py` checks preservation and negative controls. These snapshots
do not execute LLM migration. The same checker exercises the real scanner CLI in a
disposable Git tree for legacy/spec-only/ticket inventory and durable Markdown loss;
deleting fixture `.work/` does not prove live team-down or App acceptance.
