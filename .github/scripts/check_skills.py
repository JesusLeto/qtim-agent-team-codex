#!/usr/bin/env python3
"""Frontmatter каждого SKILL.md валиден и совместим с plugin ingestion.

Использует PyYAML, если он установлен; иначе — консервативный fallback-парсер,
который ловит главный класс ошибок: незакавыченный скаляр с `: ` внутри
(ровно то, что роняет ingestion-валидатор Codex). Авторитетная проверка —
validate_plugin.py из Codex plugin-creator.
"""
import pathlib
import re
import sys

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
METADATA_REQUIRED = {
    "qtim-brainstorm",
    "qtim-debug-loop",
    "qtim-grill",
    "qtim-minimal-diff",
    "qtim-mission",
    "qtim-prototype",
}
THIRD_PARTY_SOURCES = {
    "qtim-debug-loop": "mattpocock/skills",
    "qtim-grill": "mattpocock/skills",
    "qtim-prototype": "mattpocock/skills",
    "qtim-minimal-diff": "DietrichGebert/ponytail",
}
INTERFACE_FIELDS = {"display_name", "short_description", "default_prompt"}

bad = []


def parse_fallback(path, body):
    """Строгое подмножество YAML: однострочные `key: value`, plain или в кавычках."""
    data = {}
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = KEY_RE.match(line)
        if m is None:
            bad.append(f"{path}: строка не является простой парой key: value: `{line}`")
            continue
        key, value = m.group(1), m.group(2).strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                bad.append(f"{path}: незакрытая кавычка в `{key}`")
                continue
            value = value[1:-1]
        elif ": " in value or value.endswith(":"):
            bad.append(
                f"{path}: `{key}` содержит `: ` в незакавыченном значении — "
                "невалидный YAML для ingestion, возьми значение в кавычки"
            )
            continue
        data[key] = value
    return data


def validate_openai_metadata(skill_dir):
    """Validate the narrow agents/openai.yaml shape used by qtim skills without PyYAML."""
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        if skill_dir.name in METADATA_REQUIRED:
            bad.append(f"{path}: metadata обязателен для bundled discipline")
        return

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0] != "interface:":
        bad.append(f"{path}: ожидается корень `interface:`")
        return

    values = {}
    policy = {}
    section = None
    for line in lines:
        if not line.startswith(" "):
            if line not in {"interface:", "policy:"}:
                bad.append(f"{path}: неизвестная корневая секция `{line}`")
                section = None
            else:
                section = line[:-1]
            continue
        if section == "interface":
            match = re.fullmatch(r'  ([a-z_]+):\s*"([^"]*)"', line)
            if match is None:
                bad.append(f"{path}: невалидная или некавыченная interface-строка `{line}`")
                continue
            key, value = match.groups()
            if key not in INTERFACE_FIELDS:
                bad.append(f"{path}: неизвестное interface-поле `{key}`")
                continue
            values[key] = value
        elif section == "policy":
            match = re.fullmatch(r"  (allow_implicit_invocation):\s*(true|false)", line)
            if match is None:
                bad.append(f"{path}: невалидная policy-строка `{line}`")
                continue
            key, value = match.groups()
            policy[key] = value == "true"
        else:
            bad.append(f"{path}: поле вне известной секции `{line}`")

    missing = sorted(INTERFACE_FIELDS - values.keys())
    if missing:
        bad.append(f"{path}: отсутствуют поля: {', '.join(missing)}")
        return
    if not values["display_name"].strip():
        bad.append(f"{path}: `display_name` должен быть непустым")
    length = len(values["short_description"])
    if not 25 <= length <= 64:
        bad.append(f"{path}: `short_description` должен быть длиной 25-64, сейчас {length}")
    if f"${skill_dir.name}" not in values["default_prompt"]:
        bad.append(f"{path}: `default_prompt` должен явно упоминать `${skill_dir.name}`")
    if skill_dir.name == "qtim-mission" and policy.get("allow_implicit_invocation") is not True:
        bad.append(
            f"{path}: qtim-mission должен разрешать implicit loading для "
            "fail-closed activation gate"
        )


for skill_dir in sorted(pathlib.Path("plugins").glob("*/skills/*")):
    if not skill_dir.is_dir() or skill_dir.name.startswith("."):
        continue
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        bad.append(f"{skill_dir}: нет SKILL.md")
        continue
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        bad.append(f"{path}: должен начинаться с YAML frontmatter")
        continue
    end = text.find("\n---", 4)
    if end == -1:
        bad.append(f"{path}: frontmatter не закрыт")
        continue
    body = text[4:end]
    if yaml is not None:
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError as err:
            bad.append(f"{path}: невалидный YAML frontmatter: {err}")
            continue
        if not isinstance(data, dict):
            bad.append(f"{path}: frontmatter должен быть YAML-объектом")
            continue
    else:
        data = parse_fallback(path, body)
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        bad.append(f"{path}: `name` должен быть непустой строкой")
    elif name != skill_dir.name:
        bad.append(f"{path}: `name` ({name}) не совпадает с директорией ({skill_dir.name})")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        bad.append(f"{path}: `description` должен быть непустой строкой")
    source = THIRD_PARTY_SOURCES.get(skill_dir.name)
    if source and (source not in text or "MIT" not in text):
        bad.append(
            f"{path}: нет attribution `{source}` и MIT marker для adapted discipline"
        )
    validate_openai_metadata(skill_dir)

