#!/usr/bin/env python3
"""Validate Codex custom agent TOML templates."""
import pathlib
import re
import sys

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None

REQUIRED = {"name", "description", "developer_instructions"}
EXPECTED_MODEL_POLICIES = {
    "architect.toml": ("gpt-6-astra", "xhigh"),
    "database.toml": ("gpt-6-sol", "high"),
    "frontend.toml": ("gpt-6-sol", "high"),
    "product.toml": ("gpt-6-sol", "high"),
    "reviewer.toml": ("gpt-6-astra", "xhigh"),
    "testing.toml": ("gpt-6-luna", "medium"),
}
EXPECTED_MARKERS = {
    "architect.toml": [
        "$qtim-brainstorm",
        "$qtim-prototype",
        "$qtim-grill",
        "дорого откатить",
        "будущий читатель",
        "реальный trade-off",
        "expand-contract",
        "ADR готов к независимому stress-test",
        "adr-stress-test: astra-adversary",
        "adr-stress-test: pending",
        "$qtim-minimal-diff",
        "Новый слой и новая зависимость — архитектурное решение",
        "Чистая избыточность — рекомендация",
    ],
    "database.toml": [
        "$qtim-debug-loop",
        "$qtim-minimal-diff",
        "constraint, index или trigger",
        "обязательная минимальная проверка",
    ],
    "frontend.toml": [
        "$qtim-debug-loop",
        "$qtim-minimal-diff",
        "Trust-boundary validation",
        "одну минимальную проверку",
    ],
    "product.toml": ["вертикальный срез", "DRI", "contributing", "expand-contract"],
    "reviewer.toml": [
        "Canonical high-risk matrix",
        "обязательный запрос",
        "skipped (low-risk diff)",
        "## Adversary",
        "none (money-critical)",
        "Minimal-diff review (recommendations, not automatic blockers)",
        "$qtim-minimal-diff",
        "pure excess",
    ],
    "testing.toml": ["$qtim-debug-loop", "{{DEV_CMD}}", "dev server command/status"],
}
LANGUAGE_CONTRACT = (
    "Reason internally and message peer agents in **English** — token economy "
    "(Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing "
    "output in Russian**: contract documents, review findings, and anything relayed "
    "to the client."
)
REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
MODEL_REASONING_EFFORTS = {
    "gpt-6-astra": {"low", "medium", "high", "xhigh", "max", "ultra"},
    "gpt-6-sol": {"low", "medium", "high", "xhigh", "max", "ultra"},
    "gpt-6-luna": {"low", "medium", "high", "xhigh", "max"},
}
FORBIDDEN = [
    ".claude",
    "CLAUDE_PLUGIN_ROOT",
    "SendMessage",
    "TaskCreate",
    "TaskUpdate",
    "TeamCreate",
    "TeamDelete",
    "team_name",
]

bad = []
root = pathlib.Path("plugins/qtim/agents")
paths = sorted(root.glob("*.toml"))

for path in paths:
    text = path.read_text(encoding="utf-8")

    if tomllib is not None:
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as err:
            bad.append(f"{path}: invalid TOML: {err}")
            continue

    payload = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(r"^([A-Za-z0-9_]+)\s*=\s*(.+)$", text, re.MULTILINE)
    }

    missing = sorted(REQUIRED - payload.keys())
    if missing:
        bad.append(f"{path}: missing required fields: {', '.join(missing)}")

    for key in ("name", "description"):
        value = payload.get(key, "")
        if not re.match(r'^".+"$', value):
            bad.append(f"{path}: `{key}` must be a non-empty string")

    if "developer_instructions = '''" not in text:
        bad.append(f"{path}: `developer_instructions` must be a multiline literal string")
    elif text.count("'''") < 2:
        bad.append(f"{path}: `developer_instructions` multiline string is not closed")

    for token in FORBIDDEN:
        if token in text:
            bad.append(f"{path}: forbidden Claude-only token `{token}`")

    if "../" in text:
        bad.append(
            f"{path}: plugin-relative path (`../`) — шаблон копируется в целевой проект, "
            "где внутренние пути плагина не резолвятся; ссылайся на charter или memory/"
        )

    m = re.search(r'^model\s*=\s*"([^"]*)"', text, re.MULTILINE)
    if m and not re.fullmatch(r"gpt-(?:\d+\.\d+(?:-[a-z0-9-]+)?|\d+-[a-z0-9-]+)", m.group(1)):
        bad.append(
            f"{path}: `model = \"{m.group(1)}\"` — нужен полный variant slug; "
            "короткий alias вроде `gpt-6` не запускает роль"
        )

    reasoning = re.search(
        r'^model_reasoning_effort\s*=\s*"([^"]*)"', text, re.MULTILINE
    )
    if bool(m) != bool(reasoning):
        bad.append(
            f"{path}: `model` and `model_reasoning_effort` must be present together or both omitted"
        )
    if reasoning and reasoning.group(1) not in REASONING_EFFORTS:
        bad.append(
            f"{path}: unsupported `model_reasoning_effort = \"{reasoning.group(1)}\"`"
        )

    supported_efforts = MODEL_REASONING_EFFORTS.get(m.group(1)) if m else None
    if reasoning and supported_efforts and reasoning.group(1) not in supported_efforts:
        bad.append(
            f"{path}: `{m.group(1)}` does not support reasoning effort "
            f"`{reasoning.group(1)}`"
        )

    expected = EXPECTED_MODEL_POLICIES.get(path.name)
    if expected:
        actual = (
            m.group(1) if m else None,
            reasoning.group(1) if reasoning else None,
        )
        if actual != expected:
            bad.append(
                f"{path}: expected qtim model policy {expected[0]}/{expected[1]}, "
                f"found {actual[0]}/{actual[1]}"
            )

    if path.name == "reviewer.toml":
        sandbox = re.search(r'^sandbox_mode\s*=\s*"([^"]*)"', text, re.MULTILINE)
        if not sandbox or sandbox.group(1) != "read-only":
            bad.append(f"{path}: reviewer must enforce `sandbox_mode = \"read-only\"`")

    for marker in EXPECTED_MARKERS.get(path.name, []):
        if marker not in text:
            bad.append(f"{path}: missing current qtim discipline marker `{marker}`")

    if "## Language" not in text or LANGUAGE_CONTRACT not in text:
        bad.append(f"{path}: missing exact mandatory qtim language contract")

