#!/usr/bin/env python3
"""Validate the semantic full-stack generated-state example."""
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[2]
version = json.loads(
    (root / "plugins/qtim/.codex-plugin/plugin.json").read_text(encoding="utf-8")
)["version"]
example = root / "examples/fullstack-codex"
bad = []


def need(condition, message):
    if not condition:
        bad.append(message)


agents_md = (example / "AGENTS.md").read_text(encoding="utf-8")
need(agents_md.count("<!-- qtim:contract:start -->") == 1, "one AGENTS start marker required")
need(agents_md.count("<!-- qtim:contract:end -->") == 1, "one AGENTS end marker required")
charter = (example / ".codex/team-charter.md").read_text(encoding="utf-8")
need(charter.startswith(f"<!-- qtim-version: {version} -->"), "charter stamp mismatch")
language_markers = (
    "## Language",
    "Reason internally and message peer agents in **English**",
    "Keep **user-facing output in Russian**",
)
for marker in language_markers:
    need(marker in agents_md, f"AGENTS missing language marker {marker}")
    need(marker in charter, f"charter missing language marker {marker}")
for marker in (
    "qtim:track:dev:start", "qtim:track:dev:end", "qtim:track:pm:start",
    "qtim:track:pm:end", "Производная self-contained сводка",
    "memory/decisions.md", "последним completion marker", "Что запускать дальше",
    "$qtim-mission", "recommendation ничего не запускает", "integration target",
    "integrate topologically", "clean-context verifier",
    "$qtim-minimal-diff", "recommendation-only",
    "Approved scope", "fix-and-recheck", "$qtim-kb-format",
    "$qtim-kb-refresh", "PRD-only", "estimate.md", "Archived",
):
    need(marker in charter, f"charter missing {marker}")
for marker in (
    "$qtim-mission", "worktree", "topologically", "workers не создают descendants",
    "$qtim-kb-format", "$qtim-kb-refresh",
):
    need(marker in agents_md, f"AGENTS missing {marker}")

gitignore = (example / ".gitignore").read_text(encoding="utf-8").splitlines()
need(
    gitignore.count(".codex/qtim-runtime/") == 1,
    "golden .gitignore must contain one qtim runtime entry",
)
need(
    gitignore.count("docs/features/**/.work/") == 1,
    "golden .gitignore must contain one feature workspace entry",
)

expected = {
    "architect.toml": ("qtim-architect", "gpt-6-astra", "xhigh"),
    "database.toml": ("qtim-database", "gpt-6-sol", "high"),
    "frontend.toml": ("qtim-frontend", "gpt-6-sol", "high"),
    "product.toml": ("qtim-product", "gpt-6-sol", "high"),
    "reviewer.toml": ("qtim-reviewer", "gpt-6-astra", "xhigh"),
    "testing.toml": ("qtim-testing", "gpt-6-luna", "medium"),
}
minimal_diff_agents = {"architect.toml", "database.toml", "frontend.toml", "reviewer.toml"}
for filename, policy in expected.items():
    path = example / ".codex/agents" / filename
    need(path.is_file(), f"missing {filename}")
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    need(text.startswith(f"# qtim-version: {version}"), f"{filename} stamp mismatch")
    need("{{" not in text, f"{filename} has unresolved placeholder")
    for marker in language_markers:
        need(marker in text, f"{filename} missing language marker {marker}")
    payload = {
        match.group(1): match.group(2)
        for match in re.finditer(r'^([A-Za-z0-9_]+)\s*=\s*"([^"]*)"', text, re.MULTILINE)
    }
    need(
        (payload.get("name"), payload.get("model"), payload.get("model_reasoning_effort")) == policy,
        f"{filename} model policy mismatch",
    )
    if filename in minimal_diff_agents:
        need("$qtim-minimal-diff" in text, f"{filename} has no minimal-diff contract")
    if filename == "reviewer.toml":
        need(payload.get("sandbox_mode") == "read-only", "reviewer is not read-only")
        for marker in ("Approved scope", "fix-and-recheck", "$qtim-kb-format"):
            need(marker in text, f"reviewer has no {marker} contract")
    if filename == "testing.toml":
        need("npm run dev" in text, "tester has no dev command")

config = json.loads((example / ".codex/screenshots-gate.json").read_text(encoding="utf-8"))
directory = pathlib.PurePosixPath(config.get("directory", ""))
need(config.get("mode") == "blocking", "golden screenshot gate not blocking")
need(not directory.is_absolute() and ".." not in directory.parts, "unsafe screenshot directory")
for filename in ("MEMORY.md", "project-map.md", "commands.md", "safety.md",
                 "invariants.md", "decisions.md", "review-report.md", "bug-log.md"):
    need((example / "memory" / filename).is_file(), f"missing memory/{filename}")
memory_index = (example / "memory/MEMORY.md").read_text(encoding="utf-8")
need("memory/missions/<slug>/" in memory_index, "memory index has no on-demand missions")
need(
    "gitignored `.codex/qtim-runtime/`" in memory_index,
    "memory index does not separate opaque mission runtime",
)
for marker in ("memory/retro-log.md", "minimal-diff:", "trigger evidence", "next action"):
    need(marker in memory_index, f"memory index has no minimal-diff retro marker `{marker}`")
if bad:
    print("Golden validation failed:\n- " + "\n- ".join(bad))
    sys.exit(1)
print(f"OK: semantic golden project matches qtim {version}")