feature_spec_consumers = [
    pathlib.Path("plugins/qtim/skills/qtim-feature/SKILL.md"),
    pathlib.Path("plugins/qtim/reference/feature-pipeline.md"),
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-team-up/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-team-lazy/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-team-retro/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"),
]
for path in feature_spec_consumers:
    if not path.is_file() or "spec.md" not in path.read_text(encoding="utf-8"):
        bad.append(f"{path}: нет поддержки канонической спецификации `spec.md`")

spec_revision_consumers = [
    pathlib.Path("plugins/qtim/skills/qtim-feature/SKILL.md"),
    pathlib.Path("plugins/qtim/reference/feature-pipeline.md"),
    pathlib.Path("plugins/qtim/agents/reviewer.toml"),
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"),
    pathlib.Path("plugins/qtim/reference/upgrade-notes.md"),
]
for path in spec_revision_consumers:
    body = path.read_text(encoding="utf-8") if path.is_file() else ""
    missing = [marker for marker in ("SPEC_REVIEW", "Reviewed revision", "Approved revision") if marker not in body]
    if missing:
        bad.append(f"{path}: неполный контракт независимого ревью спецификации: {', '.join(missing)}")

vertical_slice_consumers = [
    pathlib.Path("plugins/qtim/reference/feature-pipeline.md"),
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"),
    pathlib.Path("plugins/qtim/agents/product.toml"),
    pathlib.Path("plugins/qtim/reference/upgrade-notes.md"),
]
for path in vertical_slice_consumers:
    body = path.read_text(encoding="utf-8") if path.is_file() else ""
    for marker in ("DRI", "contributing"):
        if marker.lower() not in body.lower():
            bad.append(f"{path}: vertical slicing не фиксирует `{marker}`")

risk_policy_consumers = [
    pathlib.Path("plugins/qtim/reference/independent-review.md"),
    pathlib.Path("plugins/qtim/reference/orchestration-patterns.md"),
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"),
    pathlib.Path("plugins/qtim/agents/reviewer.toml"),
    pathlib.Path("plugins/qtim/reference/upgrade-notes.md"),
]
risk_markers = (
    "security/auth",
    "money/billing/account state",
    "documented domain invariants",
    "public contracts",
    "data-transform",
    "destructive migrations",
    "critical browser flows",
    "high-risk performance/reliability",
    "hard-to-rollback",
)
for path in risk_policy_consumers:
    body = path.read_text(encoding="utf-8") if path.is_file() else ""
    missing = [marker for marker in risk_markers if marker not in body]
    if missing:
        bad.append(f"{path}: incomplete canonical risk matrix: {', '.join(missing)}")

status_contracts = {
    pathlib.Path("plugins/qtim/reference/feature-pipeline.md"): (
        "In Development", "Done", "gates",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-team-up/SKILL.md"): (
        "In Development", "Done", "gates",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-team-lazy/SKILL.md"): (
        "In Development", "Done", "gates",
    ),
}
for path, markers in status_contracts.items():
    body = path.read_text(encoding="utf-8") if path.is_file() else ""
    missing = [marker for marker in markers if marker not in body]
    if missing:
        bad.append(f"{path}: повреждён scoped status transition: {', '.join(missing)}")

update_skill = pathlib.Path("plugins/qtim/skills/qtim-update/SKILL.md").read_text(encoding="utf-8")
upgrade_notes = pathlib.Path("plugins/qtim/reference/upgrade-notes.md").read_text(encoding="utf-8")
for marker in ("oldest -> newest", "pending"):
    if marker not in update_skill or marker not in upgrade_notes:
        bad.append(f"qtim update contract не фиксирует `{marker}` в skill и upgrade notes")

if "После миграции обнови оба stamp (charter и TOML) на текущую версию плагина" in upgrade_notes:
    bad.append("upgrade notes содержат legacy target-stamp rule, конфликтующий с incremental pending migration")
if "После каждой полностью завершённой version-section" not in upgrade_notes:
    bad.append("upgrade notes не фиксируют общий incremental stamp contract")

