# AGENTS.md

This repository is a Codex plugin marketplace with one plugin: `qtim`.

All content is primarily Russian. The repository has no build step and no application runtime; the source is Markdown, JSON, and TOML used by Codex.

## Structure

- `.agents/plugins/marketplace.json` — Codex marketplace manifest exposing `plugins/qtim`.
- `plugins/qtim/.codex-plugin/plugin.json` — Codex plugin manifest.
- `plugins/qtim/skills/` — Codex workflows: `qtim-setup`, `qtim-feature`, `qtim-mission`, `qtim-onboard`, `qtim-product-onboard`, `qtim-kb-refresh`, `qtim-team-up`, `qtim-team-lazy`, `qtim-team-retro`, `qtim-team-down`, `qtim-doctor`, `qtim-update`; bundled disciplines: `qtim-debug-loop`, `qtim-prototype`, `qtim-brainstorm`, `qtim-grill`, `qtim-minimal-diff`, `qtim-kb-format`.
- `plugins/qtim/agents/` — Codex custom agent TOML templates (dev roles + `product.toml` for the PM track) copied by `$qtim-setup` into target projects.
- `plugins/qtim/reference/` — shared mechanics plus canonical `project-hooks.json` for optional project PostToolUse and upgrade notes for generated-state migrations.
- `plugins/qtim/hooks/hooks.json` — plugin-bundled Codex `SessionStart` / `SubagentStop` lifecycle hooks.
- `docs/pm-track-backlog.md` — prioritized improvement backlog for the PM track (research-based, ICE-scored); start here when planning PM-track work.
- `docs/claude-port-map.md` — porting map to the Claude Code sibling project (toiiia/qtim-agent-team): conventions table, process, feature parity; read before porting features either way. The Claude working clone lives at `../qtim-agent-team-claude`.

## Architecture Rules

- This is Codex-native. Do not add `.claude/*`, `.claude-plugin/*`, Claude slash commands, or Claude Agent Teams primitives.
- Use Codex skills instead of slash commands.
- Use `.codex/team-charter.md` and `.codex/agents/*.toml` for generated target-project state.
- Plugin layer owns qtim `SessionStart` / `SubagentStop`; project `.codex/hooks.json` is only for optional `PostToolUse` or pre-existing user hooks. Preserve foreign hook entries and use canonical nested command schema.
- Charter is track-aware: dev and PM tracks live between `qtim:track:*` markers; generation must never clobber the other track.
- qtim subagent workflows require an explicit skill invocation or direct delegation request. Main team-lead runs on `gpt-5.6-sol` + `ultra` and may proactively delegate only inside that authorized scope. Agent threads are task-scoped and recoverable only when the runtime exposes them; do not imply hidden persistent team state.
- The main thread owns fan-out. Child agents do not recursively spawn qtim teams; respect the runtime thread cap and batch independent work when needed.
- Main thread is the team lead; subagent outputs are advisory until checked.
- Durable project decisions belong in `memory/`, not only in chat.
- Before writing `memory/` or feature process artifacts, load `$qtim-kb-format`; use `$qtim-kb-refresh` for drift in existing knowledge.
- Independent review is a separate read-only Codex agent thread, not "Codex as an external consultant". Every created ADR gets a clean-context Sol adversary before approval, regardless of the optional risk-based code-review setting.
- Role templates use explicit atomic GPT-5.6 `model` + `model_reasoning_effort` pairs; never write `model = "inherit"`. Preserve user overrides during migration.
- Bundled disciplines are role-agnostic practices, not orchestration engines: do not put main-thread fan-out, persistent-team assumptions, or qtim workflow ownership inside `qtim-debug-loop`, `qtim-prototype`, `qtim-brainstorm`, `qtim-grill`, or `qtim-minimal-diff`.
- When adapting a third-party MIT skill, add the complete applicable copyright and permission notice to `plugins/qtim/THIRD_PARTY_NOTICES.md`; an attribution link in `SKILL.md` alone is insufficient.
- On every model-generation upgrade, audit role templates for compensating step-by-step recipes. Remove recipes that newer models no longer need, but preserve structural invariants, risk-based gates, durable memory, and verification contracts.

## Workspace And Deploy

- This fork (`JesusLeto/qtim-agent-team-codex`) is the source of truth for its changes. Publish a reviewable branch to this fork; `trushhh777/qtim-agent-team` is the upstream repository. Verify the actual Git remote before pushing.
- After deploy, plugin users update via `codex plugin marketplace upgrade qtim-agent-team` + `codex plugin add qtim@qtim-agent-team` + new thread; project teams migrate with `$qtim-update`.
- `.claude/` is local session state, gitignored — never commit it.
- The Claude Code sibling is `JesusLeto/qtim-agent-team` (upstream `toiiia/qtim-agent-team`). Port shared behavior semantically using `docs/claude-port-map.md`; keep Codex and Claude runtime files separate.

## Validation

Run locally before handing off changes:

```bash
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/qtim/.codex-plugin/plugin.json > /dev/null
python3 -m json.tool plugins/qtim/hooks/hooks.json > /dev/null
python3 -m json.tool plugins/qtim/reference/project-hooks.json > /dev/null
python3 .github/scripts/check_hooks.py
python3 .github/scripts/check_placeholders.py
python3 .github/scripts/check_skills.py
python3 .github/scripts/check_skill_refs.py
python3 .github/scripts/check_skill_refs.py --self-test
python3 .github/scripts/check_missions.py
python3 .github/scripts/check_links.py
python3 .github/scripts/check_codex_agents.py
python3 .github/scripts/check_migrations.py
python3 .github/scripts/check_update_fixtures.py
python3 .github/scripts/check_update_fixtures.py --self-test
python3 .github/scripts/check_golden.py
python3 plugins/qtim/skills/qtim-kb-refresh/scripts/kb_scan.py scan --base HEAD > /dev/null
```

In CI, use repo-local scripts only. Before release, also run Codex `plugin-creator`'s `validate_plugin.py plugins/qtim` from the local Codex skill installation if it is available.

## Release Notes

For meaningful plugin changes, bump `version` in `plugins/qtim/.codex-plugin/plugin.json` and update `CHANGELOG.md`.

If the release changes the generated project state (`.codex/*`, `memory/`, project `AGENTS.md` section), also add a migration section to `plugins/qtim/reference/upgrade-notes.md` — `$qtim-update` migrates projects strictly by that file. If generated state is unchanged, add a "миграция не требуется" entry.

Generated state carries version stamps (`<!-- qtim-version: ... -->` in the charter, `# qtim-version: ...` in generated agent TOMLs); `$qtim-setup` writes them from the plugin manifest version.

Commit style: conventional commits with Russian descriptions, for example `feat(setup): ...`, `fix(agents): ...`, `docs(readme): ...`.