if not paths:
    bad.append(f"{root}: no Codex custom agent templates found")

missing_templates = sorted(set(EXPECTED_MODEL_POLICIES) - {path.name for path in paths})
if missing_templates:
    bad.append(f"{root}: missing expected templates: {', '.join(missing_templates)}")

CONTRACT_MARKERS = {
    pathlib.Path("plugins/qtim/reference/model-profiles.md"): [
        "`gpt-6-astra` + `ultra`",
        "`gpt-6-astra` + `xhigh`",
        "`gpt-6-sol` + `high`",
        "`gpt-6-luna` + `medium`",
        "`gpt-6-astra` + `xhigh`; `max`",
    ],
    pathlib.Path("plugins/qtim/reference/independent-review.md"): [
        "fork_turns = \"none\"",
        "`gpt-6-astra` и reasoning `xhigh`",
        "`adr-stress-test: astra-adversary (xhigh|max)",
        "не выключается setup-настройкой independent review",
    ],
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"): [
        "team-lead `gpt-6-astra` + `ultra`",
        "built-in explorer `gpt-6-luna` + `medium`",
        "ADR stress-test остаётся включён",
    ],
}
for contract_path, markers in CONTRACT_MARKERS.items():
    if not contract_path.exists():
        bad.append(f"{contract_path}: missing model/review contract")
        continue
    contract_text = contract_path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in contract_text:
            bad.append(f"{contract_path}: missing contract marker `{marker}`")

LANGUAGE_SURFACES = {
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"): (
        LANGUAGE_CONTRACT,
        "Language contract копируй из template дословно",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-update/SKILL.md"): (
        "для stamp 2.14.0+ каждый сопоставленный qtim agent TOML",
        "peer messages — English",
        "user-facing output — Russian",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"): (
        "Для stamp 2.14.0+",
        "English для internal/peer",
        "Russian для user-facing output",
    ),
    pathlib.Path("plugins/qtim/reference/upgrade-notes.md"): (
        "## 2.14.0",
        LANGUAGE_CONTRACT,
    ),
    pathlib.Path("plugins/qtim/reference/orchestration-patterns.md"): (
        "prompts, follow-ups и иные сообщения peer agents пиши на English",
        "остаётся на Russian",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-team-up/SKILL.md"): (
        "Write every peer-agent prompt and follow-up in English",
        "user-facing artifacts and anything intended for the user in Russian",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-mission/SKILL.md"): (
        "coordinator-to-peer",
        "user-facing artifacts и итог mission — на Russian",
    ),
}
for contract_path, markers in LANGUAGE_SURFACES.items():
    if not contract_path.exists():
        bad.append(f"{contract_path}: missing qtim language surface")
        continue
    contract_text = contract_path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in contract_text:
            bad.append(f"{contract_path}: missing language marker `{marker}`")

if bad:
    print("Codex agent template validation failed:")
    print("\n".join(bad))
    sys.exit(1)

print("OK: Codex custom agent templates are valid")