atomic_migration_markers = (
    "Мигрируй перечисленные ниже **regions независимо**",
    "target markers делают `applied` только свой region, а не всю роль",
    "architect / ADR filter",
    "product / ownership",
    "product / vertical slice",
    "product / expand-contract",
    "product / estimation",
    "наличие ровно одного target marker означает partial region",
)
missing = [marker for marker in atomic_migration_markers if marker not in upgrade_notes]
if missing:
    bad.append(f"upgrade notes не защищают atomic 2.9 agent migration: {', '.join(missing)}")

minimal_diff_contracts = {
    pathlib.Path("plugins/qtim/skills/qtim-minimal-diff/SKILL.md"): (
        "Пройди семь ступеней",
        "Сохрани защищённые обязательства",
        "minimal-diff: <потолок> — <проверяемый триггер и действие>",
        "Добавь одну минимальную breaking-проверку",
        "$qtim-brainstorm",
        "$qtim-prototype",
    ),
    pathlib.Path("plugins/qtim/agents/architect.toml"): (
        "$qtim-minimal-diff",
        "Новый слой и новая зависимость — архитектурное решение",
        "Чистая избыточность — рекомендация",
    ),
    pathlib.Path("plugins/qtim/agents/database.toml"): (
        "$qtim-minimal-diff",
        "constraint, index или trigger",
        "обязательная минимальная проверка",
    ),
    pathlib.Path("plugins/qtim/agents/frontend.toml"): (
        "$qtim-minimal-diff",
        "Trust-boundary validation",
        "одну минимальную проверку",
    ),
    pathlib.Path("plugins/qtim/agents/reviewer.toml"): (
        "Minimal-diff review (recommendations, not automatic blockers)",
        "$qtim-minimal-diff",
        "pure excess",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md"): (
        "$qtim-minimal-diff",
        "Re-run остаётся additive",
        "не удаляй роли",
        "code-writing custom role",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-update/SKILL.md"): (
        'TOML `name = "qtim-..."`',
        "Foreign custom agents",
        "частично совпавшая target",
        "qtim-generated custom role без bundled template",
    ),
    pathlib.Path("plugins/qtim/reference/upgrade-notes.md"): (
        "## 2.13.0",
        "Миграция с 2.12.0",
        "regions независимо",
        "stamps остаются `2.12.0`",
        "единственный multiline `developer_instructions`",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-doctor/SKILL.md"): (
        "Roster ↔ repository responsibilities",
        "responsibility gap",
        "Roster drift всегда `warn`",
        "PM-only roster без reviewer/testing не является drift",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-team-retro/SKILL.md"): (
        "triggered",
        "not triggered",
        "protected violation",
        "source + exact marker",
    ),
    pathlib.Path("plugins/qtim/skills/qtim-debug-loop/SKILL.md"): (
        "root seam",
        "coverage gaps",
        "$qtim-minimal-diff",
    ),
}
for path, markers in minimal_diff_contracts.items():
    body = path.read_text(encoding="utf-8") if path.is_file() else ""
    missing = [marker for marker in markers if marker not in body]
    if missing:
        bad.append(f"{path}: incomplete minimal-diff contract: {', '.join(missing)}")

maintainer_rules = pathlib.Path("AGENTS.md").read_text(encoding="utf-8")
for marker in (
    "Bundled disciplines are role-agnostic practices, not orchestration engines",
    "audit role templates for compensating step-by-step recipes",
    "preserve structural invariants, risk-based gates, durable memory, and verification contracts",
):
    if marker not in maintainer_rules:
        bad.append(f"AGENTS.md не фиксирует frontier-maintenance rule: {marker}")

claude_skill_call = re.compile(
    r"(?<![A-Za-z0-9_-])qtim:(debug-loop|prototype|brainstorm|grill|minimal-diff)\b"
)
for path in pathlib.Path("plugins/qtim").rglob("*.md"):
    if claude_skill_call.search(path.read_text(encoding="utf-8")):
        bad.append(f"{path}: Claude-вызов qtim:<skill>; в Codex используй `$qtim-<skill>`")

notice_path = pathlib.Path("plugins/qtim/THIRD_PARTY_NOTICES.md")
notice = notice_path.read_text(encoding="utf-8") if notice_path.is_file() else ""
if "Copyright (c) 2026 Matt Pocock" not in notice or "Permission is hereby granted" not in notice:
    bad.append(f"{notice_path}: нет полного MIT notice источника bundled disciplines")
if (
    "Copyright (c) 2026 DietrichGebert" not in notice
    or "DietrichGebert/ponytail" not in notice
    or notice.count("Permission is hereby granted") < 2
):
    bad.append(f"{notice_path}: нет полного MIT notice DietrichGebert/ponytail")

if bad:
    print("Skill frontmatter validation failed:")
    print("\n".join(bad))
    sys.exit(1)

mode = "PyYAML" if yaml is not None else "fallback-парсер (PyYAML не установлен)"
print(f"OK: frontmatter всех SKILL.md валиден ({mode})")
