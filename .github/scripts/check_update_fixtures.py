#!/usr/bin/env python3
"""Validate migration preservation fixtures; these do not execute Codex updates."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / ".github/fixtures/update-2.13-extended"
BEFORE = FIXTURE / "before/.codex"
AFTER = FIXTURE / "after/.codex"
AMBIGUOUS_BEFORE = FIXTURE / "ambiguous/before/.codex"
AMBIGUOUS_AFTER = FIXTURE / "ambiguous/after/.codex"
LANGUAGE_FIXTURE = ROOT / ".github/fixtures/update-2.14-language"
LANGUAGE_BEFORE = LANGUAGE_FIXTURE / "before"
LANGUAGE_AFTER = LANGUAGE_FIXTURE / "after"
FEATURE_FIXTURE = ROOT / ".github/fixtures/update-2.16-feature"
FEATURE_BEFORE = FEATURE_FIXTURE / "before"
FEATURE_AFTER = FEATURE_FIXTURE / "after"
FEATURE_VERSION = "2.16.0-experimental.1"
OLD_FEATURE_WORKFLOW = "Feature workflow: intake -> PRD -> decomposition -> optional estimate -> plan -> handoff."
NEW_FEATURE_WORKFLOW = (
    "Feature workflow: interview -> spec.md + SPEC_REVIEW -> approval -> handoff.\n"
    "SPEC_REVIEW remains mandatory when code-review: disabled; this setting controls code review only.\n"
    "Reviewed revision and Approved revision identify the current approved spec revision."
)
OLD_PRODUCT_WORKFLOW = "Produce intake.md, prd.md, decomposition.md, optional estimate.md and plan.md."
NEW_PRODUCT_WORKFLOW = (
    "Help the main editor interview and produce spec.md; preserve approved decisions "
    "and request SPEC_REVIEW before owner approval."
)
BAD = []
CUSTOM_BLOCK = (
    "\nПеред нетривиальной реализацией пройди `$qtim-minimal-diff`. "
    "Approved scope и protected zones не сокращаются; disputed scope возвращается "
    "main thread. Нетривиальная логика получает одну минимальную breaking check "
    "без новой test infrastructure.\n"
)
BEFORE_CHARTER_CELL = (
    "| devops | qtim-devops | Writes deployment and CI code | "
    "Preserve deployment safety gates |"
)
AFTER_CHARTER_CELL = (
    "| devops | qtim-devops | Writes deployment and CI code | "
    "Preserve deployment safety gates; `$qtim-minimal-diff` before non-trivial implementation |"
)
CUSTOM_MARKERS = (
    "$qtim-minimal-diff",
    "Approved scope",
    "protected zones",
    "disputed scope",
    "одну минимальную breaking check",
    "без новой test infrastructure",
)
LANGUAGE_CONTRACT = (
    "## Language\n\n"
    "Reason internally and message peer agents in **English** — token economy "
    "(Cyrillic ≈1.5–2× more tokens per equivalent content). Keep **user-facing "
    "output in Russian**: contract documents, review findings, and anything relayed "
    "to the client."
)


def need(condition, message):
    if not condition:
        BAD.append(message)


def text(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        BAD.append(f"missing fixture file: {path.relative_to(ROOT)}")
        return ""


def track_block(charter, track):
    match = re.search(
        rf"<!-- qtim:track:{track}:start -->.*?<!-- qtim:track:{track}:end -->",
        charter,
        re.DOTALL,
    )
    return match.group(0) if match else None


def parse_role(body):
    values = {
        match.group(1): match.group(2)
        for match in re.finditer(r'^([A-Za-z0-9_]+)\s*=\s*"([^"]*)"', body, re.MULTILINE)
    }
    instructions = re.search(
        r'^developer_instructions\s*=\s*"""(.*?)"""',
        body,
        re.MULTILINE | re.DOTALL,
    )
    values["developer_instructions"] = instructions.group(1) if instructions else ""
    return values


def custom_role_preserved(before, after):
    if after.count(CUSTOM_BLOCK) != 1:
        return False
    normalized = after.replace("# qtim-version: 2.13.0", "# qtim-version: 2.12.0", 1)
    normalized = normalized.replace(CUSTOM_BLOCK, "", 1)
    return normalized == before


def charter_preserved(before, after):
    if after.count(AFTER_CHARTER_CELL) != 1:
        return False
    normalized = after.replace("<!-- qtim-version: 2.13.0 -->", "<!-- qtim-version: 2.12.0 -->", 1)
    normalized = normalized.replace(AFTER_CHARTER_CELL, BEFORE_CHARTER_CELL, 1)
    return normalized == before


def foreign_bytes_preserved(before, after):
    return bool(before) and before == after


def feature_charter_preserved(before, after):
    normalized = after.replace(
        f"<!-- qtim-version: {FEATURE_VERSION} -->", "<!-- qtim-version: 2.15.1 -->", 1
    ).replace("| reviewer | qtim-reviewer |\n", "", 1).replace(
        NEW_FEATURE_WORKFLOW, OLD_FEATURE_WORKFLOW, 1
    )
    return after.count(NEW_FEATURE_WORKFLOW) == 1 and normalized == before


def feature_product_preserved(before, after):
    normalized = after.replace(
        f"# qtim-version: {FEATURE_VERSION}", "# qtim-version: 2.15.1", 1
    ).replace(NEW_PRODUCT_WORKFLOW, OLD_PRODUCT_WORKFLOW, 1)
    return after.count(NEW_PRODUCT_WORKFLOW) == 1 and normalized == before


def tree_snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def pending_bytes_preserved(before, after):
    return bool(before) and before == after


def pending_state_held(charter, roles):
    if not charter.startswith("<!-- qtim-version: 2.12.0 -->"):
        return False
    if "2.13.0" in charter or any("2.13.0" in role for role in roles):
        return False
    if not roles or any(not role.startswith("# qtim-version: 2.12.0") for role in roles):
        return False
    names = [parse_role(role).get("name") for role in roles]
    if names.count("qtim-devops") < 2:
        return False
    return any(
        "$qtim-minimal-diff" in role
        and not all(marker in parse_role(role).get("developer_instructions", "") for marker in CUSTOM_MARKERS)
        for role in roles
    )


before_charter = text(BEFORE / "team-charter.md")
after_charter = text(AFTER / "team-charter.md")
need(before_charter.startswith("<!-- qtim-version: 2.12.0 -->"), "before charter stamp mismatch")
need(after_charter.startswith("<!-- qtim-version: 2.13.0 -->"), "after charter stamp mismatch")
need(
    charter_preserved(before_charter, after_charter),
    "charter changed outside the target stamp and one mandatory-practice cell",
)
for track in ("dev", "pm"):
    need(track_block(before_charter, track) is not None, f"before charter missing {track} track")
    need(
        track_block(before_charter, track) == track_block(after_charter, track),
        f"{track} track was not preserved byte-for-byte",
    )
need(
    BEFORE_CHARTER_CELL in before_charter,
    "fixture does not identify the generated custom role through the charter roster",
)
need(
    AFTER_CHARTER_CELL in after_charter,
    "after charter does not add minimal-diff to the custom code-writing role cell",
)

before_role_path = BEFORE / "agents/qtim-devops.toml"
after_role_path = AFTER / "agents/qtim-devops.toml"
before_role_text = text(before_role_path)
after_role_text = text(after_role_path)
before_role = parse_role(before_role_text)
after_role = parse_role(after_role_text)
need(before_role.get("developer_instructions"), "before custom role has no multiline instructions")
need(after_role.get("developer_instructions"), "after custom role has no multiline instructions")

need(before_role_text.startswith("# qtim-version: 2.12.0"), "before custom role stamp mismatch")
need(after_role_text.startswith("# qtim-version: 2.13.0"), "after custom role stamp mismatch")
need(
    custom_role_preserved(before_role_text, after_role_text),
    "custom role changed outside the target stamp and one exact additive minimal-diff block",
)
need(before_role.get("name") == after_role.get("name") == "qtim-devops", "custom role name drift")
need(
    (before_role.get("model"), before_role.get("model_reasoning_effort"))
    == (after_role.get("model"), after_role.get("model_reasoning_effort"))
    == ("gpt-5.6-terra", "high"),
    "custom role user model override was not preserved",
)
for marker in CUSTOM_MARKERS:
    need(marker in after_role.get("developer_instructions", ""), f"custom role missing `{marker}`")

for relative in ("agents/foreign-agent.toml", "agents/qtim-foreign-near-miss.toml", "hooks.json"):
    before_bytes = (BEFORE / relative).read_bytes() if (BEFORE / relative).is_file() else b""
    after_bytes = (AFTER / relative).read_bytes() if (AFTER / relative).is_file() else b""
    need(foreign_bytes_preserved(before_bytes, after_bytes), f"{relative} was not preserved byte-for-byte")
try:
    json.loads(text(AFTER / "hooks.json"))
except json.JSONDecodeError as err:
    BAD.append(f"after foreign hook fixture is invalid JSON: {err}")

ambiguous_before_snapshot = tree_snapshot(AMBIGUOUS_BEFORE)
ambiguous_after_snapshot = tree_snapshot(AMBIGUOUS_AFTER)
need(
    pending_bytes_preserved(ambiguous_before_snapshot, ambiguous_after_snapshot),
    "ambiguous/partial pending state was not preserved byte-for-byte",
)
ambiguous_charter = text(AMBIGUOUS_AFTER / "team-charter.md")
ambiguous_roles = [
    text(path) for path in sorted((AMBIGUOUS_AFTER / "agents").glob("qtim-devops*.toml"))
]
need(
    pending_state_held(ambiguous_charter, ambiguous_roles),
    "ambiguous/partial custom-role fixture did not hold charter and all qtim stamps at 2.12.0",
)

language_before_role = text(LANGUAGE_BEFORE / ".codex/agents/qtim-devops.toml")
language_after_role = text(LANGUAGE_AFTER / ".codex/agents/qtim-devops.toml")
need(language_before_role.startswith("# qtim-version: 2.13.0"), "2.14 before role stamp mismatch")
need(language_after_role.startswith("# qtim-version: 2.14.0"), "2.14 after role stamp mismatch")
need(language_after_role.count(LANGUAGE_CONTRACT) == 1, "2.14 custom role language block missing or duplicated")
normalized_language_role = language_after_role.replace(
    "# qtim-version: 2.14.0", "# qtim-version: 2.13.0", 1
).replace(f"\n\n{LANGUAGE_CONTRACT}\n", "", 1)
need(
    normalized_language_role == language_before_role,
    "2.14 custom role changed outside stamp and exact additive language block",
)

language_before_charter = text(LANGUAGE_BEFORE / ".codex/team-charter.md")
language_after_charter = text(LANGUAGE_AFTER / ".codex/team-charter.md")
need(language_after_charter.count(LANGUAGE_CONTRACT) == 1, "2.14 charter language block missing or duplicated")
normalized_language_charter = language_after_charter.replace(
    "<!-- qtim-version: 2.14.0 -->", "<!-- qtim-version: 2.13.0 -->", 1
).replace(f"\n{LANGUAGE_CONTRACT}\n", "", 1)
need(
    normalized_language_charter == language_before_charter,
    "2.14 charter changed outside stamp and exact additive language block",
)
need(
    track_block(language_before_charter, "dev") == track_block(language_after_charter, "dev"),
    "2.14 language migration changed dev track",
)

language_before_agents = text(LANGUAGE_BEFORE / "AGENTS.md")
language_after_agents = text(LANGUAGE_AFTER / "AGENTS.md")
need(language_after_agents.count(LANGUAGE_CONTRACT) == 1, "2.14 AGENTS language block missing or duplicated")
need(
    language_after_agents.replace(f"\n\n{LANGUAGE_CONTRACT}\n", "\n", 1)
    == language_before_agents,
    "2.14 AGENTS migration changed bytes outside the managed language insertion",
)
need(
    text(LANGUAGE_BEFORE / ".codex/agents/foreign-agent.toml")
    == text(LANGUAGE_AFTER / ".codex/agents/foreign-agent.toml"),
    "2.14 migration changed foreign agent bytes",
)

feature_before_charter = text(FEATURE_BEFORE / ".codex/team-charter.md")
feature_after_charter = text(FEATURE_AFTER / ".codex/team-charter.md")
feature_before_product = text(FEATURE_BEFORE / ".codex/agents/product.toml")
feature_after_product = text(FEATURE_AFTER / ".codex/agents/product.toml")
need(
    feature_charter_preserved(feature_before_charter, feature_after_charter),
    "experimental charter changed outside stamp, reviewer row and feature workflow",
)
need(
    track_block(feature_before_charter, "dev") is None
    and track_block(feature_after_charter, "dev") is None,
    "PM-only migration invented a dev track",
)
need(
    not (FEATURE_BEFORE / ".codex/agents/reviewer.toml").exists(),
    "experimental control fixture already had a reviewer",
)
need(
    feature_product_preserved(feature_before_product, feature_after_product),
    "experimental product changed outside stamp and feature workflow",
)
feature_product_policy = parse_role(feature_after_product)
need(
    (feature_product_policy.get("model"), feature_product_policy.get("model_reasoning_effort"))
    == ("gpt-6-astra", "high"),
    "experimental migration lost the product's atomic user model override",
)
feature_reviewer = text(FEATURE_AFTER / ".codex/agents/reviewer.toml")
feature_reviewer_policy = parse_role(feature_reviewer)
need(feature_reviewer.startswith(f"# qtim-version: {FEATURE_VERSION}"), "experimental reviewer stamp mismatch")
need(
    (feature_reviewer_policy.get("name"), feature_reviewer_policy.get("model"),
     feature_reviewer_policy.get("model_reasoning_effort"), feature_reviewer_policy.get("sandbox_mode"))
    == ("qtim-reviewer", "gpt-6-astra", "xhigh", "read-only"),
    "experimental PM reviewer lacks the atomic default policy or mechanical read-only sandbox",
)
for marker in ("SPEC_REVIEW", "READY_FOR_APPROVAL", "CHANGES_REQUESTED", "Reviewed revision", "Approved revision"):
    need(marker in feature_reviewer, f"experimental reviewer missing {marker}")
need(
    re.search(r"^code-review: disabled$", feature_after_charter, re.MULTILINE) is not None
    and "SPEC_REVIEW remains mandatory when code-review: disabled" in feature_after_charter,
    "experimental spec review was disabled with the optional code review gate",
)
for relative in (".codex/agents/foreign-agent.toml", "docs/features/legacy/prd.md"):
    need(
        foreign_bytes_preserved(text(FEATURE_BEFORE / relative), text(FEATURE_AFTER / relative)),
        f"experimental migration changed foreign or legacy bytes: {relative}",
    )
feature_before_tree = tree_snapshot(FEATURE_BEFORE)
feature_after_tree = tree_snapshot(FEATURE_AFTER)
need(
    set(feature_after_tree) - set(feature_before_tree) == {".codex/agents/reviewer.toml"}
    and set(feature_before_tree) <= set(feature_after_tree),
    "experimental fixture deleted existing files or added unrelated state",
)

contract_markers = {
    ROOT / "plugins/qtim/skills/qtim-update/SKILL.md": (
        "qtim-generated custom role без bundled template",
        "code-writing role получает только явно описанный",
        "Foreign custom agents не меняй",
        "stamps **всех** однозначно сопоставленных qtim role TOML",
    ),
    ROOT / "plugins/qtim/reference/upgrade-notes.md": (
        "одна charter row",
        "единственный multiline `developer_instructions`",
        "одну минимальную breaking check без новой",
        "charter и все qtim role stamps остаются `2.12.0`",
    ),
    ROOT / "plugins/qtim/skills/qtim-doctor/SKILL.md": (
        "PM-only roster без reviewer/testing не является drift",
        "qtim-generated custom role без bundled template",
        "не считай foreign agent qtim-owned",
    ),
    ROOT / "plugins/qtim/skills/qtim-setup/SKILL.md": (
        "Каждая custom role без bundled template независимо от responsibility получает",
        "дословный `## Language` contract",
    ),
    ROOT / "plugins/qtim/reference/upgrade-notes.md": (
        "## 2.14.0",
        "Миграция с 2.13.0",
        "foreign/ambiguous file не меняй",
        "stamps всех сопоставленных qtim role TOML до `2.14.0`",
    ),
}
for path, markers in contract_markers.items():
    body = text(path)
    for marker in markers:
        need(marker in body, f"{path.relative_to(ROOT)} missing migration marker `{marker}`")

if "--self-test" in sys.argv[1:]:
    need(
        not feature_product_preserved(feature_before_product, feature_after_product.replace(
            'model_reasoning_effort = "high"', 'model_reasoning_effort = "xhigh"', 1
        )),
        "negative oracle accepted experimental product model-override loss",
    )
    need(
        not feature_charter_preserved(feature_before_charter, feature_after_charter.replace(
            "MANUAL-PM-FEATURE: preserve byte-for-byte.", "MANUAL-PM-FEATURE: changed.", 1
        )),
        "negative oracle accepted experimental manual PM text loss",
    )
    need(
        not feature_charter_preserved(feature_before_charter, feature_after_charter.replace(
            "SPEC_REVIEW remains mandatory when code-review: disabled; this setting controls code review only.\n", "", 1
        )),
        "negative oracle accepted experimental code-review toggle disabling spec review",
    )
    manual_loss = after_role_text.replace(
        "Change deployment and CI code only inside the approved scope.\n",
        "",
        1,
    )
    need(
        not custom_role_preserved(before_role_text, manual_loss),
        "negative oracle accepted deleted manual custom-role instruction",
    )
    changed_manual = after_role_text.replace(
        "MANUAL-ROLE-TEXT: preserve byte-for-byte.",
        "MANUAL-ROLE-TEXT: silently changed.",
        1,
    )
    need(
        not custom_role_preserved(before_role_text, changed_manual),
        "negative oracle accepted changed manual custom-role instruction",
    )
    before_near_miss = text(BEFORE / "agents/qtim-foreign-near-miss.toml")
    after_near_miss = text(AFTER / "agents/qtim-foreign-near-miss.toml")
    mutated_near_miss = after_near_miss.replace(
        "FOREIGN-QTIM-LOOKING-BYTES-MUST-NOT-CHANGE",
        "mutated",
        1,
    )
    need(before_near_miss == after_near_miss, "near-miss control fixture is not identical")
    need(
        not foreign_bytes_preserved(
            before_near_miss.encode("utf-8"),
            mutated_near_miss.encode("utf-8"),
        ),
        "negative oracle accepted mutation of qtim-looking foreign near-miss",
    )
    advanced_charter = ambiguous_charter.replace(
        "<!-- qtim-version: 2.12.0 -->",
        "<!-- qtim-version: 2.13.0 -->",
        1,
    )
    advanced_role = ambiguous_roles[0].replace(
        "# qtim-version: 2.12.0",
        "# qtim-version: 2.13.0",
        1,
    )
    need(
        not pending_state_held(advanced_charter, ambiguous_roles),
        "negative oracle accepted target charter stamp for ambiguous custom role",
    )
    need(
        not pending_state_held(ambiguous_charter, [advanced_role, *ambiguous_roles[1:]]),
        "negative oracle accepted target role stamp for partial custom region",
    )
    mutated_pending_role = dict(ambiguous_after_snapshot)
    pending_role_key = "agents/qtim-devops.toml"
    mutated_pending_role[pending_role_key] = mutated_pending_role[pending_role_key].replace(
        b"MANUAL-PARTIAL-TEXT: preserve pending state.",
        b"MANUAL-PARTIAL-TEXT: silently changed.",
        1,
    )
    need(
        mutated_pending_role[pending_role_key]
        != ambiguous_after_snapshot[pending_role_key],
        "ambiguous role mutation self-test did not alter its control bytes",
    )
    need(
        not pending_bytes_preserved(ambiguous_before_snapshot, mutated_pending_role),
        "negative oracle accepted ambiguous role manual-byte mutation",
    )
    mutated_pending_charter = dict(ambiguous_after_snapshot)
    pending_charter_key = "team-charter.md"
    mutated_pending_charter[pending_charter_key] = mutated_pending_charter[
        pending_charter_key
    ].replace(
        b"AMBIGUOUS-DEV-TRACK: no mutation before owner decision",
        b"AMBIGUOUS-DEV-TRACK: silently changed",
        1,
    )
    need(
        mutated_pending_charter[pending_charter_key]
        != ambiguous_after_snapshot[pending_charter_key],
        "ambiguous charter mutation self-test did not alter its control bytes",
    )
    need(
        not pending_bytes_preserved(ambiguous_before_snapshot, mutated_pending_charter),
        "negative oracle accepted ambiguous charter manual-byte mutation",
    )
    mutated_language_role = language_after_role.replace(
        "MANUAL-LANGUAGE-FIXTURE: preserve byte-for-byte.",
        "MANUAL-LANGUAGE-FIXTURE: silently changed.",
        1,
    )
    normalized_mutated_language_role = mutated_language_role.replace(
        "# qtim-version: 2.14.0", "# qtim-version: 2.13.0", 1
    ).replace(f"\n\n{LANGUAGE_CONTRACT}\n", "", 1)
    need(
        normalized_mutated_language_role != language_before_role,
        "negative oracle accepted 2.14 custom-role manual-byte mutation",
    )
    partial_language_role = language_after_role.replace(
        "Keep **user-facing output in Russian**",
        "Keep user-facing output in Russian",
        1,
    )
    need(
        partial_language_role.count(LANGUAGE_CONTRACT) == 0,
        "negative oracle accepted partial 2.14 language contract",
    )

if BAD:
    print("Extended update fixture validation failed:\n- " + "\n- ".join(BAD))
    sys.exit(1)
if "--self-test" in sys.argv[1:]:
    print("OK: update-fixture negative oracles reject manual loss, foreign mutation, model-override loss, disabled spec review, partial language, and ambiguous stamp drift")
else:
    print("OK: 2.13/2.14 and experimental feature fixtures preserve non-target, legacy and foreign bytes (documented snapshots; no live migration executed)")
