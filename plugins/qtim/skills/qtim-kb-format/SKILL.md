---
name: qtim-kb-format
description: Use before creating or editing qtim project memory or feature process artifacts. Defines memory frontmatter, checked SHA, symbolic anchors, status labels, journal routing, and the docs/features .work boundary.
---

# qtim project knowledge format

Apply this skill before any write to `memory/` or process material in `docs/features/`, including setup, onboarding, retro, and feature completion. Respect stronger project instructions in `AGENTS.md`. Code at the selected base revision is the source for code facts. A recent `checked` is evidence of a prior review, not proof that a claim still holds.

## Memory file

`memory/MEMORY.md` is the concise index. Entry files are `memory/*.md`; history belongs in `memory/journal/` and is read on demand. Use one genre and one primary reader per entry file.

~~~yaml
---
name: <filename without .md>
description: <what is here and when to read it>
metadata:
  type: project
  genre: index | reference | invariant | procedure | decision | finding | journal
  audience: <roles> | none
  updated: YYYY-MM-DD
  checked: YYYY-MM-DD @ <commit-sha>
  status: current | archive
---
~~~

The index may also have `metadata.base: <ref>`. Set `checked` only after every code claim and anchor in that file has been reviewed against that commit. A narrow edit updates `updated` and leaves `checked` alone. The initial setup must review all claims before stamping its initial SHA; do not invent a checked revision. Use `qtim-kb-refresh` for whole-file revalidation and stamping.
For an existing legacy file without this frontmatter, a narrow edit must preserve
its unrelated content. Do not invent a `checked` value or silently convert every
claim; report the file for an explicit `$qtim-kb-refresh` migration. New files
use the format above from the start.

After the header, write a title and one navigator line: `> **Когда читать:** … · **Не здесь:** …`. Preserve filenames and `##` headings used by consumers. Keep entry files around 1200 words; the scanner warns over 1800. Move episodic closed material to `memory/journal/<relative memory path with / replaced by ->.md>` and leave a short router in the entry. Do not re-summarize the journal in the entry.

## Claims and anchors

- Code facts use a repo-relative symbolic anchor such as `src/service.ts#Service.run`; verify that the symbol exists **and** supports the claim in the selected revision. For JSON or YAML, use a key path. Line numbers and bare basenames are not stable anchors.
- `open:` means a live defect and stays in the entry. Change it to `fixed: <sha>` only when the code and a fix commit touching the anchor path support closure. `claimed:` records an external or unverified report; `policy:` records a project decision. These labels never stand in for evidence.
- Avoid counts that silently age, such as the current number of guards or migrations. Give a command or a stable invariant instead.
- Before adding a claim, find its existing home in project rules, skills, charter, and nearby memory. Keep one fact in one home and link to it elsewhere.
- `memory/decisions.md` is a short decision and feature pointer registry. Keep feature pointers in the entry when a feature closes; do not move them to journal.

Use patch or file editing tools that preserve unrelated user changes. After writes, run the read-only `scan` in [qtim-kb-refresh/scripts/kb_scan.py](../qtim-kb-refresh/scripts/kb_scan.py); its format and anchor checks are mechanical, so review semantic accuracy yourself.

## Feature process files

Keep canonical product artifacts directly in `docs/features/<slug>/`. Put consult output, intermediate review reports, run logs, and other disposable process material in `docs/features/<slug>/.work/`, covered by the root `.gitignore` rule `docs/features/**/.work/`. Do not rename or delete canonical artifacts as cleanup. Archive and remove process material only after merge evidence and the owner's decision; preserve the durable decision pointer.

Do not write to Codex runtime state, agent memory, or other external stores as part of memory maintenance. Report drift in those stores to their owner.
