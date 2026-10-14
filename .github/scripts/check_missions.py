#!/usr/bin/env python3
"""Semantic golden checks for the complete qtim cross-dialog mission contract."""

from __future__ import annotations

import json
import hashlib
import os
import pathlib
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata


ROOT = pathlib.Path(__file__).resolve().parents[2]
FILESYSTEM_SNAPSHOT_MAX_ENTRIES = 50_000
FILESYSTEM_SNAPSHOT_MAX_BYTES = 512 * 1024 * 1024
MISSION_REGISTRY_MAX_BYTES = 1024 * 1024


def is_filesystem_junction(path: pathlib.Path) -> bool:
    path = pathlib.Path(path)
    return bool(
        getattr(os.path, "isjunction", lambda _path: False)(path)
        or getattr(path, "is_junction", lambda: False)()
    )


def fail(message: str) -> None:
    print(f"Mission validation failed: {message}")
    raise SystemExit(1)


def read(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        fail(f"missing required mission file: {path}")
    return target.read_text(encoding="utf-8")


def require(path: str, *markers: str) -> None:
    body = read(path)
    missing = [marker for marker in markers if marker not in body]
    if missing:
        fail(f"{path}: missing markers: {', '.join(missing)}")


def require_order(path: str, *markers: str) -> None:
    body = read(path)
    cursor = -1
    for marker in markers:
        position = body.find(marker, cursor + 1)
        if position < 0:
            fail(f"{path}: missing or out-of-order marker: {marker}")
        cursor = position


def activation_mode(
    prompt: str,
    approved: bool,
    preflight_ok: bool,
    *,
    approved_preview_in_context: bool = False,
    feature_recommendation_in_context: bool = False,
) -> str:
    """Small golden classifier; the skill remains the runtime contract."""
    normalized = " ".join(prompt.lower().split())
    explicit_skill = "$qtim-mission" in normalized
    imperative_execution_verb = (
        r"(?:запусти|запускай|создай|создавай|начни|начинай|"
        r"реализуй|реализовывай|выполни|выполняй|проведи|проводи|организуй)"
    )
    execution_verb = (
        r"(?:запусти|запускай|запускать|создай|создавай|создавать|"
        r"начни|начинай|начать|реализуй|реализовывай|реализовать|"
        r"выполни|выполняй|выполнить|проведи|проводи|проводить|провести|"
        r"организуй|организовать)"
    )
    explicit_execution = bool(
        re.search(
            rf"^(?:пожалуйста[,\s]+)?(?:"
            rf"\$qtim-mission[\s,:—-]+\b{imperative_execution_verb}\b|"
            rf"\b{imperative_execution_verb}\b.{{0,40}}\$qtim-mission\b)",
            normalized,
        )
    )
    multi_peer_shape = bool(
        re.search(
            r"(?:\bнесколько\b.{0,60}\b(?:задач|диалогов)\b|"
            r"\b(?:две|три)\b.{0,60}\bзадачи\b|"
            r"\b(?:два|три)\b.{0,60}\bдиалога\b|"
            r"\bотдельн(?:ые|ых|ыми)\b.{0,80}"
            r"\b(?:задачи|задач|задачами|диалоги|диалогов|диалогами)\b)",
            normalized,
        )
    )
    mission_coordination = bool(
        re.search(r"\b(qtim[- ]?мисси\w*|мисси\w*)\b", normalized)
    )
    direct_peer_request = bool(
        re.search(rf"\b{imperative_execution_verb}\b", normalized)
        and multi_peer_shape
        and mission_coordination
    )
    negated = bool(
        re.search(
            rf"\b(не|нельзя)(?:\s+\w+){{0,3}}\s+{execution_verb}\b",
            normalized,
        )
        or re.search(
            r"\b(не хочу|не нужно|не надо|не стоит|без запуска|"
            r"воздержись|отмени|исключи)\b",
            normalized,
        )
        or re.search(r"\bбез\s+создания\s+(задач|диалогов)\b", normalized)
        or re.search(
            r"\bзапрещаю\s+(запускать|запуск|создавать|создание)\b",
            normalized,
        )
        or re.search(r"\b(кроме|за исключением)\s+\$qtim-mission\b", normalized)
        or re.search(
            r"\b(?:кроме|за\s+исключением|исключая)\s+"
            r"(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
        or re.search(
            r"\b(?:запрещено|запрещены|запрещён\w*|запрещается)\b",
            normalized,
        )
        or re.search(
            r"\bбез(?:\s+\w+){0,3}\s+(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
        or re.search(
            r"\bне(?:\s+\w+){0,4}\s+(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
        or re.search(
            r"\b(?:qtim[- ]?)?мисси\w*\b.{0,50}\b(?:не|без|исключая)\b",
            normalized,
        )
        or re.search(
            r"\b(?:это|данн\w+|эт\w+\s+(?:работа|задача|запрос))?\s*"
            r"не\s+(?:одна\s+)?(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
        or re.search(
            r"\bне\s+(?:проводи|проводить|проведи|организуй|организовывай)"
            r".{0,60}\b(?:как|в\s+виде)\s+(?:одн\w+\s+)?"
            r"(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
        or re.search(
            r"\bне\s+(?:как|в\s+виде)\s+(?:одн\w+\s+)?"
            r"(?:qtim[- ]?)?мисси\w*\b",
            normalized,
        )
    )
    quoted_span = any(
        character in "\"'`~＂＇〝〞"
        or unicodedata.category(character) in {"Pi", "Pf"}
        for character in normalized
    )
    quoted_or_question = (
        normalized.startswith(
            (
                "что такое", "как работает", "как создать", "как запустить",
                "можно ли", "стоит ли", "нужно ли", "следует ли", "почему",
                "зачем", "где", "когда", "какой", "какая", "какие",
                "объясни", "расскажи",
            )
        )
        or bool(re.search(r"\b(пример|цитата|документаци\w*|упомянут\w*)\b", normalized))
        or "?" in normalized
        or "？" in normalized
        or quoted_span
    )
    planning_request = bool(
        re.search(
            r"\b(preview|превью|покажи\s+(план|граф|preview)|"
            r"только\s+спланируй|спланируй|создай\s+план|"
            r"составь\s+план|подготовь\s+(?:план|оценку|анализ)|"
            r"предложи\s+(?:план|подход)|набросай\s+план|"
            r"(?:сделай|дай)\s+оценку|опиши(?:\s*,?\s+как)?|"
            r"(?:мне\s+)?нужно\s+понять|хочу\s+(?:узнать|понять)|"
            r"только\s+(?:план|планирование|оценка|анализ)|"
            r"оцени|проанализируй)\b",
            normalized,
        )
    )
    preview_request = explicit_skill and planning_request
    deferred = bool(
        re.search(r"\b(?:если|когда)\b", normalized)
        or re.search(
            r"\b(после следующего подтверждения|после подтверждения|"
            r"когда подтверд\w*|если подтверд\w*|по завершении|по готовности|"
            r"по окончании|после окончания|после того как|как только|"
            r"на следующей неделе|"
            r"в следующем месяце|при условии|в случае если|"
            r"потом|позже|в будущем|отложи|отложен\w*|дождись)\b",
            normalized,
        )
        or re.search(
            r"\bпосле\s+(?:релиза|деплоя|мержа|ревью|проверки|"
            r"тестов?|сборки|публикации|завершения|готовности|"
            r"согласования|апрува|ответа)\b",
            normalized,
        )
        or re.search(
            r"\b(не сейчас|не сегодня|пока не|не раньше|"
            r"завтра|послезавтра|когда-нибудь)\b",
            normalized,
        )
        or re.search(
            r"\b(?:только|лишь)\s+после\s+(?:моего|нашего|отдельного)\s+"
            r"(?:сигнала|разрешения|подтверждения)\b",
            normalized,
        )
        or re.search(
            r"\bчерез\s+(?:"
            r"(?:(?:\d+|один|одну|два|две|три|пару|несколько|полтора|полторы)"
            r"(?:\s+с\s+половиной)?\s+)?"
            r"(?:сек(?:унд\w*)?|мин(?:ут\w*)?|час\w*|дн\w*|недел\w*|"
            r"месяц\w*|год\w*|сутк\w*|seconds?|minutes?|hours?)|"
            r"пол(?:секунды|минуты|часа|дня|недели|месяца|года)|"
            r"(?:некоторое|какое(?:-|\s)то)\s+время)\b",
            normalized,
        )
        or re.search(
            r"\b(?:через|спустя)\s+(?:четверть|три\s+четверти)\s+"
            r"(?:час\w*|дн\w*|недел\w*|месяц\w*|год\w*)\b",
            normalized,
        )
        or re.search(
            r"\b(?:сегодня\s+)?(?:утром|днём|днем|вечером|ночью)\b|"
            r"\b(?:в|во)\s+(?:понедельник|вторник|среду|четверг|пятницу|"
            r"субботу|воскресенье)\b|"
            r"\b(?:на\s+выходных|в\s+конце\s+(?:дня|недели|месяца|года))\b|"
            r"\bв\s+\d{1,2}:\d{2}\b|"
            r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
            normalized,
        )
        or bool(
            re.match(
                r"^(?:я\s+)?(?:планирую|собираюсь|буду|намерен\w*)\b",
                normalized,
            )
        )
    )
    referential_approval = (
        approved_preview_in_context
        and normalized
        in {
            "запускай предложенное",
            "запусти предложенное",
            "да, запускай предложенное",
        }
    )
    feature_handoff_approval = (
        feature_recommendation_in_context
        and normalized
        in {
            "запускай предложенное",
            "запусти предложенное",
            "да, запускай предложенное",
        }
    )

    if quoted_or_question:
        return "NOOP"
    if preview_request:
        return "PREVIEW"
    if negated or deferred:
        return "NOOP"
    if feature_handoff_approval:
        return "PREVIEW"
    if planning_request:
        return "PREVIEW" if explicit_skill or (multi_peer_shape and mission_coordination) else "NOOP"
    approved_source_reference = bool(
        approved
        and re.search(r"\b(?:approved|утвержд\w*|одобрен\w*)\b", normalized)
    )
    explicit_approved_execution = bool(
        explicit_execution and (approved_source_reference or multi_peer_shape)
    )
    if not (
        referential_approval
        or explicit_approved_execution
        or direct_peer_request
    ):
        if explicit_skill:
            return "PREVIEW"
        return "RECOMMEND" if "mission" in normalized else "NOOP"
    return "AUTO-START" if approved and preflight_ok else "PREVIEW"


def recommend_workflow(
    outcomes: int,
    feedback_loop: bool,
    isolated_contexts: bool,
    dependency_edges: int,
    point_roles: bool,
) -> str:
    """Shape-based routing golden; size intentionally is not an argument."""
    if outcomes >= 2 or dependency_edges > 0 or isolated_contexts:
        return "$qtim-mission"
    if feedback_loop:
        return "$qtim-team-up"
    if point_roles:
        return "$qtim-team-lazy"
    return "direct"


def canonical_mission_identifier(raw_identifier: object) -> bool:
    return bool(
        isinstance(raw_identifier, str)
        and len(raw_identifier) <= 64
        and re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?",
            raw_identifier,
        )
    )


def canonical_git_ref(raw_ref: object) -> bool:
    if not isinstance(raw_ref, str) or not raw_ref.startswith("refs/"):
        return False
    return (
        subprocess.run(
            ["git", "check-ref-format", raw_ref],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).returncode
        == 0
    )


def canonical_branch_ref(raw_ref: object) -> bool:
    return bool(
        isinstance(raw_ref, str)
        and raw_ref.startswith("refs/heads/")
        and canonical_git_ref(raw_ref)
    )


def mission_identity_errors(
    *,
    mission_slug: object,
    mission_id: object,
    node_ids: object,
    state_ref: object,
    integration_target_ref: object,
) -> list[str]:
    errors = []
    if not canonical_mission_identifier(mission_slug):
        errors.append("mission slug must be canonical lowercase ASCII kebab")
    if not canonical_mission_identifier(mission_id):
        errors.append("mission id must be canonical lowercase ASCII kebab")
    if (
        canonical_mission_identifier(mission_slug)
        and canonical_mission_identifier(mission_id)
        and mission_slug != mission_id
    ):
        errors.append("mission slug and mission id must match")
    if not isinstance(node_ids, list):
        errors.append("node ids must be a list")
        normalized_node_ids: list[object] = []
    else:
        normalized_node_ids = node_ids
    if any(
        not canonical_mission_identifier(node_id)
        for node_id in normalized_node_ids
    ):
        errors.append("node id must be canonical lowercase ASCII kebab")
    if len(set(map(str, normalized_node_ids))) != len(normalized_node_ids):
        errors.append("node ids must be unique")
    expected_state_ref = (
        f"refs/heads/codex/qtim-mission-state-{mission_slug}"
        if canonical_mission_identifier(mission_slug)
        else None
    )
    if (
        not canonical_branch_ref(state_ref)
        or state_ref != expected_state_ref
    ):
        errors.append("state ref must exactly derive from mission slug")
    if not canonical_branch_ref(integration_target_ref):
        errors.append("integration target must be a canonical branch ref")
    if (
        isinstance(integration_target_ref, str)
        and (
            integration_target_ref == "refs/heads/codex"
            or
            integration_target_ref.startswith(
                "refs/heads/codex/qtim-mission-state-"
            )
        )
    ):
        errors.append("integration target must not use reserved mission ref namespace")
    if (
        canonical_branch_ref(state_ref)
        and canonical_branch_ref(integration_target_ref)
        and state_ref == integration_target_ref
    ):
        errors.append("state and integration refs must differ")
    if (
        canonical_mission_identifier(mission_id)
        and all(
            canonical_mission_identifier(node_id)
            for node_id in normalized_node_ids
        )
    ):
        markers = [
            f"qtim:{mission_id}:{node_id}"
            for node_id in normalized_node_ids
        ]
        if len(set(markers)) != len(markers):
            errors.append("mission markers must be unique")
    return errors


def validate_dag(graph: dict[str, list[str]]) -> list[str]:
    if len(graph) < 2:
        raise ValueError("mission requires at least two content nodes")
    if any(not canonical_mission_identifier(node_id) for node_id in graph):
        raise ValueError("non-canonical node id")
    unknown = sorted({dep for deps in graph.values() for dep in deps if dep not in graph})
    if unknown:
        raise ValueError(f"unknown dependencies: {', '.join(unknown)}")

    temporary: set[str] = set()
    permanent: set[str] = set()
    order: list[str] = []

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            raise ValueError("cycle")
        temporary.add(node)
        for dependency in graph[node]:
            visit(dependency)
        temporary.remove(node)
        permanent.add(node)
        order.append(node)

    for node in graph:
        visit(node)
    return order


def validate_edge_contracts(
    graph: dict[str, list[str]],
    edge_contracts: dict[tuple[str, str], str],
) -> None:
    expected_edges = {
        (dependency, node)
        for node, dependencies in graph.items()
        for dependency in dependencies
    }
    if set(edge_contracts) != expected_edges:
        raise ValueError("edge contract map must exactly cover DAG dependencies")
    if any(
        contract not in {"evidence", "integrated"}
        for contract in edge_contracts.values()
    ):
        raise ValueError("unknown edge contract")


def ready_nodes(
    graph: dict[str, list[str]],
    statuses: dict[str, str],
    edge_contracts: dict[tuple[str, str], str],
) -> list[str]:
    validate_dag(graph)
    validate_edge_contracts(graph, edge_contracts)

    def dependency_ready(node: str, dependency: str) -> bool:
        required = edge_contracts[(dependency, node)]
        expected = "integrated" if required == "integrated" else "validated"
        return statuses.get(dependency) == expected

    return [
        node
        for node, dependencies in graph.items()
        if statuses.get(node) == "pending"
        and all(dependency_ready(node, dependency) for dependency in dependencies)
    ]


def terminal_verifier_ready(
    content_nodes: set[str],
    required_nodes: set[str],
    writer_nodes: set[str],
    statuses: dict[str, str],
    *,
    global_gates_green: bool,
) -> bool:
    if (
        global_gates_green is not True
        or len(content_nodes) < 2
        or required_nodes != content_nodes
        or not writer_nodes <= content_nodes
    ):
        return False
    return all(
        statuses.get(node) == ("integrated" if node in writer_nodes else "validated")
        for node in required_nodes
    )


ALLOWED_TRANSITIONS = {
    "pending": {"ready", "blocked", "cancelled"},
    "ready": {"creating", "blocked", "cancelled"},
    "creating": {"preflight-ready", "running", "blocked", "cancelled"},
    "preflight-ready": {"running", "blocked", "cancelled"},
    "running": {"needs_input", "failed", "succeeded", "cancelled"},
    "needs_input": {"running", "blocked", "cancelled"},
    "failed": {"ready", "blocked", "superseded"},
    "succeeded": {"validated", "failed"},
    "validated": {"integrated", "verified", "blocked"},
    "integrated": {"verified", "blocked"},
}


def transition_allowed(before: str, after: str) -> bool:
    return after in ALLOWED_TRANSITIONS.get(before, set())


def writer_start_outcome(
    *,
    followup_available: bool,
    no_edits: bool,
    detached_expected_base: bool,
    clean_including_untracked: bool,
    refs_unchanged: bool,
    all_wave_targets_reconciled: bool,
    coordinator_baselines_captured: bool,
    exact_authorization_matches: bool,
) -> str:
    """Model the mandatory no-edit READY handshake before writer authorization."""
    if followup_available is not True:
        return "unavailable"
    if not (
        no_edits is True
        and detached_expected_base is True
        and clean_including_untracked is True
        and refs_unchanged is True
    ):
        return "blocked"
    if not (
        all_wave_targets_reconciled is True
        and coordinator_baselines_captured is True
    ):
        return "preflight-ready"
    return "running" if exact_authorization_matches is True else "blocked"


def parse_repo_scope(raw_scope: object) -> tuple[str | None, str | None]:
    """Normalize a portable scope or return a fail-closed error class."""
    if not isinstance(raw_scope, str):
        return None, "unsafe"
    stripped_candidate = raw_scope.strip()
    surrounding_whitespace = stripped_candidate != raw_scope
    raw_candidate = unicodedata.normalize("NFC", stripped_candidate)
    unicode_noncanonical = raw_candidate != stripped_candidate
    comparable = raw_candidate.rstrip("/")
    contains_unicode_control = any(
        unicodedata.category(character).startswith("C")
        for character in raw_candidate
    )
    if (
        not comparable
        or comparable.startswith("/")
        or comparable.startswith("-")
        or "\\" in raw_candidate
        or ":" in raw_candidate
        or "$" in raw_candidate
        or "%" in raw_candidate
        or contains_unicode_control
        or re.search(r"[*?\[\]{}]", raw_candidate)
        or re.search(r"(?:^|/)[!+@]\(", raw_candidate)
        or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", comparable)
    ):
        return None, "unsafe"
    normalized_scope = posixpath.normpath(comparable)
    if (
        normalized_scope in {".", ".."}
        or normalized_scope.startswith("../")
    ):
        return None, "unsafe"
    windows_reserved = {
        "con", "prn", "aux", "nul",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
    for component in normalized_scope.split("/"):
        windows_alias = component.rstrip(" .")
        folded = windows_alias.casefold()
        reserved_base = folded.split(".", 1)[0]
        if (
            not windows_alias
            or windows_alias != component
            or component.startswith("~")
            or folded == ".git"
            or reserved_base in windows_reserved
        ):
            return None, "unsafe"
    if (
        surrounding_whitespace
        or unicode_noncanonical
        or normalized_scope != comparable
    ):
        return normalized_scope, "noncanonical"
    return normalized_scope, None


def portable_scope_key(scope: str) -> str:
    return unicodedata.normalize("NFC", scope).casefold()


def scope_contains(allowed: str, candidate: str) -> bool:
    allowed_key = portable_scope_key(allowed)
    candidate_key = portable_scope_key(candidate)
    return (
        candidate_key == allowed_key
        or candidate_key.startswith(f"{allowed_key}/")
    )


def scopes_overlap(left: str, right: str) -> bool:
    return scope_contains(left, right) or scope_contains(right, left)


def target_scope_errors(
    worktree_root: pathlib.Path,
    raw_scope: object,
) -> list[str]:
    normalized_scope, scope_error = parse_repo_scope(raw_scope)
    if scope_error is not None or normalized_scope is None:
        return ["scope must be canonical safe repo-relative path"]
    root = worktree_root.resolve()
    current = root
    for component in normalized_scope.split("/"):
        current = current / component
        if current.is_symlink() or is_filesystem_junction(current):
            return ["scope must not cross symlink or junction components"]
        if current.exists():
            resolved = current.resolve()
            try:
                if os.path.commonpath((str(root), str(resolved))) != str(root):
                    return ["scope realpath must stay inside exact worktree root"]
            except ValueError:
                return ["scope realpath must stay inside exact worktree root"]
    return []


def writer_scope_serialization_errors(
    *,
    graph: dict[str, list[str]],
    edge_contracts: dict[tuple[str, str], str],
    writer_scopes: dict[str, list[object]],
) -> list[str]:
    errors = []
    try:
        validate_dag(graph)
        validate_edge_contracts(graph, edge_contracts)
    except ValueError as error:
        return [str(error)]
    normalized_by_node: dict[str, list[str]] = {}
    for node_id, raw_scopes in writer_scopes.items():
        if node_id not in graph or not isinstance(raw_scopes, list):
            errors.append("writer scope map must reference DAG nodes with lists")
            continue
        normalized_by_node[node_id] = []
        for raw_scope in raw_scopes:
            normalized_scope, scope_error = parse_repo_scope(raw_scope)
            if scope_error is not None or normalized_scope is None:
                errors.append("writer scope map contains unsafe or noncanonical scope")
            else:
                normalized_by_node[node_id].append(normalized_scope)
    nodes = sorted(normalized_by_node)
    for index, left_node in enumerate(nodes):
        for right_node in nodes[index + 1 :]:
            overlap = any(
                scopes_overlap(left_scope, right_scope)
                for left_scope in normalized_by_node[left_node]
                for right_scope in normalized_by_node[right_node]
            )
            if not overlap:
                continue
            explicitly_integrated = (
                edge_contracts.get((left_node, right_node)) == "integrated"
                or edge_contracts.get((right_node, left_node)) == "integrated"
            )
            if not explicitly_integrated:
                errors.append(
                    "overlapping writer scopes require a direct integrated edge"
                )
    return errors


def protected_ref_snapshot_errors(
    *,
    refs_before: object,
    refs_after: object,
    authorized_updates: object,
    mission_slug: object,
    coordinator_owned_refs: object,
) -> list[str]:
    canonical_oid = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
    state_ref = (
        f"refs/heads/codex/qtim-mission-state-{mission_slug}"
        if canonical_mission_identifier(mission_slug)
        else None
    )
    if (
        state_ref is None
        or
        not isinstance(refs_before, dict)
        or not isinstance(refs_after, dict)
        or not isinstance(authorized_updates, dict)
        or not isinstance(coordinator_owned_refs, set)
        or any(
            not isinstance(ref_name, str)
            or not canonical_git_ref(ref_name)
            or ref_name != state_ref
            for ref_name in coordinator_owned_refs
        )
        or any(
            not isinstance(ref_name, str)
            or not isinstance(ref_oid, str)
            or not canonical_git_ref(ref_name)
            or not canonical_oid.fullmatch(ref_oid)
            for snapshot in (refs_before, refs_after)
            for ref_name, ref_oid in snapshot.items()
        )
    ):
        return ["protected ref snapshot proof must be canonical"]
    expected_after = dict(refs_before)
    for ref_name, transition in authorized_updates.items():
        old = transition.get("old") if isinstance(transition, dict) else object()
        new = transition.get("new") if isinstance(transition, dict) else object()
        if (
            not canonical_git_ref(ref_name)
            or ref_name not in coordinator_owned_refs
            or not isinstance(transition, dict)
            or set(transition) != {"old", "new"}
            or old is None and new is None
            or ref_name == state_ref and (old is None or new is None)
            or old is not None
            and (
                not isinstance(old, str)
                or not canonical_oid.fullmatch(old)
                or refs_before.get(ref_name) != old
            )
            or new is not None
            and (
                not isinstance(new, str)
                or not canonical_oid.fullmatch(new)
            )
            or old is None and ref_name in refs_before
        ):
            return ["coordinator-authorized ref transition must be canonical"]
        if new is None:
            expected_after.pop(ref_name)
        else:
            expected_after[ref_name] = new
    if refs_after != expected_after:
        return ["protected refs may only follow coordinator-authorized transitions"]
    return []


def worker_ref_snapshot_errors(
    *,
    refs_before: object,
    refs_after: object,
    coordinator_authorized_updates: object,
    mission_slug: object,
    coordinator_owned_refs: object,
) -> list[str]:
    return protected_ref_snapshot_errors(
        refs_before=refs_before,
        refs_after=refs_after,
        authorized_updates=coordinator_authorized_updates,
        mission_slug=mission_slug,
        coordinator_owned_refs=coordinator_owned_refs,
    )


def writer_receipt_errors(
    receipt: dict[str, object],
    *,
    coordinator_authorized_ref_updates: object,
    mission_slug: object,
    coordinator_owned_refs: object,
) -> list[str]:
    errors = []
    if (
        not isinstance(receipt.get("commit_count"), int)
        or isinstance(receipt.get("commit_count"), bool)
        or receipt.get("commit_count") != 1
    ):
        errors.append("exactly one commit required")
    if receipt.get("merge_commit") is not False:
        errors.append("merge commit forbidden")
    if receipt.get("mission_base_is_ancestor") is not True:
        errors.append("mission base must be ancestor")
    if receipt.get("parent_is_expected_base") is not True:
        errors.append("commit parent must equal expected base")
    errors.extend(
        worker_ref_snapshot_errors(
            refs_before=receipt.get("refs_before"),
            refs_after=receipt.get("refs_after"),
            coordinator_authorized_updates=coordinator_authorized_ref_updates,
            mission_slug=mission_slug,
            coordinator_owned_refs=coordinator_owned_refs,
        )
    )
    if receipt.get("common_git_config_unchanged") is not True:
        errors.append("worker must preserve common git config")
    if receipt.get("common_git_control_unchanged") is not True:
        errors.append("worker must preserve common git control files")
    if receipt.get("git_admin_identity_unchanged") is not True:
        errors.append("worker must preserve assigned Git admin identity")
    if receipt.get("frozen_worktree_control_unchanged") is not True:
        errors.append("worker must preserve frozen per-worktree Git control")
    if receipt.get("common_worktree_admin_valid") is not True:
        errors.append("worker common worktree admin must match coordinator journal")
    if receipt.get("index_matches_commit_without_unsafe_flags") is not True:
        errors.append("worker index must match commit without unsafe flags")
    if receipt.get("submodule_state_valid") is not True:
        errors.append("worker submodule state must match coordinator baseline")
    if receipt.get("head_is_commit") is not True:
        errors.append("writer HEAD must equal commit")
    if receipt.get("detached_head") is not True:
        errors.append("writer HEAD must remain detached")
    if receipt.get("worktree_clean") is not True:
        errors.append("writer worktree must be clean including untracked files")
    if receipt.get("tree_matches_commit") is not True:
        errors.append("writer filesystem must match commit tree")
    if receipt.get("target_scopes_contained") is not True:
        errors.append("writer scopes must resolve inside exact worktree")
    changed: set[str] = set()
    scopes: set[str] = set()
    raw_scopes = receipt.get("scope", [])
    raw_changed = receipt.get("changed", [])
    if not isinstance(raw_scopes, list):
        errors.append("writer scope must be a list")
        raw_scopes = []
    if not isinstance(raw_changed, list):
        errors.append("changed paths must be a list")
        raw_changed = []
    for raw_scope in raw_scopes:
        normalized, error = parse_repo_scope(raw_scope)
        if error == "unsafe":
            errors.append("writer scope must be a safe repo-relative path")
        elif error == "noncanonical":
            errors.append("writer scope must be canonical")
        if normalized:
            scopes.add(normalized)
    for raw_path in raw_changed:
        normalized, error = parse_repo_scope(raw_path)
        if error == "unsafe":
            errors.append("changed path must be a safe repo-relative path")
        elif error == "noncanonical":
            errors.append("changed path must be canonical")
        if normalized:
            changed.add(normalized)
    if not scopes:
        errors.append("writer scope required")
    if not changed:
        errors.append("writer must change at least one path")
    if any(
        not any(scope_contains(scope, path) for scope in scopes)
        for path in changed
    ):
        errors.append("changed path outside scope")
    if receipt.get("gates_green") is not True:
        errors.append("node gates must be green")
    return errors


def git_read_only_target_errors(
    target: pathlib.Path,
    *,
    expected_revision: str,
    expected_refs: dict[str, str],
    coordinator_authorized_ref_updates: dict[str, dict[str, str]],
    mission_slug: str,
    coordinator_owned_refs: set[str],
    expected_common_config: str,
    expected_common_control: dict[str, str],
    expected_common_worktree_admin: dict[str, str],
    coordinator_worktree_admin_additions: dict[str, dict[str, str]],
    expected_worktree_control: dict[str, str],
    expected_filesystem: dict[str, str],
    coordinator_registry_transition: dict[str, object] | None = None,
) -> list[str]:
    """Verify an isolated git target remained on the exact immutable snapshot."""
    errors = []
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_revision):
        return ["read-only expected revision must be a canonical commit id"]
    if git(
        target,
        "cat-file",
        "-e",
        f"{expected_revision}^{{commit}}",
        check=False,
    ).returncode != 0:
        return ["read-only expected revision must resolve to a commit"]
    current_head = git(
        target,
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )
    if (
        current_head.returncode != 0
        or current_head.stdout.strip() != expected_revision
    ):
        errors.append("read-only HEAD must equal expected revision")
    status_result = git(
        target,
        "status",
        "--short",
        "--untracked-files=all",
        check=False,
    )
    if status_result.returncode != 0 or status_result.stdout:
        errors.append("read-only target must remain clean")
    if git(
        target,
        "diff-tree",
        "--quiet",
        expected_revision,
        "HEAD",
        "--",
        check=False,
    ).returncode != 0:
        errors.append("read-only tree must equal expected revision")
    ref_errors = protected_ref_snapshot_errors(
        refs_before=expected_refs,
        refs_after=git_ref_snapshot(target),
        authorized_updates=coordinator_authorized_ref_updates,
        mission_slug=mission_slug,
        coordinator_owned_refs=coordinator_owned_refs,
    )
    if ref_errors:
        errors.append("read-only protected refs violate authorized transitions")
    if git_common_config_snapshot(target) != expected_common_config:
        errors.append("read-only common git config must match baseline")
    if git_common_control_snapshot(target) != expected_common_control:
        errors.append("read-only common git control files must match baseline")
    try:
        common_worktree_errors = common_worktree_admin_errors(
            before=expected_common_worktree_admin,
            after=git_common_worktree_admin_snapshot(target),
            coordinator_additions=coordinator_worktree_admin_additions,
        )
    except ValueError:
        common_worktree_errors = [
            "common worktree admin snapshot budget or entry type is invalid"
        ]
    if common_worktree_errors:
        errors.append(
            "read-only common worktree admin violates coordinator journal"
        )
    if git_worktree_control_snapshot(target) != expected_worktree_control:
        errors.append("read-only per-worktree git control must match baseline")
    try:
        current_filesystem = worktree_filesystem_snapshot(target)
    except ValueError as error:
        errors.append(
            "read-only filesystem snapshot budget exceeded"
            if str(error) == "filesystem snapshot budget exceeded"
            else "read-only filesystem snapshot contains unsupported entry"
        )
    else:
        baseline_comparable = dict(expected_filesystem)
        current_comparable = dict(current_filesystem)
        registry_transition_valid = False
        registry_relative = (
            f".codex/qtim-runtime/missions/{mission_slug}.json"
        )
        if coordinator_registry_transition is not None:
            transition = coordinator_registry_transition
            required_keys = {
                "beforeFingerprint",
                "afterFingerprint",
                "coordinatorThreadId",
                "hostId",
                "generation",
            }
            before_fingerprint = (
                transition.get("beforeFingerprint")
                if isinstance(transition, dict)
                else None
            )
            after_fingerprint = (
                transition.get("afterFingerprint")
                if isinstance(transition, dict)
                else None
            )
            coordinator_thread_id = (
                transition.get("coordinatorThreadId")
                if isinstance(transition, dict)
                else None
            )
            host_id = (
                transition.get("hostId")
                if isinstance(transition, dict)
                else None
            )
            generation = (
                transition.get("generation")
                if isinstance(transition, dict)
                else None
            )
            fingerprint_pattern = re.compile(
                r"file:[0-7]{1,4}:[0-9]+:[0-9]+:[0-9]+:[0-9a-f]{64}"
            )
            registry_transition_valid = (
                isinstance(transition, dict)
                and set(transition) == required_keys
                and canonical_mission_identifier(mission_slug)
                and isinstance(before_fingerprint, str)
                and isinstance(after_fingerprint, str)
                and fingerprint_pattern.fullmatch(before_fingerprint) is not None
                and fingerprint_pattern.fullmatch(after_fingerprint) is not None
                and before_fingerprint != after_fingerprint
                and isinstance(coordinator_thread_id, str)
                and bool(coordinator_thread_id)
                and isinstance(host_id, str)
                and bool(host_id)
                and isinstance(generation, int)
                and not isinstance(generation, bool)
                and generation >= 1
                and baseline_comparable.get(registry_relative)
                == before_fingerprint
                and current_comparable.get(registry_relative)
                == after_fingerprint
            )
            registry_path = target / registry_relative
            registry_bytes = b""
            if registry_transition_valid:
                try:
                    registry_stat = os.lstat(registry_path)
                    if (
                        not stat.S_ISREG(registry_stat.st_mode)
                        or registry_stat.st_mode & 0o111
                        or registry_stat.st_size > MISSION_REGISTRY_MAX_BYTES
                    ):
                        registry_transition_valid = False
                    else:
                        registry_bytes = registry_path.read_bytes()
                except OSError:
                    registry_transition_valid = False
            if registry_transition_valid:
                registry_stat = os.lstat(registry_path)
                final_fingerprint = (
                    f"file:{registry_stat.st_mode & 0o7777:o}:"
                    f"{registry_stat.st_dev}:{registry_stat.st_ino}:"
                    f"{registry_stat.st_nlink}:"
                    f"{_sha256_bytes(registry_bytes)}"
                )
                if final_fingerprint != after_fingerprint:
                    registry_transition_valid = False
            registry = None
            if registry_transition_valid:
                try:
                    registry = json.loads(registry_bytes.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    registry_transition_valid = False
            if registry_transition_valid:
                ownership = (
                    registry.get("ownership")
                    if isinstance(registry, dict)
                    else None
                )
                registry_transition_valid = (
                    registry.get("schemaVersion") == 1
                    and registry.get("missionId") == mission_slug
                    and isinstance(ownership, dict)
                    and ownership.get("coordinatorThreadId")
                    == coordinator_thread_id
                    and ownership.get("hostId") == host_id
                    and ownership.get("generation") == generation
                )
            if registry_transition_valid:
                baseline_comparable.pop(registry_relative)
                current_comparable.pop(registry_relative)
            else:
                errors.append(
                    "read-only coordinator registry transition must match "
                    "baseline, final bytes, mission, owner, and generation"
                )
        if current_comparable != baseline_comparable:
            errors.append("read-only raw filesystem must match baseline")
    return errors


def git_writer_target_errors(
    target: pathlib.Path,
    *,
    expected_commit: str,
    expected_git_admin_identity: dict[str, str],
    expected_worktree_control: dict[str, str],
    expected_common_config: str,
    expected_common_control: dict[str, str],
    expected_common_worktree_admin: dict[str, str],
    assigned_worktree_entries: set[str],
    coordinator_worktree_admin_additions: dict[str, dict[str, str]],
    expected_submodule_state: dict[str, dict[str, object]],
    authorized_submodule_transitions: set[str],
) -> list[str]:
    errors = []
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_commit):
        return ["writer commit must be a canonical commit id"]
    if git(
        target,
        "cat-file",
        "-e",
        f"{expected_commit}^{{commit}}",
        check=False,
    ).returncode != 0:
        return ["writer commit must resolve"]
    if git(target, "rev-parse", "HEAD").stdout.strip() != expected_commit:
        errors.append("writer HEAD must equal commit")
    symbolic_head = git(
        target,
        "symbolic-ref",
        "-q",
        "HEAD",
        check=False,
    )
    if symbolic_head.returncode == 0 or symbolic_head.stdout.strip():
        errors.append("writer HEAD must remain detached")
    status_result = git(
        target,
        "status",
        "--short",
        "--untracked-files=all",
        check=False,
    )
    if status_result.returncode != 0 or status_result.stdout:
        errors.append("writer worktree must be clean including untracked files")
    if git_tree_filesystem_errors(
        target,
        expected_revision=expected_commit,
    ):
        errors.append("writer filesystem must match commit tree")
    if git_admin_identity_snapshot(target) != expected_git_admin_identity:
        errors.append("writer Git admin identity must match assigned worktree")
    if git_common_config_snapshot(target) != expected_common_config:
        errors.append("writer common Git config must match baseline")
    if git_common_control_snapshot(target) != expected_common_control:
        errors.append("writer common Git control files must match baseline")
    current_worktree_control = git_worktree_control_snapshot(target)
    mutable_control_paths = {"HEAD", "index", "logs/HEAD"}
    frozen_before = {
        path: value
        for path, value in expected_worktree_control.items()
        if path not in mutable_control_paths
    }
    frozen_after = {
        path: value
        for path, value in current_worktree_control.items()
        if path not in mutable_control_paths
    }
    if frozen_after != frozen_before:
        errors.append("writer frozen per-worktree Git control must match baseline")
    if git(
        target,
        "diff-index",
        "--cached",
        "--quiet",
        expected_commit,
        "--",
        check=False,
    ).returncode != 0:
        errors.append("writer index must exactly match commit")
    listed_index = git(
        target,
        "ls-files",
        "-v",
        "-z",
        check=False,
    )
    unmerged_index = git(
        target,
        "ls-files",
        "--unmerged",
        "-z",
        check=False,
    )
    if (
        listed_index.returncode != 0
        or unmerged_index.returncode != 0
        or bool(unmerged_index.stdout)
        or any(
        not record.startswith("H ")
        for record in listed_index.stdout.split("\0")
        if record
        )
    ):
        errors.append("writer index must not contain unsafe flags or stages")
    try:
        common_admin_errors = writer_common_worktree_admin_errors(
            before=expected_common_worktree_admin,
            after=git_common_worktree_admin_snapshot(target),
            assigned_entries=assigned_worktree_entries,
            coordinator_additions=coordinator_worktree_admin_additions,
        )
    except ValueError:
        common_admin_errors = [
            "common worktree admin snapshot budget or entry type is invalid"
        ]
    if common_admin_errors:
        errors.append("writer common worktree admin violates coordinator journal")
    try:
        current_submodule_state = git_submodule_state_snapshot(
            target,
            revision=expected_commit,
        )
    except ValueError:
        current_submodule_state = {}
        errors.append("writer submodule state could not be verified")
    if not isinstance(authorized_submodule_transitions, set) or any(
        not isinstance(path, str) for path in authorized_submodule_transitions
    ):
        errors.append("writer authorized submodule transitions must be canonical")
    else:
        for relative in set(expected_submodule_state) | set(current_submodule_state):
            if relative in authorized_submodule_transitions:
                continue
            if expected_submodule_state.get(relative) != current_submodule_state.get(
                relative
            ):
                errors.append(
                    "writer submodule initialization and admin state must "
                    "match baseline"
                )
                break
    return errors


def lazy_receipt_errors(
    receipt: dict[str, object],
    *,
    expected_role_contracts: dict[str, dict[str, object]],
    expected_node_write_scopes: list[object],
) -> list[str]:
    errors = []
    expected_node_scopes = []
    for raw_scope in expected_node_write_scopes:
        normalized_scope, scope_error = parse_repo_scope(raw_scope)
        if scope_error is not None or normalized_scope is None:
            errors.append("coordinator node scope contract must be canonical")
        else:
            expected_node_scopes.append(normalized_scope)
    if any(
        not isinstance(role_name, str)
        or not role_name
        or not isinstance(contract, dict)
        for role_name, contract in expected_role_contracts.items()
    ):
        errors.append("coordinator role contract must be a map")
    roles = receipt.get("roles", [])
    if not isinstance(roles, list) or any(not isinstance(role, dict) for role in roles):
        return ["lazy roles must be a list of objects"]
    if any(not isinstance(role.get("name"), str) or not role.get("name") for role in roles):
        errors.append("every role needs a string name")
    if any(
        not isinstance(role.get("responsibility"), str)
        or not role.get("responsibility")
        or not isinstance(role.get("output"), str)
        or not role.get("output")
        for role in roles
    ):
        errors.append("every role needs string responsibility and output")
    if receipt.get("descendants_created") is not False:
        errors.append("third-level descendants forbidden")
    if not isinstance(receipt.get("feedback_loop"), bool):
        errors.append("feedback loop flag must be boolean")
    if not isinstance(receipt.get("product_fork"), bool):
        errors.append("product fork flag must be boolean")
    raw_approved_roles = receipt.get("approved_roles", [])
    if (
        not isinstance(raw_approved_roles, list)
        or any(not isinstance(role, str) or not role for role in raw_approved_roles)
    ):
        errors.append("approved roles must be a list of names")
        raw_approved_roles = []
    approved_roles = set(expected_role_contracts)
    if set(raw_approved_roles) != approved_roles:
        errors.append("receipt approved roles differ from coordinator contract")
    role_names = [role.get("name") for role in roles]
    actual_roles = set(role_names)
    if len(actual_roles) != len(role_names):
        errors.append("duplicate lazy role")
    unauthorized_role = bool(actual_roles - approved_roles)
    if unauthorized_role:
        errors.append("role outside approved allowlist")
    scoped_roles = []
    for role in roles:
        role_name = role.get("name")
        expected_contract = expected_role_contracts.get(role_name, {})
        write_policy = role.get("write_policy")
        role_scopes = role.get("write_scopes", [])
        read_scopes = role.get("read_scopes", [])
        if write_policy not in {"writer", "read-only"}:
            errors.append("role write policy must be writer or read-only")
        if expected_contract and write_policy != expected_contract.get("write_policy"):
            errors.append("role write policy differs from coordinator contract")
        if expected_contract and (
            role.get("responsibility") != expected_contract.get("responsibility")
            or role.get("output") != expected_contract.get("output")
        ):
            errors.append("role responsibility/output differs from coordinator contract")
        if not isinstance(role_scopes, list):
            errors.append("local write scopes must be a list")
            continue
        if not isinstance(read_scopes, list):
            errors.append("local read scopes must be a list")
            read_scopes = []
        if write_policy == "writer" and not role_scopes:
            errors.append("writer role needs a write scope")
        if write_policy == "read-only":
            if role_scopes:
                errors.append("read-only role must have empty write scopes")
            if not read_scopes:
                errors.append("read-only role needs an explicit read scope")
        normalized_read_scopes = []
        for raw_scope in read_scopes:
            normalized_scope, scope_error = parse_repo_scope(raw_scope)
            if scope_error == "unsafe":
                errors.append("read scope must be a safe repo-relative path")
            elif scope_error == "noncanonical":
                errors.append("read scope must be canonical")
            if normalized_scope is None:
                continue
            normalized_read_scopes.append(normalized_scope)
        normalized_write_scopes = []
        for raw_scope in role_scopes:
            normalized_scope, scope_error = parse_repo_scope(raw_scope)
            if scope_error == "unsafe":
                errors.append("write scope must be a safe repo-relative path")
                continue
            if scope_error == "noncanonical":
                errors.append("write scope must be canonical")
            if normalized_scope:
                normalized_write_scopes.append(normalized_scope)
                scoped_roles.append((role.get("name"), normalized_scope))
        expected_write_scopes = []
        expected_read_scopes = []
        for expected_scope in expected_contract.get("write_scopes", []):
            normalized, error = parse_repo_scope(expected_scope)
            if error is not None or normalized is None:
                errors.append("coordinator role scope contract must be canonical")
            else:
                expected_write_scopes.append(normalized)
        for expected_scope in expected_contract.get("read_scopes", []):
            normalized, error = parse_repo_scope(expected_scope)
            if error is not None or normalized is None:
                errors.append("coordinator role scope contract must be canonical")
            else:
                expected_read_scopes.append(normalized)
        if any(
            not any(
                scope_contains(allowed, scope)
                for allowed in expected_write_scopes
            )
            or not any(
                scope_contains(node_scope, scope)
                for node_scope in expected_node_scopes
            )
            for scope in normalized_write_scopes
        ):
            errors.append("role write scope exceeds coordinator contract")
        if any(
            not any(
                scope_contains(allowed, scope)
                for allowed in expected_read_scopes
            )
            for scope in normalized_read_scopes
        ):
            errors.append("role read scope exceeds coordinator contract")
    scope_collision = False
    for index, (left_role, left_scope) in enumerate(scoped_roles):
        for right_role, right_scope in scoped_roles[index + 1 :]:
            if left_role == right_role:
                continue
            if scopes_overlap(left_scope, right_scope):
                errors.append("local write scopes overlap")
                scope_collision = True
                index = len(scoped_roles)
                break
        else:
            continue
        break
    escalation_marker = receipt.get("escalation", "")
    if escalation_marker not in {"", "ESCALATION_REQUEST"}:
        errors.append("invalid mission escalation marker")
    escalation_condition = bool(
        receipt.get("feedback_loop")
        or receipt.get("product_fork")
        or unauthorized_role
        or scope_collision
    )
    if escalation_condition and escalation_marker != "ESCALATION_REQUEST":
        errors.append("mission escalation requires ESCALATION_REQUEST")
    requires_escalation = bool(
        escalation_condition or escalation_marker == "ESCALATION_REQUEST"
    )
    if requires_escalation and receipt.get("status") != "BLOCKED":
        errors.append("mission escalation must return BLOCKED")
    if receipt.get("status") == "BLOCKED":
        errors.append("BLOCKED lazy receipt cannot validate")
    elif receipt.get("status") != "SUCCEEDED":
        errors.append("lazy receipt status must be SUCCEEDED or BLOCKED")
    if receipt.get("lead_checked_results") is not True:
        errors.append("node lead must check local results")
    return errors


def classify_resume(
    *,
    tool_available: bool,
    candidates: int,
    project_matches: bool,
    marker_matches: bool,
    attempt_matches: bool,
    host_matches: bool,
    source_matches: bool,
    base_matches: bool,
    pending_creation: bool = False,
    portable_state_clean: bool = True,
    state_sequence_valid: bool = True,
) -> str:
    if not tool_available:
        return "unavailable"
    if not portable_state_clean or not state_sequence_valid:
        return "blocked"
    if pending_creation and candidates == 0:
        return "pending"
    if candidates == 0:
        return "orphan"
    if candidates > 1:
        return "ambiguous"
    if not all(
        (
            project_matches,
            marker_matches,
            attempt_matches,
            host_matches,
            source_matches,
            base_matches,
        )
    ):
        return "stale"
    return "live"


def mission_terminal_status(
    *,
    durable_status: str,
    final_verdict: str,
    evidence_delivered: bool,
    evidence_matches_checkpoint: bool,
    done_checkpoint_clean: bool,
    done_checkpoint_matches_delivery: bool,
) -> str:
    if (
        durable_status == "Done"
        and final_verdict == "APPROVED"
        and evidence_delivered is True
        and evidence_matches_checkpoint is True
        and done_checkpoint_clean is True
        and done_checkpoint_matches_delivery is True
    ):
        return "Done"
    return "Verifying"


def exact_verification_verdict(body: str) -> str | None:
    """Parse only exact verdict records; the final exact record is authoritative."""
    verdicts: list[str] = []
    for raw_line in body.splitlines():
        if raw_line in {"verdict: APPROVED", "verdict: NOT APPROVED"}:
            verdicts.append(raw_line.removeprefix("verdict: "))
            continue
        if raw_line.lstrip().startswith("verdict:"):
            return None
    return verdicts[-1] if verdicts else None


def reconcile_delivered_evidence(
    *,
    final_verdict: str,
    durable_status: str,
    delivered_revision: str,
    promoted_revision: str,
    recorded_delivery_revision: str | None,
    evidence_matches_checkpoint: bool,
    delivered_revision_resolves: bool,
    promoted_revision_resolves: bool,
) -> str:
    """Return the only safe action for the post-promotion crash window."""
    canonical_oid = bool(
        re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", delivered_revision)
    )
    canonical_promoted_oid = bool(
        re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", promoted_revision)
    )
    recorded_oid_valid = (
        recorded_delivery_revision is None
        or bool(
            re.fullmatch(
                r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
                recorded_delivery_revision,
            )
        )
    )
    if (
        final_verdict != "APPROVED"
        or evidence_matches_checkpoint is not True
        or not canonical_oid
        or not canonical_promoted_oid
        or delivered_revision != promoted_revision
        or not recorded_oid_valid
        or delivered_revision_resolves is not True
        or promoted_revision_resolves is not True
    ):
        return "blocked"
    if durable_status == "Verifying" and recorded_delivery_revision is None:
        return "checkpoint-done"
    if durable_status == "Done":
        return (
            "noop"
            if recorded_delivery_revision == delivered_revision
            else "blocked"
        )
    return "blocked"


def classify_coordinator_ownership(
    *,
    tool_available: bool,
    same_coordinator: bool,
    previous_coordinator_running: bool,
    previous_coordinator_confirmed: bool,
    explicit_resume: bool,
    generation_matches: bool,
) -> str:
    if not tool_available or not previous_coordinator_confirmed:
        return "unavailable"
    if not generation_matches:
        return "stale"
    if same_coordinator:
        return "owned"
    if previous_coordinator_running:
        return "ambiguous"
    if not explicit_resume:
        return "unavailable"
    return "takeover"


def canonical_mission_runtime_paths(
    project_root: pathlib.Path,
    mission_slug: str,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    if not canonical_mission_identifier(mission_slug):
        raise ValueError("mission slug must be canonical")
    missions = project_root / ".codex" / "qtim-runtime" / "missions"
    return (
        missions / f"{mission_slug}.json",
        missions / f"{mission_slug}.ownership.lock",
        missions / f"{mission_slug}.promotion.lock",
    )


def local_state_path_errors(
    project_root: pathlib.Path,
    target: pathlib.Path,
    *,
    leaf_kind: str,
) -> list[str]:
    """Reject symlink/junction, escape and cross-device state paths before writes."""
    if leaf_kind not in {"regular", "directory"}:
        return ["local state leaf kind must be canonical"]
    project_root = pathlib.Path(os.path.abspath(project_root))
    target = pathlib.Path(os.path.abspath(target))
    try:
        target.relative_to(project_root)
    except ValueError:
        return ["local state path must be inside exact project root"]
    try:
        root_stat = os.lstat(project_root)
    except FileNotFoundError:
        return ["exact project root must exist"]
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or is_filesystem_junction(project_root)
    ):
        return ["exact project root must be a real directory"]
    try:
        resolved_root = project_root.resolve(strict=True)
    except OSError:
        return ["exact project root must resolve"]
    current = project_root
    for component in target.relative_to(project_root).parts[:-1]:
        current = current / component
        try:
            current_stat = os.lstat(current)
        except FileNotFoundError:
            return ["local state parent directories must exist before write"]
        if (
            not stat.S_ISDIR(current_stat.st_mode)
            or stat.S_ISLNK(current_stat.st_mode)
            or is_filesystem_junction(current)
            or current_stat.st_dev != root_stat.st_dev
        ):
            return ["local state parents must be real same-filesystem directories"]
        try:
            current.resolve(strict=True).relative_to(resolved_root)
        except (OSError, ValueError):
            return ["local state parent escaped exact project root"]
    try:
        leaf_stat = os.lstat(target)
    except FileNotFoundError:
        leaf_stat = None
    if leaf_stat is not None:
        if (
            stat.S_ISLNK(leaf_stat.st_mode)
            or is_filesystem_junction(target)
            or leaf_stat.st_dev != root_stat.st_dev
        ):
            return ["local state leaf must be contained on the same filesystem"]
        if leaf_kind == "regular" and not stat.S_ISREG(leaf_stat.st_mode):
            return ["local state registry leaf must be a regular file"]
        if leaf_kind == "directory" and not stat.S_ISDIR(leaf_stat.st_mode):
            return ["local state evidence leaf must be a directory"]
    return []


def initialize_local_state_parents_fixture(
    project_root: pathlib.Path,
    target: pathlib.Path,
    *,
    leaf_kind: str,
    mode: int = 0o700,
) -> list[str]:
    """Create missing first-run components one at a time, then revalidate."""
    if (
        leaf_kind not in {"regular", "directory"}
        or not isinstance(mode, int)
        or isinstance(mode, bool)
        or mode < 0
        or mode > 0o777
    ):
        return ["local state directory mode must be canonical"]
    project_root = pathlib.Path(os.path.abspath(project_root))
    target = pathlib.Path(os.path.abspath(target))
    try:
        relative = target.relative_to(project_root)
        root_stat = os.lstat(project_root)
        resolved_root = project_root.resolve(strict=True)
    except (ValueError, FileNotFoundError, OSError):
        return ["exact project root must be a resolvable real directory"]
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or is_filesystem_junction(project_root)
    ):
        return ["exact project root must be a real directory"]
    current = project_root
    directory_components = (
        relative.parts
        if leaf_kind == "directory"
        else relative.parts[:-1]
    )
    for component in directory_components:
        current = current / component
        try:
            os.mkdir(current, mode)
        except FileExistsError:
            pass
        except OSError:
            return ["local state parent could not be created exclusively"]
        try:
            current_stat = os.lstat(current)
            resolved_current = current.resolve(strict=True)
            resolved_current.relative_to(resolved_root)
        except (FileNotFoundError, OSError, ValueError):
            return ["local state parent failed post-create containment"]
        if (
            not stat.S_ISDIR(current_stat.st_mode)
            or stat.S_ISLNK(current_stat.st_mode)
            or is_filesystem_junction(current)
            or current_stat.st_dev != root_stat.st_dev
        ):
            return ["local state parents must be real same-filesystem directories"]
    return local_state_path_errors(
        project_root,
        target,
        leaf_kind=leaf_kind,
    )


def atomic_registry_initialize_fixture(
    project_root: pathlib.Path,
    mission_slug: str,
    *,
    coordinator_thread_id: str,
    host_id: str,
) -> str:
    """Publish the first registry under its canonical ownership lock without clobber."""
    if (
        not isinstance(coordinator_thread_id, str)
        or not coordinator_thread_id
        or not isinstance(host_id, str)
        or not host_id
    ):
        return "unavailable"
    try:
        registry_path, lock_path, _ = canonical_mission_runtime_paths(
            project_root,
            mission_slug,
        )
    except ValueError:
        return "unavailable"
    if initialize_local_state_parents_fixture(
        project_root,
        registry_path,
        leaf_kind="regular",
    ):
        return "unavailable"
    if (
        local_state_path_errors(
            project_root,
            registry_path,
            leaf_kind="regular",
        )
        or local_state_path_errors(
            project_root,
            lock_path,
            leaf_kind="directory",
        )
    ):
        return "unavailable"
    try:
        lock_path.mkdir()
    except FileExistsError:
        return "ambiguous"
    except OSError:
        return "unavailable"

    temporary_path = registry_path.with_name(
        f"{registry_path.name}.init.tmp"
    )
    temporary_created = False
    try:
        if registry_path.exists() or registry_path.is_symlink():
            return "ambiguous"
        if local_state_path_errors(
            project_root,
            temporary_path,
            leaf_kind="regular",
        ):
            return "unavailable"
        registry = {
            "schemaVersion": 1,
            "missionId": mission_slug,
            "ownership": {
                "coordinatorThreadId": coordinator_thread_id,
                "hostId": host_id,
                "generation": 1,
            },
        }
        try:
            temporary = temporary_path.open("x", encoding="utf-8")
        except FileExistsError:
            return "ambiguous"
        except OSError:
            return "unavailable"
        temporary_created = True
        with temporary:
            json.dump(registry, temporary, ensure_ascii=False, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(
                temporary_path,
                registry_path,
                follow_symlinks=False,
            )
        except FileExistsError:
            return "ambiguous"
        except OSError:
            return "unavailable"
        temporary_path.unlink()
        temporary_created = False
        directory_fd = os.open(registry_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            final_stat = os.lstat(registry_path)
            final_registry = json.loads(
                registry_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return "unavailable"
        if (
            not stat.S_ISREG(final_stat.st_mode)
            or stat.S_ISLNK(final_stat.st_mode)
            or final_stat.st_nlink != 1
            or final_registry != registry
        ):
            return "unavailable"
        return "owned"
    finally:
        if temporary_created and temporary_path.exists():
            temporary_path.unlink()
        lock_path.rmdir()


def atomic_takeover_fixture(
    project_root: pathlib.Path,
    mission_slug: str,
    *,
    expected_generation: int,
    new_thread_id: str,
    new_host_id: str,
) -> str:
    try:
        registry_path, lock_path, _ = canonical_mission_runtime_paths(
            project_root,
            mission_slug,
        )
    except ValueError:
        return "unavailable"
    if local_state_path_errors(
        project_root,
        registry_path,
        leaf_kind="regular",
    ):
        return "unavailable"
    try:
        lock_path.mkdir()
    except FileExistsError:
        return "ambiguous"

    temporary_path = registry_path.with_suffix(".json.tmp")
    temporary_created = False
    try:
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            ownership = registry["ownership"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            return "unavailable"
        if (
            registry.get("missionId") != mission_slug
            or not isinstance(ownership, dict)
        ):
            return "unavailable"
        if ownership.get("generation") != expected_generation:
            return "stale"
        expected_ownership = {
            "coordinatorThreadId": new_thread_id,
            "hostId": new_host_id,
            "generation": expected_generation + 1,
        }
        ownership.update(expected_ownership)
        try:
            temporary = temporary_path.open("x", encoding="utf-8")
        except FileExistsError:
            return "ambiguous"
        temporary_created = True
        with temporary:
            json.dump(registry, temporary, ensure_ascii=False)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, registry_path)
        directory_fd = os.open(registry_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            final_stat = os.lstat(registry_path)
            final_registry = json.loads(
                registry_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return "ambiguous"
        if (
            not stat.S_ISREG(final_stat.st_mode)
            or stat.S_ISLNK(final_stat.st_mode)
            or final_stat.st_nlink != 1
            or final_registry != registry
            or final_registry.get("missionId") != mission_slug
            or final_registry.get("ownership") != expected_ownership
        ):
            return "ambiguous"
        return "takeover"
    finally:
        if temporary_created and temporary_path.exists():
            temporary_path.unlink()
        lock_path.rmdir()


def git(repo: pathlib.Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        check=False,
    )
    if check and result.returncode != 0:
        fail(f"git fixture failed: {' '.join(args)}: {result.stderr.strip()}")
    return result


def git_ref_snapshot(repo: pathlib.Path) -> dict[str, str]:
    snapshot = {}
    output = git(
        repo,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)",
    ).stdout
    for line in output.splitlines():
        ref_name, object_name = line.split("\0", 1)
        if ref_name.startswith("refs/codex/"):
            continue
        snapshot[ref_name] = object_name
    return snapshot


def git_common_config_snapshot(repo: pathlib.Path) -> str:
    return git(
        repo,
        "config",
        "--local",
        "--null",
        "--list",
        "--show-origin",
    ).stdout


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def worktree_filesystem_snapshot(
    repo: pathlib.Path,
    *,
    opaque_directories: set[str] | None = None,
    max_entries: int = FILESYSTEM_SNAPSHOT_MAX_ENTRIES,
    max_bytes: int = FILESYSTEM_SNAPSHOT_MAX_BYTES,
) -> dict[str, str]:
    """Hash actual worktree entries without trusting Git index or ignore rules."""
    snapshot = {}
    opaque_directories = opaque_directories or set()
    entry_count = 0
    byte_count = 0

    def reserve_entry(size: int = 0) -> None:
        nonlocal entry_count, byte_count
        entry_count += 1
        byte_count += size
        if entry_count > max_entries or byte_count > max_bytes:
            raise ValueError("filesystem snapshot budget exceeded")

    def bounded_file_digest(path: pathlib.Path) -> str:
        nonlocal byte_count
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(min(1024 * 1024, max_bytes - byte_count + 1)):
                byte_count += len(chunk)
                if byte_count > max_bytes:
                    raise ValueError("filesystem snapshot budget exceeded")
                digest.update(chunk)
        return digest.hexdigest()

    if (
        not isinstance(max_entries, int)
        or isinstance(max_entries, bool)
        or max_entries < 1
        or not isinstance(max_bytes, int)
        or isinstance(max_bytes, bool)
        or max_bytes < 1
    ):
        raise ValueError("filesystem snapshot budget exceeded")
    repo_stat = os.lstat(repo)
    if (
        not stat.S_ISDIR(repo_stat.st_mode)
        or stat.S_ISLNK(repo_stat.st_mode)
        or is_filesystem_junction(repo)
    ):
        raise ValueError("unsupported filesystem entry")
    reserve_entry()
    snapshot["@root"] = (
        f"directory:{repo_stat.st_mode & 0o7777:o}:"
        f"{repo_stat.st_dev}:{repo_stat.st_ino}:{repo_stat.st_nlink}"
    )
    for current_root, directory_names, file_names in os.walk(
        repo,
        topdown=True,
        followlinks=False,
    ):
        current = pathlib.Path(current_root)
        relative_root = current.relative_to(repo)
        kept_directories = []
        for directory_name in sorted(directory_names):
            if relative_root == pathlib.Path(".") and directory_name == ".git":
                continue
            directory = current / directory_name
            relative = (relative_root / directory_name).as_posix()
            if is_filesystem_junction(directory):
                raise ValueError("unsupported filesystem entry")
            if directory.is_symlink():
                target = os.readlink(directory).encode()
                directory_stat = os.lstat(directory)
                reserve_entry(len(target))
                snapshot[relative] = (
                    f"symlink:{directory_stat.st_mode & 0o7777:o}:"
                    f"{directory_stat.st_dev}:{directory_stat.st_ino}:"
                    f"{directory_stat.st_nlink}:{_sha256_bytes(target)}"
                )
            elif relative in opaque_directories:
                reserve_entry()
                snapshot[relative] = "opaque-directory"
            else:
                directory_stat = os.lstat(directory)
                reserve_entry()
                snapshot[f"{relative}/"] = (
                    f"directory:{directory_stat.st_mode & 0o7777:o}:"
                    f"{directory_stat.st_dev}:{directory_stat.st_ino}:"
                    f"{directory_stat.st_nlink}"
                )
                kept_directories.append(directory_name)
        directory_names[:] = kept_directories
        for file_name in sorted(file_names):
            if relative_root == pathlib.Path(".") and file_name == ".git":
                continue
            file_path = current / file_name
            relative = (relative_root / file_name).as_posix()
            if file_path.is_symlink():
                target = os.readlink(file_path).encode()
                file_stat = os.lstat(file_path)
                reserve_entry(len(target))
                snapshot[relative] = (
                    f"symlink:{file_stat.st_mode & 0o7777:o}:"
                    f"{file_stat.st_dev}:{file_stat.st_ino}:"
                    f"{file_stat.st_nlink}:{_sha256_bytes(target)}"
                )
                continue
            reserve_entry()
            file_stat = os.lstat(file_path)
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError("unsupported filesystem entry")
            snapshot[relative] = (
                f"file:{file_stat.st_mode & 0o7777:o}:"
                f"{file_stat.st_dev}:{file_stat.st_ino}:{file_stat.st_nlink}:"
                f"{bounded_file_digest(file_path)}"
            )
    return snapshot


def git_common_control_snapshot(repo: pathlib.Path) -> dict[str, str]:
    common_dir_raw = git(
        repo,
        "rev-parse",
        "--git-common-dir",
    ).stdout.strip()
    common_dir = pathlib.Path(common_dir_raw)
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    protected_paths = (
        "config",
        "objects",
        "modules",
        "refs",
        "logs",
        "info",
        "hooks",
        "packed-refs",
        "info/exclude",
        "info/attributes",
        "info/grafts",
        "objects/info/alternates",
        "shallow",
    )
    snapshot = {}

    def fingerprint(target: pathlib.Path) -> str:
        try:
            target_stat = os.lstat(target)
        except FileNotFoundError:
            return "<missing>"
        mode = target_stat.st_mode & 0o7777
        if stat.S_ISLNK(target_stat.st_mode):
            return (
                f"symlink:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}:"
                f"{target_stat.st_nlink}:"
                f"{_sha256_bytes(os.readlink(target).encode())}"
            )
        if stat.S_ISREG(target_stat.st_mode):
            return (
                f"file:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}:"
                f"{target_stat.st_nlink}:{_sha256_bytes(target.read_bytes())}"
            )
        if stat.S_ISDIR(target_stat.st_mode):
            return (
                f"directory:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}"
            )
        return f"special:{stat.S_IFMT(target_stat.st_mode):o}:{mode:o}"

    for relative in protected_paths:
        target = common_dir / relative
        snapshot[relative] = fingerprint(target)
    hooks = common_dir / "hooks"
    snapshot["hooks"] = fingerprint(hooks)
    try:
        hooks_stat = os.lstat(hooks)
    except FileNotFoundError:
        hooks_stat = None
    if hooks_stat is not None and stat.S_ISDIR(hooks_stat.st_mode):
        for hook in sorted(hooks.rglob("*")):
            relative = hook.relative_to(common_dir).as_posix()
            snapshot[relative] = fingerprint(hook)
    return snapshot


def git_admin_identity_snapshot(repo: pathlib.Path) -> dict[str, str]:
    """Bind validation to the exact App-assigned .git marker and Git dirs."""

    def entry_fingerprint(target: pathlib.Path) -> str:
        try:
            target_stat = os.lstat(target)
        except FileNotFoundError:
            return "<missing>"
        mode = target_stat.st_mode & 0o7777
        if stat.S_ISLNK(target_stat.st_mode):
            return (
                f"symlink:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}:"
                f"{target_stat.st_nlink}:"
                f"{_sha256_bytes(os.readlink(target).encode())}"
            )
        if stat.S_ISREG(target_stat.st_mode):
            return (
                f"file:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}:"
                f"{target_stat.st_nlink}:{_sha256_bytes(target.read_bytes())}"
            )
        if stat.S_ISDIR(target_stat.st_mode):
            return (
                f"directory:{mode:o}:{target_stat.st_dev}:{target_stat.st_ino}"
            )
        return f"special:{stat.S_IFMT(target_stat.st_mode):o}:{mode:o}"

    def resolved_identity(raw_path: str) -> tuple[str, pathlib.Path]:
        path = pathlib.Path(raw_path)
        lexical = path if path.is_absolute() else repo / path
        lexical = pathlib.Path(os.path.abspath(lexical))
        try:
            resolved = lexical.resolve(strict=True)
        except OSError:
            return f"{lexical.as_posix()}|<unresolved>", lexical
        return f"{lexical.as_posix()}|{resolved.as_posix()}", lexical

    git_dir_raw = git(
        repo,
        "rev-parse",
        "--git-dir",
        check=False,
    )
    common_dir_raw = git(
        repo,
        "rev-parse",
        "--git-common-dir",
        check=False,
    )
    snapshot = {
        "@worktree-dotgit": entry_fingerprint(repo / ".git"),
        "@git-dir-command": f"exit:{git_dir_raw.returncode}:{git_dir_raw.stdout}",
        "@common-dir-command": (
            f"exit:{common_dir_raw.returncode}:{common_dir_raw.stdout}"
        ),
    }
    if git_dir_raw.returncode == 0 and git_dir_raw.stdout.strip():
        identity, lexical = resolved_identity(git_dir_raw.stdout.strip())
        snapshot["@git-dir-identity"] = identity
        snapshot["@git-dir-root"] = entry_fingerprint(lexical)
    else:
        snapshot["@git-dir-identity"] = "<unavailable>"
        snapshot["@git-dir-root"] = "<unavailable>"
    if common_dir_raw.returncode == 0 and common_dir_raw.stdout.strip():
        identity, lexical = resolved_identity(common_dir_raw.stdout.strip())
        snapshot["@common-dir-identity"] = identity
        snapshot["@common-dir-root"] = entry_fingerprint(lexical)
    else:
        snapshot["@common-dir-identity"] = "<unavailable>"
        snapshot["@common-dir-root"] = "<unavailable>"
    return snapshot


def git_common_worktree_admin_snapshot(repo: pathlib.Path) -> dict[str, str]:
    """Fingerprint the common worktree registry, including foreign entries."""
    common_dir_raw = git(
        repo,
        "rev-parse",
        "--git-common-dir",
    ).stdout.strip()
    common_dir = pathlib.Path(common_dir_raw)
    if not common_dir.is_absolute():
        common_dir = pathlib.Path(os.path.abspath(repo / common_dir))
    worktrees = common_dir / "worktrees"
    try:
        root_stat = os.lstat(worktrees)
    except FileNotFoundError:
        return {"@root": "<missing>"}
    root_mode = root_stat.st_mode & 0o7777
    if stat.S_ISLNK(root_stat.st_mode):
        return {
            "@root": (
                f"symlink:{root_mode:o}:"
                f"{_sha256_bytes(os.readlink(worktrees).encode())}"
            )
        }
    if not stat.S_ISDIR(root_stat.st_mode):
        return {
            "@root": (
                f"special:{stat.S_IFMT(root_stat.st_mode):o}:{root_mode:o}"
            )
        }
    return {
        **worktree_filesystem_snapshot(worktrees),
        "@root": (
            f"directory:{root_mode:o}:{root_stat.st_dev}:{root_stat.st_ino}"
        ),
    }


def common_worktree_admin_errors(
    *,
    before: dict[str, str],
    after: dict[str, str],
    coordinator_additions: dict[str, dict[str, str]],
) -> list[str]:
    """Allow only exact new coordinator-created worktree admin subtrees."""
    if not (
        isinstance(before, dict)
        and isinstance(after, dict)
        and isinstance(coordinator_additions, dict)
        and all(
            isinstance(path, str) and isinstance(value, str)
            for snapshot in (before, after)
            for path, value in snapshot.items()
        )
    ):
        return ["common worktree admin proof must be canonical"]
    remaining_after = dict(after)
    for entry_name, journaled_subtree in coordinator_additions.items():
        if (
            not isinstance(entry_name, str)
            or not entry_name
            or entry_name in {".", ".."}
            or "/" in entry_name
            or "\\" in entry_name
            or any(ord(character) < 32 for character in entry_name)
            or not isinstance(journaled_subtree, dict)
            or not journaled_subtree
            or any(
                not isinstance(path, str) or not isinstance(value, str)
                for path, value in journaled_subtree.items()
            )
        ):
            return ["common worktree admin journal must be canonical"]
        prefix = f"{entry_name}/"
        if any(
            path == entry_name or path.startswith(prefix)
            for path in before
        ):
            return [
                "common worktree admin journal cannot authorize "
                "a pre-existing entry"
            ]
        actual_subtree = {
            path: value
            for path, value in after.items()
            if path == entry_name or path.startswith(prefix)
        }
        if actual_subtree != journaled_subtree:
            return [
                "common worktree admin journal must match exact added subtree"
            ]
        for path in actual_subtree:
            remaining_after.pop(path)
    if remaining_after != before:
        return ["common worktree admin changed outside coordinator additions"]
    return []


def writer_common_worktree_admin_errors(
    *,
    before: dict[str, str],
    after: dict[str, str],
    assigned_entries: set[str],
    coordinator_additions: dict[str, dict[str, str]],
) -> list[str]:
    """Freeze foreign entries while assigned writer admin changes are validated locally."""
    comparable_before = dict(before)
    comparable_after = dict(after)
    if not isinstance(assigned_entries, set):
        return ["assigned common worktree entries must be canonical"]
    for assigned_entry in assigned_entries:
        if (
            not isinstance(assigned_entry, str)
            or not assigned_entry
            or assigned_entry in {".", ".."}
            or "/" in assigned_entry
            or "\\" in assigned_entry
        ):
            return ["assigned common worktree entry must be canonical"]
        prefix = f"{assigned_entry}/"
        before_assigned = {
            path: value
            for path, value in before.items()
            if path == assigned_entry or path.startswith(prefix)
        }
        after_assigned = {
            path: value
            for path, value in after.items()
            if path == assigned_entry or path.startswith(prefix)
        }
        if not before_assigned or not after_assigned:
            return ["assigned common worktree entry must exist before and after"]
        required_directories = {
            f"{assigned_entry}/",
        }
        required_files = {
            f"{assigned_entry}/HEAD",
            f"{assigned_entry}/index",
        }
        optional_files = {f"{assigned_entry}/COMMIT_EDITMSG"}
        logs_directory = f"{assigned_entry}/logs/"
        logs_head = f"{assigned_entry}/logs/HEAD"
        directory_pattern = re.compile(
            r"directory:([0-7]{1,4}):[0-9]+:[0-9]+:[0-9]+"
        )
        file_pattern = re.compile(
            r"file:([0-7]{1,4}):[0-9]+:[0-9]+:([0-9]+):[0-9a-f]{64}"
        )
        if any(
            directory_pattern.fullmatch(after.get(path, "")) is None
            for path in required_directories
        ):
            return ["assigned common worktree admin directories must be real"]
        for path in required_files | optional_files:
            fingerprint = after.get(path)
            if fingerprint is None and path in optional_files:
                continue
            match = file_pattern.fullmatch(fingerprint or "")
            if (
                match is None
                or int(match.group(1), 8) & 0o111
                or int(match.group(2)) != 1
            ):
                return [
                    "assigned common worktree admin files must be regular, "
                    "non-executable, and single-link"
                ]
        logs_directory_fingerprint = after.get(logs_directory)
        logs_head_fingerprint = after.get(logs_head)
        if (logs_directory_fingerprint is None) != (logs_head_fingerprint is None):
            return ["assigned common worktree reflog admin must be a complete pair"]
        if logs_directory_fingerprint is not None:
            logs_match = file_pattern.fullmatch(logs_head_fingerprint or "")
            if (
                directory_pattern.fullmatch(logs_directory_fingerprint) is None
                or logs_match is None
                or int(logs_match.group(1), 8) & 0o111
                or int(logs_match.group(2)) != 1
            ):
                return [
                    "assigned common worktree reflog admin must be real "
                    "and single-link"
                ]
        mutable_paths = {
            f"{assigned_entry}/",
            f"{assigned_entry}/COMMIT_EDITMSG",
            f"{assigned_entry}/HEAD",
            f"{assigned_entry}/index",
            f"{assigned_entry}/logs/",
            f"{assigned_entry}/logs/HEAD",
        }
        for path in mutable_paths:
            comparable_before.pop(path, None)
            comparable_after.pop(path, None)
    return common_worktree_admin_errors(
        before=comparable_before,
        after=comparable_after,
        coordinator_additions=coordinator_additions,
    )


def assigned_common_worktree_entry(repo: pathlib.Path) -> str | None:
    git_dir_raw = git(repo, "rev-parse", "--git-dir").stdout.strip()
    common_dir_raw = git(repo, "rev-parse", "--git-common-dir").stdout.strip()
    git_dir = pathlib.Path(git_dir_raw)
    common_dir = pathlib.Path(common_dir_raw)
    if not git_dir.is_absolute():
        git_dir = pathlib.Path(os.path.abspath(repo / git_dir))
    if not common_dir.is_absolute():
        common_dir = pathlib.Path(os.path.abspath(repo / common_dir))
    try:
        relative = git_dir.relative_to(common_dir / "worktrees")
    except ValueError:
        return None
    return relative.parts[0] if len(relative.parts) == 1 else None


def git_worktree_control_snapshot(repo: pathlib.Path) -> dict[str, str]:
    """Fingerprint per-worktree Git metadata without traversing shared objects/refs."""
    git_dir_raw = git(repo, "rev-parse", "--git-dir").stdout.strip()
    git_dir = pathlib.Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = (repo / git_dir).resolve()
    protected_paths = (
        "HEAD",
        "index",
        "commondir",
        "gitdir",
        "config.worktree",
        "info/sparse-checkout",
        "logs/HEAD",
        "ORIG_HEAD",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
    )
    snapshot = git_admin_identity_snapshot(repo)
    for relative in protected_paths:
        target = git_dir / relative
        try:
            target_stat = os.lstat(target)
        except FileNotFoundError:
            snapshot[relative] = "<missing>"
            continue
        mode = target_stat.st_mode & 0o7777
        if stat.S_ISLNK(target_stat.st_mode):
            snapshot[relative] = (
                f"symlink:{mode:o}:"
                f"{_sha256_bytes(os.readlink(target).encode())}"
            )
        elif stat.S_ISREG(target_stat.st_mode):
            snapshot[relative] = (
                f"file:{mode:o}:{_sha256_bytes(target.read_bytes())}"
            )
        elif stat.S_ISDIR(target_stat.st_mode):
            snapshot[relative] = f"directory:{mode:o}"
        else:
            snapshot[relative] = (
                f"special:{stat.S_IFMT(target_stat.st_mode):o}:{mode:o}"
            )
    return snapshot


def git_submodule_state_snapshot(
    repo: pathlib.Path,
    *,
    revision: str,
) -> dict[str, dict[str, object]]:
    """Capture initialized/uninitialized topology for every gitlink in a commit."""
    tree = git(
        repo,
        "ls-tree",
        "-rz",
        "--full-tree",
        revision,
        check=False,
    )
    if tree.returncode != 0:
        raise ValueError("submodule baseline revision must resolve")
    gitlinks = {}
    for record in tree.stdout.split("\0"):
        if not record:
            continue
        metadata, relative = record.split("\t", 1)
        mode, object_type, object_id = metadata.split()
        if mode == "160000" and object_type == "commit":
            gitlinks[relative] = object_id
    snapshot: dict[str, dict[str, object]] = {}
    for relative, object_id in gitlinks.items():
        target = repo / relative
        try:
            target_stat = os.lstat(target)
        except FileNotFoundError:
            snapshot[relative] = {
                "kind": "uninitialized-missing",
                "expectedHead": object_id,
            }
            continue
        if not stat.S_ISDIR(target_stat.st_mode):
            snapshot[relative] = {
                "kind": "invalid",
                "expectedHead": object_id,
                "type": stat.S_IFMT(target_stat.st_mode),
            }
            continue
        git_marker = target / ".git"
        visible_entries = sorted(
            entry.name
            for entry in target.iterdir()
            if entry.name != ".git"
        )
        if git_marker.exists() or git_marker.is_symlink():
            git_dir_probe = git(
                target,
                "rev-parse",
                "--git-dir",
                check=False,
            )
            common_dir_probe = git(
                target,
                "rev-parse",
                "--git-common-dir",
                check=False,
            )
            if (
                git_dir_probe.returncode != 0
                or common_dir_probe.returncode != 0
            ):
                snapshot[relative] = {
                    "kind": "invalid-initialized-admin",
                    "expectedHead": object_id,
                    "gitDirExit": git_dir_probe.returncode,
                    "commonDirExit": common_dir_probe.returncode,
                }
                continue
            snapshot[relative] = {
                "kind": "initialized",
                "expectedHead": object_id,
                "actualHead": git(
                    target,
                    "rev-parse",
                    "--verify",
                    "HEAD",
                    check=False,
                ).stdout.strip(),
                "clean": (
                    git(
                        target,
                        "status",
                        "--short",
                        "--untracked-files=all",
                        check=False,
                    ).stdout
                    == ""
                ),
                "adminIdentity": git_admin_identity_snapshot(target),
                "worktreeControl": git_worktree_control_snapshot(target),
                "commonConfig": git_common_config_snapshot(target),
                "commonControl": git_common_control_snapshot(target),
                "commonWorktreeAdmin": git_common_worktree_admin_snapshot(
                    target
                ),
            }
        elif not visible_entries:
            snapshot[relative] = {
                "kind": "uninitialized-empty",
                "expectedHead": object_id,
                "directoryMode": target_stat.st_mode & 0o7777,
                "directoryDevice": target_stat.st_dev,
                "directoryInode": target_stat.st_ino,
                "directoryLinks": target_stat.st_nlink,
            }
        else:
            snapshot[relative] = {
                "kind": "invalid-uninitialized-content",
                "expectedHead": object_id,
                "entries": visible_entries,
            }
    return snapshot


def writer_validation_baseline(
    repo: pathlib.Path,
    *,
    revision: str,
) -> dict[str, object]:
    """Coordinator-owned post-create baseline for one assigned writer target."""
    return {
        "expected_git_admin_identity": git_admin_identity_snapshot(repo),
        "expected_worktree_control": git_worktree_control_snapshot(repo),
        "expected_common_config": git_common_config_snapshot(repo),
        "expected_common_control": git_common_control_snapshot(repo),
        "expected_common_worktree_admin": git_common_worktree_admin_snapshot(repo),
        "assigned_worktree_entries": (
            {entry}
            if (entry := assigned_common_worktree_entry(repo)) is not None
            else set()
        ),
        "coordinator_worktree_admin_additions": {},
        "expected_submodule_state": git_submodule_state_snapshot(
            repo,
            revision=revision,
        ),
        "authorized_submodule_transitions": set(),
    }


def git_tree_filesystem_errors(
    repo: pathlib.Path,
    *,
    expected_revision: str,
) -> list[str]:
    """Compare actual files to a commit tree without trusting index flags."""
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_revision):
        return ["expected tree revision must be a canonical commit id"]
    tree_output = git(
        repo,
        "ls-tree",
        "-rz",
        "--full-tree",
        expected_revision,
        check=False,
    )
    if tree_output.returncode != 0:
        return ["expected tree revision must resolve"]
    object_format = git(repo, "rev-parse", "--show-object-format").stdout.strip()
    expected_files: dict[str, tuple[str, str, str]] = {}
    expected_directories: set[str] = set()
    for record in tree_output.stdout.split("\0"):
        if not record:
            continue
        metadata, path = record.split("\t", 1)
        mode, object_type, object_id = metadata.split()
        expected_files[path] = (mode, object_type, object_id)
        parent = pathlib.PurePosixPath(path).parent
        while str(parent) != ".":
            expected_directories.add(f"{parent.as_posix()}/")
            parent = parent.parent
    errors = []
    submodule_paths = {
        relative
        for relative, (_, object_type, _) in expected_files.items()
        if object_type == "commit"
    }
    try:
        actual_snapshot = worktree_filesystem_snapshot(
            repo,
            opaque_directories=submodule_paths,
        )
    except ValueError as error:
        return [
            "filesystem snapshot budget exceeded"
            if str(error) == "filesystem snapshot budget exceeded"
            else "filesystem snapshot contains unsupported entry"
        ]
    actual_entries = set(actual_snapshot)
    allowed_entries = set(expected_files) | expected_directories | {"@root"}
    extras = sorted(actual_entries - allowed_entries)
    if extras:
        errors.append("worktree contains paths outside expected commit tree")
    file_mode_enabled = (
        git(
            repo,
            "config",
            "--bool",
            "core.filemode",
            check=False,
        ).stdout.strip()
        != "false"
    )
    symlinks_enabled = (
        git(
            repo,
            "config",
            "--bool",
            "core.symlinks",
            check=False,
        ).stdout.strip()
        != "false"
    )
    for relative, (mode, object_type, object_id) in expected_files.items():
        path = repo / relative
        if object_type == "commit":
            if path.is_symlink():
                errors.append("submodule does not match expected commit tree")
                continue
            if not path.exists():
                continue
            if not path.is_dir():
                errors.append("submodule does not match expected commit tree")
                continue
            git_marker = path / ".git"
            visible_entries = [
                entry
                for entry in path.iterdir()
                if entry.name != ".git"
            ]
            if not git_marker.exists() and not git_marker.is_symlink():
                if not visible_entries:
                    continue
                errors.append("submodule does not match expected commit tree")
                continue
            if (
                git(path, "rev-parse", "HEAD", check=False).stdout.strip()
                != object_id
                or git(
                    path,
                    "status",
                    "--short",
                    "--untracked-files=all",
                    check=False,
                ).stdout
            ):
                errors.append("submodule does not match expected commit tree")
            continue
        if object_type != "blob" or not path.exists() and not path.is_symlink():
            errors.append("worktree path is missing from expected commit tree")
            continue
        if mode == "120000" and symlinks_enabled:
            if not path.is_symlink():
                errors.append("worktree symlink mode differs from expected tree")
                continue
            content = os.readlink(path).encode()
            digest = hashlib.new(object_format)
            digest.update(f"blob {len(content)}\0".encode())
            digest.update(content)
            actual_object_id = digest.hexdigest()
        else:
            if path.is_symlink() or not path.is_file():
                errors.append("worktree file type differs from expected tree")
                continue
            path_stat = os.stat(path)
            if path_stat.st_nlink != 1:
                errors.append("worktree regular file must be single-link")
                continue
            executable = bool(path_stat.st_mode & 0o111)
            if file_mode_enabled and executable != (mode == "100755"):
                errors.append("worktree executable mode differs from expected tree")
            hashed = git(
                repo,
                "hash-object",
                f"--path={relative}",
                "--",
                str(path),
                check=False,
            )
            if hashed.returncode != 0:
                errors.append("worktree path clean filter could not be evaluated")
                continue
            actual_object_id = hashed.stdout.strip()
        if actual_object_id != object_id:
            errors.append("worktree bytes differ from expected commit tree")
    return errors


def fenced_ff_only_promotion(
    integration: pathlib.Path,
    *,
    project_root: pathlib.Path,
    mission_slug: str,
    owner_token: str,
    owner_generation: int,
    integration_target_ref: str,
    expected_old: str,
    transaction_head: str,
    lock_path: pathlib.Path,
) -> str:
    canonical_oid = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
    try:
        (
            registry_path,
            ownership_lock_path,
            canonical_lock_path,
        ) = canonical_mission_runtime_paths(project_root, mission_slug)
    except ValueError:
        return "unavailable"
    if (
        lock_path != canonical_lock_path
        or not isinstance(owner_token, str)
        or not owner_token
        or not isinstance(owner_generation, int)
        or isinstance(owner_generation, bool)
        or owner_generation < 1
        or local_state_path_errors(
            project_root,
            lock_path,
            leaf_kind="directory",
        )
        or local_state_path_errors(
            project_root,
            registry_path,
            leaf_kind="regular",
        )
        or local_state_path_errors(
            project_root,
            ownership_lock_path,
            leaf_kind="directory",
        )
    ):
        return "unavailable"

    def rollback() -> bool:
        restored_ref = git(
            integration,
            "update-ref",
            integration_target_ref,
            expected_old,
            transaction_head,
            check=False,
        )
        if restored_ref.returncode != 0:
            return False
        restored_tree = git(
            integration,
            "read-tree",
            "--reset",
            "-u",
            expected_old,
            check=False,
        )
        return (
            restored_tree.returncode == 0
            and git(
                integration,
                "symbolic-ref",
                "-q",
                "HEAD",
                check=False,
            ).stdout.strip()
            == integration_target_ref
            and git(
                integration,
                "rev-parse",
                "--verify",
                integration_target_ref,
            ).stdout.strip()
            == expected_old
            and git(integration, "rev-parse", "HEAD").stdout.strip() == expected_old
            and not git(integration, "status", "--short").stdout
        )

    try:
        ownership_lock_path.mkdir()
    except FileExistsError:
        return "ambiguous"
    except OSError:
        return "unavailable"
    try:
        lock_path.mkdir()
    except FileExistsError:
        ownership_lock_path.rmdir()
        return "ambiguous"
    except OSError:
        ownership_lock_path.rmdir()
        return "unavailable"
    owner_path = lock_path / "owner.json"
    try:
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            ownership = registry["ownership"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            return "unavailable"
        if (
            registry.get("missionId") != mission_slug
            or ownership.get("coordinatorThreadId") != owner_token
            or ownership.get("generation") != owner_generation
        ):
            return "stale"
        owner_record = {
            "missionId": mission_slug,
            "ownerToken": owner_token,
            "generation": owner_generation,
            "integrationTarget": integration_target_ref,
        }
        with owner_path.open("x", encoding="utf-8") as owner_file:
            json.dump(owner_record, owner_file, sort_keys=True)
            owner_file.write("\n")
            owner_file.flush()
            os.fsync(owner_file.fileno())
        if json.loads(owner_path.read_text(encoding="utf-8")) != owner_record:
            return "ambiguous"
        if (
            not isinstance(integration_target_ref, str)
            or not integration_target_ref.startswith("refs/heads/")
            or git(
                integration,
                "check-ref-format",
                integration_target_ref,
                check=False,
            ).returncode
            != 0
            or git(
                integration,
                "symbolic-ref",
                "-q",
                "HEAD",
                check=False,
            ).stdout.strip()
            != integration_target_ref
        ):
            return "rejected"
        if git(integration, "status", "--short").stdout:
            return "dirty"
        if (
            not canonical_oid.fullmatch(expected_old)
            or not canonical_oid.fullmatch(transaction_head)
            or transaction_head == expected_old
        ):
            return "rejected"
        for revision in (expected_old, transaction_head):
            if git(
                integration,
                "cat-file",
                "-e",
                f"{revision}^{{commit}}",
                check=False,
            ).returncode != 0:
                return "rejected"
        current = git(integration, "rev-parse", "HEAD").stdout.strip()
        target_current = git(
            integration,
            "rev-parse",
            "--verify",
            integration_target_ref,
            check=False,
        )
        if (
            target_current.returncode != 0
            or current != expected_old
            or target_current.stdout.strip() != expected_old
        ):
            return "stale"
        if git(
            integration,
            "merge-base",
            "--is-ancestor",
            expected_old,
            transaction_head,
            check=False,
        ).returncode != 0:
            return "rejected"
        promoted = git(
            integration,
            "update-ref",
            integration_target_ref,
            transaction_head,
            expected_old,
            check=False,
        )
        if promoted.returncode != 0:
            return "stale"
        synchronized = git(
            integration,
            "read-tree",
            "--reset",
            "-u",
            transaction_head,
            check=False,
        )
        if synchronized.returncode != 0:
            return "rejected" if rollback() else "ambiguous"
        if (
            git(
                integration,
                "symbolic-ref",
                "-q",
                "HEAD",
                check=False,
            ).stdout.strip()
            != integration_target_ref
            or git(integration, "rev-parse", "HEAD").stdout.strip()
            != transaction_head
            or git(
                integration,
                "rev-parse",
                "--verify",
                integration_target_ref,
            ).stdout.strip()
            != transaction_head
            or git(integration, "status", "--short").stdout
        ):
            return "rejected" if rollback() else "ambiguous"
        return "integrated"
    finally:
        if owner_path.exists():
            owner_path.unlink()
        lock_path.rmdir()
        ownership_lock_path.rmdir()


def check_activation_fixtures() -> None:
    fixtures = [
        ("$qtim-mission, запусти Approved план.", True, True, False, "AUTO-START"),
        (
            "$qtim-mission, запусти фичу отдельными backend и client задачами.",
            True,
            True,
            False,
            "AUTO-START",
        ),
        ("$qtim-mission, запусти сырой план.", False, True, False, "PREVIEW"),
        ("$qtim-mission, создай одну отдельную задачу Codex.", True, True, False, "PREVIEW"),
        ("$qtim-mission, реализуй только план.", True, True, False, "PREVIEW"),
        ("Что такое $qtim-mission?", True, True, False, "NOOP"),
        (
            "Можно ли создать несколько отдельных задач Codex и провести их как одну миссию? Ответь кратко.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Стоит ли создать несколько отдельных задач Codex и провести их как одну миссию? Поясни.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Как создать несколько отдельных задач Codex и провести их как одну миссию? Покажи шаги.",
            True,
            True,
            False,
            "NOOP",
        ),
        ("Не запускай $qtim-mission.", True, True, False, "NOOP"),
        ("Я не хочу запускать mission.", True, True, False, "NOOP"),
        ("Пример: $qtim-mission, запусти план.", True, True, False, "NOOP"),
        ('В документации: "$qtim-mission, запусти план".', True, True, False, "NOOP"),
        ("Возможно, здесь пригодится mission.", True, True, False, "RECOMMEND"),
        (
            "Создай отдельные задачи Codex и проведи их как одну миссию.",
            True,
            True,
            False,
            "AUTO-START",
        ),
        (
            "Создай несколько отдельных задач Codex, но не проводи их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай отдельные задачи Codex, но это не qtim-миссия.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько задач Codex, но без qtim-миссии.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько задач Codex, но не используй qtim-миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько задач Codex, но без использования qtim-миссии.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько задач Codex, но не пользуйся qtim-миссией.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько задач Codex, но qtim-миссию не используй.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex, исключая qtim-миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex, за исключением qtim-миссии.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            '"Создай отдельные задачи Codex и проведи их как одну миссию."',
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "`Создай отдельные задачи Codex и проведи их как одну миссию.`",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "‘Создай отдельные задачи Codex и проведи их как одну миссию.’",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "“Создай отдельные задачи Codex и проведи их как одну миссию.”",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "‹Создай отдельные задачи Codex и проведи их как одну миссию.›",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "„Создай отдельные задачи Codex и проведи их как одну миссию…”",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "‚Создай отдельные задачи Codex и проведи их как одну миссию.’",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "〝Создай отдельные задачи Codex и проведи их как одну миссию.〞",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "＂Создай отдельные задачи Codex и проведи их как одну миссию.＂",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "'Создай отдельные задачи Codex и проведи их как одну миссию.'",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "'' Создай отдельные задачи Codex и проведи их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "`` Создай отдельные задачи Codex и проведи их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "~~~\nСоздай отдельные задачи Codex и проведи их как одну миссию.\n~~~",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "~ Создай отдельные задачи Codex и проведи их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        ("Создай одну задачу в трекере.", True, True, False, "NOOP"),
        ("Запусти диалог с клиентом.", True, True, False, "NOOP"),
        ("Создай отдельную задачу Codex.", True, True, False, "NOOP"),
        ("Запусти отдельный диалог Codex.", True, True, False, "NOOP"),
        (
            "Создай план для нескольких отдельных задач Codex.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Подготовь план, как создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        (
            "Опиши, как создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        (
            "Сделай оценку: создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        (
            "Планирую создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Собираюсь создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Мне нужно понять, как создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        (
            "Хочу узнать, как создать несколько отдельных задач Codex и провести их как одну миссию.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        ("Не реализуй $qtim-mission.", True, True, False, "NOOP"),
        ("Не запусти $qtim-mission.", True, True, False, "NOOP"),
        ("Реализуй всё, кроме $qtim-mission.", True, True, False, "NOOP"),
        (
            "$qtim-mission, запусти Approved план, но не сейчас.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план завтра.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план через час.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план через 30 секунд.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план при условии зелёного QA.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission после релиза.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission, когда QA будет готово.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission по завершении релиза.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission, как только завершится релиз.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission через неделю.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission по готовности релиза.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Запусти $qtim-mission в следующем месяце.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            '"$qtim-mission, запусти Approved план."',
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, начни миссию, но только спланируй её.",
            True,
            True,
            False,
            "PREVIEW",
        ),
        ("$qtim-mission, preview, без создания задач.", True, True, False, "PREVIEW"),
        ("Запрещаю создавать задачи для mission.", True, True, False, "NOOP"),
        (
            "Создавать peer-задачи запрещено; $qtim-mission, запусти Approved план.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план; peer-задачи не создавать.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "$qtim-mission, запусти Approved план через 10 сек.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию через полчаса.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию через пару минут.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию через сутки.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию через четверть часа.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию в понедельник.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию вечером.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию после окончания текущей проверки.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию по окончании текущей проверки.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию, но отложи запуск.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию; запуск отложен.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию только после моего сигнала.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "Создай несколько отдельных задач Codex и проведи их как одну миссию, дождись моего сигнала.",
            True,
            True,
            False,
            "NOOP",
        ),
        (
            "После следующего подтверждения запусти mission.",
            True,
            True,
            False,
            "NOOP",
        ),
        ("Запускай предложенное", True, True, False, "NOOP"),
        ("Запускай предложенное", True, True, True, "AUTO-START"),
    ]
    for prompt, approved, preflight_ok, has_preview, expected in fixtures:
        actual = activation_mode(
            prompt,
            approved,
            preflight_ok,
            approved_preview_in_context=has_preview,
        )
        if actual != expected:
            fail(f"activation fixture {prompt!r}: expected {expected}, got {actual}")
    feature_handoff = activation_mode(
        "Запускай предложенное",
        approved=True,
        preflight_ok=True,
        feature_recommendation_in_context=True,
    )
    if feature_handoff != "PREVIEW":
        fail(
            "feature recommendation approval must enter PREVIEW, "
            f"got {feature_handoff}"
        )


def check_routing_fixtures() -> None:
    fixtures = [
        ((2, False, True, 1, False), "$qtim-mission"),
        ((2, False, False, 0, False), "$qtim-mission"),
        ((1, False, True, 0, False), "$qtim-mission"),
        ((1, True, False, 0, True), "$qtim-team-up"),
        ((1, False, False, 0, True), "$qtim-team-lazy"),
        ((1, False, False, 0, False), "direct"),
    ]
    for args, expected in fixtures:
        actual = recommend_workflow(*args)
        if actual != expected:
            fail(f"routing fixture {args}: expected {expected}, got {actual}")


def check_dag_and_state_fixtures() -> None:
    writer_preflight = dict(
        no_edits=True,
        detached_expected_base=True,
        clean_including_untracked=True,
        refs_unchanged=True,
    )
    if writer_start_outcome(
        followup_available=True,
        all_wave_targets_reconciled=False,
        coordinator_baselines_captured=False,
        exact_authorization_matches=False,
        **writer_preflight,
    ) != "preflight-ready":
        fail("no-edit writer preflight did not stop before baseline capture")
    if writer_start_outcome(
        followup_available=True,
        all_wave_targets_reconciled=True,
        coordinator_baselines_captured=True,
        exact_authorization_matches=True,
        **writer_preflight,
    ) != "running":
        fail("exact follow-up did not authorize a baselined writer wave")
    if writer_start_outcome(
        followup_available=False,
        all_wave_targets_reconciled=True,
        coordinator_baselines_captured=True,
        exact_authorization_matches=True,
        **writer_preflight,
    ) != "unavailable":
        fail("writer started without callable follow-up control")
    if writer_start_outcome(
        followup_available=True,
        no_edits=False,
        detached_expected_base=True,
        clean_including_untracked=True,
        refs_unchanged=True,
        all_wave_targets_reconciled=True,
        coordinator_baselines_captured=True,
        exact_authorization_matches=True,
    ) != "blocked":
        fail("writer edits before coordinator authorization were accepted")
    if writer_start_outcome(
        followup_available=True,
        all_wave_targets_reconciled=True,
        coordinator_baselines_captured=True,
        exact_authorization_matches=False,
        **writer_preflight,
    ) != "blocked":
        fail("mismatched writer follow-up authorization was accepted")

    valid_identity = dict(
        mission_slug="payments-contract",
        mission_id="payments-contract",
        node_ids=["analysis", "writer-a", "final-verification"],
        state_ref="refs/heads/codex/qtim-mission-state-payments-contract",
        integration_target_ref="refs/heads/codex/qtim-mission-payments-contract",
    )
    if mission_identity_errors(**valid_identity):
        fail("valid canonical mission identity was rejected")
    invalid_identity_fixtures = (
        {**valid_identity, "mission_slug": "../../outside"},
        {**valid_identity, "mission_id": "a:b"},
        {**valid_identity, "node_ids": ["c", "b:c"]},
        {**valid_identity, "node_ids": ["writer", "writer"]},
        {**valid_identity, "node_ids": [".git", "-writer"]},
        {**valid_identity, "mission_id": "Payments"},
        {**valid_identity, "mission_id": "x" * 65},
        {**valid_identity, "state_ref": "refs/heads/codex/../outside"},
        {**valid_identity, "integration_target_ref": "HEAD"},
        {
            **valid_identity,
            "integration_target_ref":
                "refs/heads/codex/qtim-mission-state-payments-contract",
        },
        {
            **valid_identity,
            "integration_target_ref": "refs/heads/codex",
        },
    )
    for invalid_identity in invalid_identity_fixtures:
        if not mission_identity_errors(**invalid_identity):
            fail(f"unsafe mission identity was accepted: {invalid_identity}")
    collision_left = mission_identity_errors(
        **{
            **valid_identity,
            "mission_id": "a:b",
            "node_ids": ["c"],
        }
    )
    collision_right = mission_identity_errors(
        **{
            **valid_identity,
            "mission_slug": "a",
            "mission_id": "a",
            "node_ids": ["b:c"],
            "state_ref": "refs/heads/codex/qtim-mission-state-a",
        }
    )
    if not collision_left or not collision_right:
        fail("colon-based mission marker collision was not rejected")
    graph = {"analysis": [], "writer": ["analysis"]}
    order = validate_dag(graph)
    if order != ["analysis", "writer"]:
        fail(f"invalid topological order: {order}")
    statuses = {"analysis": "pending", "writer": "pending"}
    edges = {("analysis", "writer"): "evidence"}
    if ready_nodes(graph, statuses, edges) != ["analysis"]:
        fail("initial DAG did not unlock only analysis")
    statuses["analysis"] = "succeeded"
    if ready_nodes(graph, statuses, edges):
        fail("succeeded incorrectly unlocked evidence edge")
    statuses["analysis"] = "validated"
    if ready_nodes(graph, statuses, edges) != ["writer"]:
        fail("validated evidence did not unlock writer")
    for invalid_edges in (
        {},
        {("analysis", "writer"): "integated"},
        {
            ("analysis", "writer"): "evidence",
            ("writer", "analysis"): "evidence",
        },
    ):
        try:
            ready_nodes(graph, statuses, invalid_edges)
        except ValueError:
            continue
        fail(f"missing/unknown/extra edge contract was accepted: {invalid_edges}")
    statuses["writer"] = "validated"
    if ready_nodes(graph, statuses, edges):
        fail("completed content DAG unexpectedly unlocked another content node")
    if terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis", "writer"},
        {"writer"},
        statuses,
        global_gates_green=True,
    ):
        fail("validated writer incorrectly unlocked terminal verifier")
    statuses["writer"] = "integrated"
    if terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis", "writer"},
        {"writer"},
        statuses,
        global_gates_green=False,
    ):
        fail("terminal verifier ignored red global gates")
    if not terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis", "writer"},
        {"writer"},
        statuses,
        global_gates_green=True,
    ):
        fail("integrated content DAG did not unlock terminal verifier")
    if terminal_verifier_ready(
        {"analysis", "writer"},
        set(),
        {"writer"},
        statuses,
        global_gates_green=True,
    ):
        fail("empty verifier dependency set was accepted")
    if terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis"},
        {"writer"},
        statuses,
        global_gates_green=True,
    ):
        fail("incomplete verifier dependency set was accepted")
    if terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis", "writer"},
        {"unknown-writer"},
        statuses,
        global_gates_green=True,
    ):
        fail("verifier accepted writer outside the content graph")
    if terminal_verifier_ready(
        {"analysis", "writer"},
        {"analysis", "writer"},
        {"writer"},
        statuses,
        global_gates_green="false",  # type: ignore[arg-type]
    ):
        fail("truthy-string global gate unlocked terminal verifier")

    for invalid in (
        {},
        {"single": []},
        {"a": ["b"], "b": ["a"]},
        {"a": ["missing"], "b": []},
        {"a:b": [], "c": []},
    ):
        try:
            validate_dag(invalid)
        except ValueError:
            continue
        fail(f"invalid DAG was accepted: {invalid}")

    for before, after, expected in (
        ("succeeded", "validated", True),
        ("succeeded", "integrated", False),
        ("validated", "integrated", True),
        ("integrated", "verified", True),
        ("running", "verified", False),
    ):
        if transition_allowed(before, after) != expected:
            fail(f"transition fixture {before}->{after} expected {expected}")


def check_windows_junction_fixtures() -> None:
    if os.name != "nt":
        fail("Windows junction fixtures require a Windows host")
    with tempfile.TemporaryDirectory(
        prefix="qtim-mission-junction-"
    ) as temporary_directory:
        root = pathlib.Path(temporary_directory)
        external = root / "external"
        project = root / "project"
        external.mkdir()
        project.mkdir()
        (external / "outside.txt").write_text("outside\n", encoding="utf-8")

        def create_junction(link: pathlib.Path, target: pathlib.Path) -> None:
            result = subprocess.run(
                [
                    "cmd",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(link),
                    str(target),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0 or not is_filesystem_junction(link):
                fail(
                    "Windows junction fixture could not create a real junction: "
                    f"{result.stderr.strip()}"
                )

        child_junction = project / "junction"
        create_junction(child_junction, external)
        if target_scope_errors(
            project,
            "junction/outside.txt",
        ) != ["scope must not cross symlink or junction components"]:
            fail("Windows child junction bypassed target containment")
        external_before = (external / "outside.txt").read_bytes()
        try:
            worktree_filesystem_snapshot(project)
        except ValueError:
            pass
        else:
            fail("Windows child junction was traversed by raw snapshot")
        if (external / "outside.txt").read_bytes() != external_before:
            fail("Windows child junction fixture changed external bytes")
        os.rmdir(child_junction)

        root_junction = root / "root-junction"
        create_junction(root_junction, external)
        try:
            worktree_filesystem_snapshot(root_junction)
        except ValueError:
            pass
        else:
            fail("Windows root junction was accepted as a real worktree")
        os.rmdir(root_junction)


def check_writer_and_lazy_fixtures() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        scope_fixture_root = pathlib.Path(temporary_directory)
        worktree_root = scope_fixture_root / "worktree"
        outside_root = scope_fixture_root / "outside"
        worktree_root.mkdir()
        outside_root.mkdir()
        (worktree_root / "safe").mkdir()
        os.symlink(outside_root, worktree_root / "linked-outside")
        if target_scope_errors(worktree_root, "safe/new-file.md"):
            fail("safe non-existing target scope was rejected")
        if target_scope_errors(
            worktree_root,
            "linked-outside/file.md",
        ) != ["scope must not cross symlink or junction components"]:
            fail("scope symlink escape was accepted")

    with tempfile.TemporaryDirectory(prefix="qtim-fs-budget-") as budget_temp:
        budget_root = pathlib.Path(budget_temp)
        for name in ("one.txt", "two.txt", "three.txt"):
            (budget_root / name).write_text(name, encoding="utf-8")
        try:
            worktree_filesystem_snapshot(
                budget_root,
                max_entries=2,
                max_bytes=1024,
            )
        except ValueError as error:
            if str(error) != "filesystem snapshot budget exceeded":
                fail(f"filesystem entry budget returned wrong error: {error}")
        else:
            fail("filesystem entry budget did not stop raw hashing")
        try:
            worktree_filesystem_snapshot(
                budget_root,
                max_entries=10,
                max_bytes=4,
            )
        except ValueError:
            pass
        else:
            fail("filesystem byte budget did not stop raw hashing")
        if hasattr(os, "mkfifo"):
            fifo_path = budget_root / "ignored.fifo"
            os.mkfifo(fifo_path)
            try:
                worktree_filesystem_snapshot(budget_root)
            except ValueError as error:
                if str(error) != "unsupported filesystem entry":
                    fail(f"special filesystem entry returned wrong error: {error}")
            else:
                fail("FIFO bypassed raw filesystem fail-closed guard")

    serialized_writer_graph = {"writer-a": [], "writer-b": ["writer-a"]}
    overlapping_writer_scopes = {
        "writer-a": ["plugins/qtim/reference/"],
        "writer-b": ["plugins/qtim/reference/a.md"],
    }
    if writer_scope_serialization_errors(
        graph=serialized_writer_graph,
        edge_contracts={("writer-a", "writer-b"): "integrated"},
        writer_scopes=overlapping_writer_scopes,
    ):
        fail("explicit integrated edge did not serialize overlapping writer scopes")
    for unsafe_edges in (
        {("writer-a", "writer-b"): "evidence"},
        {},
        {("writer-a", "writer-b"): "integated"},
    ):
        if not writer_scope_serialization_errors(
            graph=serialized_writer_graph,
            edge_contracts=unsafe_edges,
            writer_scopes=overlapping_writer_scopes,
        ):
            fail(f"writer overlap bypassed integrated edge contract: {unsafe_edges}")
    if (
        "overlapping writer scopes require a direct integrated edge"
        not in writer_scope_serialization_errors(
            graph={"writer-a": [], "writer-b": []},
            edge_contracts={},
            writer_scopes={
                "writer-a": ["src/Foo.ts"],
                "writer-b": ["src/foo.ts"],
            },
        )
    ):
        fail("case-folded writer scope collision was accepted")
    decomposed_scope = "docs/cafe\u0301.md"
    if parse_repo_scope(decomposed_scope)[1] != "noncanonical":
        fail("Unicode-normalization scope alias was accepted as canonical")

    writer_expected_base = "a" * 40
    writer_commit = "b" * 40
    writer_refs_before = {
        "refs/heads/codex/qtim-mission-example": writer_expected_base,
        "refs/heads/codex/qtim-mission-state-example": writer_expected_base,
        "refs/heads/main": "c" * 40,
        "refs/tags/release-fixture": "d" * 40,
        "refs/remotes/origin/main": "e" * 40,
        "refs/notes/review-fixture": "f" * 40,
    }
    writer_refs_after = dict(writer_refs_before)
    valid_writer = {
        "commit_count": 1,
        "merge_commit": False,
        "mission_base_is_ancestor": True,
        "parent_is_expected_base": True,
        "expected_base": writer_expected_base,
        "commit_sha": writer_commit,
        "refs_before": writer_refs_before,
        "refs_after": writer_refs_after,
        "common_git_config_unchanged": True,
        "common_git_control_unchanged": True,
        "git_admin_identity_unchanged": True,
        "frozen_worktree_control_unchanged": True,
        "common_worktree_admin_valid": True,
        "index_matches_commit_without_unsafe_flags": True,
        "submodule_state_valid": True,
        "head_is_commit": True,
        "detached_head": True,
        "worktree_clean": True,
        "tree_matches_commit": True,
        "target_scopes_contained": True,
        "changed": ["plugins/qtim/reference/a.md"],
        "scope": ["plugins/qtim/reference/a.md"],
        "gates_green": True,
    }

    def validate_writer(
        receipt: dict[str, object],
        authorized_updates: object | None = None,
    ) -> list[str]:
        return writer_receipt_errors(
            receipt,
            coordinator_authorized_ref_updates=(
                {} if authorized_updates is None else authorized_updates
            ),
            mission_slug="example",
            coordinator_owned_refs=(
                set()
                if authorized_updates is None
                else set(authorized_updates)
            ),
        )

    if validate_writer(valid_writer):
        fail("valid detached writer receipt was rejected")
    malicious_writer_refs = {
        **valid_writer,
        "refs_after": {
            **writer_refs_after,
            "refs/heads/codex/qtim-mission-example": writer_commit,
        },
    }
    if (
        "protected refs may only follow coordinator-authorized transitions"
        not in validate_writer(malicious_writer_refs)
    ):
        fail("writer mutation of Approved integration ref was accepted")
    deleted_state_ref = {
        **valid_writer,
        "refs_after": {
            ref_name: ref_oid
            for ref_name, ref_oid in writer_refs_after.items()
            if ref_name != "refs/heads/codex/qtim-mission-state-example"
        },
    }
    if (
        "protected refs may only follow coordinator-authorized transitions"
        not in validate_writer(deleted_state_ref)
    ):
        fail("writer deletion of mission state ref was accepted")
    state_checkpoint = "2" * 40
    checkpoint_refs = {
        **writer_refs_after,
        "refs/heads/codex/qtim-mission-state-example": state_checkpoint,
    }
    valid_checkpoint_writer = {
        **valid_writer,
        "refs_before": writer_refs_before,
        "refs_after": checkpoint_refs,
    }
    checkpoint_authorized_update = {
        "refs/heads/codex/qtim-mission-state-example": {
            "old": writer_expected_base,
            "new": state_checkpoint,
        },
    }
    if validate_writer(
        valid_checkpoint_writer,
        checkpoint_authorized_update,
    ):
        fail("journaled state checkpoint was rejected during detached writer")
    if (
        "protected refs may only follow coordinator-authorized transitions"
        not in validate_writer(valid_checkpoint_writer)
    ):
        fail("unjournaled state checkpoint was accepted")
    if (
        "coordinator-authorized ref transition must be canonical"
        not in validate_writer(
            valid_checkpoint_writer,
            {
                "refs/heads/codex/qtim-mission-state-example": {
                    "old": "3" * 40,
                    "new": state_checkpoint,
                },
            },
        )
    ):
        fail("wrong coordinator transition baseline was accepted")
    self_authorized_foreign_ref = {
        **valid_writer,
        "refs_after": {
            **writer_refs_after,
            "refs/heads/main": writer_commit,
        },
        "coordinator_authorized_ref_updates": {
            "refs/heads/main": {
                "old": writer_refs_before["refs/heads/main"],
                "new": writer_commit,
            },
        },
    }
    if (
        "protected refs may only follow coordinator-authorized transitions"
        not in validate_writer(self_authorized_foreign_ref)
    ):
        fail("worker self-authorized a foreign ref transition")
    if (
        "protected ref snapshot proof must be canonical"
        not in validate_writer(
            self_authorized_foreign_ref,
            self_authorized_foreign_ref[
                "coordinator_authorized_ref_updates"
            ],
        )
    ):
        fail("coordinator ledger authorized a foreign ref transition")
    state_ref_name = "refs/heads/codex/qtim-mission-state-example"
    if (
        "coordinator-authorized ref transition must be canonical"
        not in protected_ref_snapshot_errors(
            refs_before=writer_refs_before,
            refs_after={
                ref_name: ref_oid
                for ref_name, ref_oid in writer_refs_before.items()
                if ref_name != state_ref_name
            },
            authorized_updates={
                state_ref_name: {
                    "old": writer_expected_base,
                    "new": None,
                },
            },
            mission_slug="example",
            coordinator_owned_refs={state_ref_name},
        )
    ):
        fail("durable mission state ref deletion was accepted")
    if "worker must preserve common git config" not in validate_writer(
        {**valid_writer, "common_git_config_unchanged": False}
    ):
        fail("writer shared git config mutation was accepted")
    if "worker must preserve common git control files" not in validate_writer(
        {**valid_writer, "common_git_control_unchanged": False}
    ):
        fail("writer shared git control mutation was accepted")
    for malformed_writer_postcondition, expected_error in (
        ("head_is_commit", "writer HEAD must equal commit"),
        ("detached_head", "writer HEAD must remain detached"),
        (
            "worktree_clean",
            "writer worktree must be clean including untracked files",
        ),
        ("tree_matches_commit", "writer filesystem must match commit tree"),
        (
            "git_admin_identity_unchanged",
            "worker must preserve assigned Git admin identity",
        ),
        (
            "frozen_worktree_control_unchanged",
            "worker must preserve frozen per-worktree Git control",
        ),
        (
            "common_worktree_admin_valid",
            "worker common worktree admin must match coordinator journal",
        ),
        (
            "index_matches_commit_without_unsafe_flags",
            "worker index must match commit without unsafe flags",
        ),
        (
            "submodule_state_valid",
            "worker submodule state must match coordinator baseline",
        ),
        (
            "target_scopes_contained",
            "writer scopes must resolve inside exact worktree",
        ),
        ("gates_green", "node gates must be green"),
        ("mission_base_is_ancestor", "mission base must be ancestor"),
        ("parent_is_expected_base", "commit parent must equal expected base"),
    ):
        if expected_error not in validate_writer(
            {**valid_writer, malformed_writer_postcondition: "false"}
        ):
            fail(
                "truthy-string writer gate was accepted: "
                f"{malformed_writer_postcondition}"
            )
    invalid_writer = {**valid_writer, "changed": ["README.md"], "commit_count": 2}
    if len(validate_writer(invalid_writer)) != 2:
        fail("out-of-scope multi-commit writer was not rejected")
    stale_parent_writer = {**valid_writer, "parent_is_expected_base": False}
    if validate_writer(stale_parent_writer) != [
        "commit parent must equal expected base"
    ]:
        fail("stale-parent writer was not rejected independently")
    valid_directory_writer = {
        **valid_writer,
        "scope": ["plugins/qtim/reference/"],
    }
    if validate_writer(valid_directory_writer):
        fail("valid canonical writer directory scope was rejected")
    writer_scope_aliases = (
        ("./plugins/qtim/reference/a.md", "writer scope must be canonical"),
        ("../plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("C:plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("plugins\\qtim\\reference\\a.md", "writer scope must be a safe repo-relative path"),
        ("file:/plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("git+ssh:repo/path", "writer scope must be a safe repo-relative path"),
        ("~/plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("~reviewer/plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("$HOME/plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("%USERPROFILE%/plugins/qtim/reference/a.md", "writer scope must be a safe repo-relative path"),
        ("plugins/**/a.md", "writer scope must be a safe repo-relative path"),
        ("plugins/+(qtim)/a.md", "writer scope must be a safe repo-relative path"),
        ("plugins/qtim/a.md:stream", "writer scope must be a safe repo-relative path"),
        ("plugins/\nreference/a.md", "writer scope must be a safe repo-relative path"),
        ("plugins/\u0085reference/a.md", "writer scope must be a safe repo-relative path"),
        (".git/refs/heads/main", "writer scope must be a safe repo-relative path"),
        (".GIT/config", "writer scope must be a safe repo-relative path"),
        (".git./config", "writer scope must be a safe repo-relative path"),
        ("NUL/report.md", "writer scope must be a safe repo-relative path"),
        ("docs/COM1.txt", "writer scope must be a safe repo-relative path"),
        ("-option-like-path", "writer scope must be a safe repo-relative path"),
        (" plugins/qtim/reference/a.md", "writer scope must be canonical"),
        (None, "writer scope must be a safe repo-relative path"),
    )
    for unsafe_writer_scope, expected_error in writer_scope_aliases:
        alias_errors = validate_writer(
            {**valid_writer, "scope": [unsafe_writer_scope]}
        )
        if expected_error not in alias_errors:
            fail(
                "writer scope alias was not rejected: "
                f"{unsafe_writer_scope!r} -> {alias_errors}"
            )
    malformed_writer_errors = validate_writer(
        {
            **valid_writer,
            "commit_count": True,
            "scope": "plugins/qtim/reference/a.md",
            "changed": "plugins/qtim/reference/a.md",
        }
    )
    if not {
        "exactly one commit required",
        "writer scope must be a list",
        "changed paths must be a list",
        "writer scope required",
        "writer must change at least one path",
    } <= set(malformed_writer_errors):
        fail(f"malformed writer receipt was not fail-closed: {malformed_writer_errors}")

    valid_lazy = {
        "status": "SUCCEEDED",
        "roles": [
            {
                "name": "qtim-architect",
                "responsibility": "contract",
                "output": "report",
                "write_policy": "writer",
                "write_scopes": ["docs/architecture/"],
            },
            {
                "name": "qtim-testing",
                "responsibility": "gates",
                "output": "evidence",
                "write_policy": "writer",
                "write_scopes": ["docs/testing/"],
            },
        ],
        "approved_roles": ["qtim-architect", "qtim-testing"],
        "descendants_created": False,
        "feedback_loop": False,
        "product_fork": False,
        "escalation": "",
        "lead_checked_results": True,
    }
    expected_lazy_contracts = {
        "qtim-architect": {
            "responsibility": "contract",
            "output": "report",
            "write_policy": "writer",
            "write_scopes": ["docs/architecture/"],
            "read_scopes": [],
        },
        "qtim-testing": {
            "responsibility": "gates",
            "output": "evidence",
            "write_policy": "writer",
            "write_scopes": ["docs/testing/"],
            "read_scopes": [],
        },
    }

    def validate_lazy(receipt: dict[str, object]) -> list[str]:
        return lazy_receipt_errors(
            receipt,
            expected_role_contracts=expected_lazy_contracts,
            expected_node_write_scopes=["docs/"],
        )

    if validate_lazy(valid_lazy):
        fail("valid aggregated lazy receipt was rejected")
    case_alias_lazy = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["docs/Foo/"],
            },
            {
                **valid_lazy["roles"][1],
                "write_scopes": ["docs/foo/"],
            },
        ],
    }
    case_alias_contracts = {
        "qtim-architect": {
            **expected_lazy_contracts["qtim-architect"],
            "write_scopes": ["docs/Foo/"],
        },
        "qtim-testing": {
            **expected_lazy_contracts["qtim-testing"],
            "write_scopes": ["docs/foo/"],
        },
    }
    if (
        "local write scopes overlap"
        not in lazy_receipt_errors(
            case_alias_lazy,
            expected_role_contracts=case_alias_contracts,
            expected_node_write_scopes=["docs/"],
        )
    ):
        fail("case-folded lazy scope collision was accepted")
    escaped_lazy_scope = {
        **valid_lazy,
        "roles": [
            valid_lazy["roles"][0],
            {
                **valid_lazy["roles"][1],
                "write_scopes": [
                    "plugins/qtim/.codex-plugin/plugin.json",
                ],
            },
        ],
    }
    if "role write scope exceeds coordinator contract" not in validate_lazy(
        escaped_lazy_scope
    ):
        fail("lazy role escaped coordinator-owned role/node scope contract")
    repurposed_lazy_role = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "responsibility": "unapproved implementation",
            },
            valid_lazy["roles"][1],
        ],
    }
    if (
        "role responsibility/output differs from coordinator contract"
        not in validate_lazy(repurposed_lazy_role)
    ):
        fail("approved lazy role was repurposed outside coordinator contract")
    if (
        "receipt approved roles differ from coordinator contract"
        not in validate_lazy(
            {
                **valid_lazy,
                "approved_roles": [
                    "qtim-architect",
                    "qtim-testing",
                    "qtim-product",
                ],
            }
        )
    ):
        fail("self-reported lazy role allowlist overrode coordinator contract")
    valid_read_only_lazy = {
        **valid_lazy,
        "roles": [
            {
                "name": "qtim-architect",
                "responsibility": "read-only review",
                "output": "report",
                "write_policy": "read-only",
                "write_scopes": [],
                "read_scopes": ["docs/architecture/"],
            },
        ],
        "approved_roles": ["qtim-architect"],
    }
    if lazy_receipt_errors(
        valid_read_only_lazy,
        expected_role_contracts={
            "qtim-architect": {
                "responsibility": "read-only review",
                "output": "report",
                "write_policy": "read-only",
                "write_scopes": [],
                "read_scopes": ["docs/architecture/"],
            },
        },
        expected_node_write_scopes=[],
    ):
        fail("valid explicit read-only lazy receipt was rejected")
    invalid_lazy = {
        **valid_lazy,
        "roles": [
            *valid_lazy["roles"],
            {
                "name": "qtim-product",
                "responsibility": "unapproved fork",
                "output": "decision",
                "write_policy": "writer",
                "write_scopes": ["./docs/architecture/decisions/"],
            },
        ],
        "descendants_created": True,
        "feedback_loop": True,
        "product_fork": True,
        "escalation": "",
    }
    invalid_lazy_errors = validate_lazy(invalid_lazy)
    expected_lazy_errors = {
        "third-level descendants forbidden",
        "role outside approved allowlist",
        "write scope must be canonical",
        "role write scope exceeds coordinator contract",
        "local write scopes overlap",
        "mission escalation requires ESCALATION_REQUEST",
        "mission escalation must return BLOCKED",
    }
    if set(invalid_lazy_errors) != expected_lazy_errors:
        fail(f"lazy authorization/escalation guards did not fire: {invalid_lazy_errors}")
    unsafe_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["../outside-repository"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(unsafe_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("unsafe lazy write scope was not rejected independently")
    drive_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["C:\\repository\\docs"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(drive_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("drive-qualified lazy write scope was not rejected independently")
    drive_relative_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["C:repository\\docs"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(drive_relative_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("drive-relative lazy write scope was not rejected independently")
    backslash_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["docs\\architecture"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(backslash_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("backslash lazy write scope was not rejected independently")
    uri_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["file:/repository/docs"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(uri_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("URI-like lazy write scope was not rejected independently")
    scheme_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": ["git+ssh:repo/path"],
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(scheme_scope) != [
        "write scope must be a safe repo-relative path"
    ]:
        fail("scheme-prefixed lazy write scope was not rejected independently")
    duplicate_role = {
        **valid_lazy,
        "roles": [valid_lazy["roles"][0], valid_lazy["roles"][0]],
    }
    if validate_lazy(duplicate_role) != ["duplicate lazy role"]:
        fail("duplicate lazy role was not rejected independently")
    succeeded_escalation = {
        **valid_lazy,
        "feedback_loop": True,
        "escalation": "ESCALATION_REQUEST",
    }
    if validate_lazy(succeeded_escalation) != [
        "mission escalation must return BLOCKED"
    ]:
        fail("SUCCEEDED lazy escalation was accepted for validation")
    marker_only_escalation = {
        **valid_lazy,
        "escalation": "ESCALATION_REQUEST",
    }
    if validate_lazy(marker_only_escalation) != [
        "mission escalation must return BLOCKED"
    ]:
        fail("marker-only SUCCEEDED lazy escalation was accepted")
    blocked_escalation = {
        **succeeded_escalation,
        "status": "BLOCKED",
    }
    if validate_lazy(blocked_escalation) != [
        "BLOCKED lazy receipt cannot validate"
    ]:
        fail("BLOCKED lazy escalation incorrectly unlocked validation")
    if validate_lazy({**valid_lazy, "roles": "qtim-testing"}) != [
        "lazy roles must be a list of objects"
    ]:
        fail("malformed lazy role collection was not rejected")
    malformed_local_scopes = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": "docs/architecture/",
            },
            valid_lazy["roles"][1],
        ],
    }
    if validate_lazy(malformed_local_scopes) != [
        "local write scopes must be a list"
    ]:
        fail("malformed local scope collection was not rejected")
    falsey_local_scope = {
        **valid_lazy,
        "roles": [
            {
                **valid_lazy["roles"][0],
                "write_scopes": [None],
            },
            valid_lazy["roles"][1],
        ],
    }
    falsey_errors = validate_lazy(falsey_local_scope)
    if "write scope must be a safe repo-relative path" not in falsey_errors:
        fail("falsey lazy write scope was silently discarded")
    implicit_read_only = {
        **valid_read_only_lazy,
        "roles": [
            {
                **valid_read_only_lazy["roles"][0],
                "write_policy": "writer",
            },
        ],
    }
    if "writer role needs a write scope" not in lazy_receipt_errors(
        implicit_read_only,
        expected_role_contracts={
            "qtim-architect": {
                "responsibility": "read-only review",
                "output": "report",
                "write_policy": "writer",
                "write_scopes": ["docs/architecture/"],
                "read_scopes": [],
            },
        },
        expected_node_write_scopes=["docs/"],
    ):
        fail("empty write scopes silently implied read-only policy")
    blocked_new_role_without_marker = {
        **valid_lazy,
        "status": "BLOCKED",
        "roles": [
            *valid_lazy["roles"],
            {
                "name": "qtim-product",
                "responsibility": "unapproved fork",
                "output": "decision",
                "write_policy": "read-only",
                "write_scopes": [],
                "read_scopes": ["docs/product/"],
            },
        ],
    }
    blocked_new_role_errors = validate_lazy(blocked_new_role_without_marker)
    if "mission escalation requires ESCALATION_REQUEST" not in blocked_new_role_errors:
        fail("BLOCKED new-role request omitted mandatory escalation marker")
    blocked_overlap_without_marker = {
        **valid_lazy,
        "status": "BLOCKED",
        "roles": [
            valid_lazy["roles"][0],
            {
                **valid_lazy["roles"][1],
                "write_scopes": ["docs/architecture/reports/"],
            },
        ],
    }
    blocked_overlap_errors = validate_lazy(blocked_overlap_without_marker)
    if "mission escalation requires ESCALATION_REQUEST" not in blocked_overlap_errors:
        fail("BLOCKED scope-overlap request omitted mandatory escalation marker")
    for malformed_lazy_field, expected_error in (
        ("lead_checked_results", "node lead must check local results"),
        ("descendants_created", "third-level descendants forbidden"),
    ):
        if expected_error not in validate_lazy(
            {**valid_lazy, malformed_lazy_field: "false"}
        ):
            fail(f"truthy-string lazy gate was accepted: {malformed_lazy_field}")


def check_recovery_fixtures() -> None:
    verdict_fixtures = (
        ("verdict: APPROVED\n", "APPROVED"),
        ("verdict: NOT APPROVED\n", "NOT APPROVED"),
        ("verdict: NOT APPROVED\nverdict: APPROVED\n", "APPROVED"),
        ("verdict: APPROVED\nverdict: NOT APPROVED\n", "NOT APPROVED"),
        ("verdict: APPROVED-ish\n", None),
        ("note: verdict: APPROVED\n", None),
        ("verdict: approved\n", None),
        ("    verdict: APPROVED\n", None),
        ("verdict:\tAPPROVED\n", None),
        ("verdict:    APPROVED\n", None),
    )
    for body, expected_verdict in verdict_fixtures:
        actual_verdict = exact_verification_verdict(body)
        if actual_verdict != expected_verdict:
            fail(
                "exact verdict parser mismatch: "
                f"{body!r} -> {actual_verdict!r}, expected {expected_verdict!r}"
            )
    for malformed_evidence_value in ("false", 1, [], {}):
        if (
            mission_terminal_status(
                durable_status="Done",
                final_verdict="APPROVED",
                evidence_delivered=malformed_evidence_value,  # type: ignore[arg-type]
                evidence_matches_checkpoint=malformed_evidence_value,  # type: ignore[arg-type]
                done_checkpoint_clean=malformed_evidence_value,  # type: ignore[arg-type]
                done_checkpoint_matches_delivery=malformed_evidence_value,  # type: ignore[arg-type]
            )
            == "Done"
        ):
            fail("malformed truthy evidence predicate produced terminal Done")

    exact_identity = dict(
        project_matches=True,
        marker_matches=True,
        attempt_matches=True,
        host_matches=True,
        source_matches=True,
        base_matches=True,
    )
    fixtures = [
        (dict(tool_available=True, candidates=1, **exact_identity), "live"),
        (
            dict(
                tool_available=True,
                candidates=0,
                pending_creation=True,
                **exact_identity,
            ),
            "pending",
        ),
        (dict(tool_available=True, candidates=0, **exact_identity), "orphan"),
        (dict(tool_available=True, candidates=2, **exact_identity), "ambiguous"),
        (
            dict(
                tool_available=True,
                candidates=1,
                portable_state_clean=False,
                **exact_identity,
            ),
            "blocked",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                state_sequence_valid=False,
                **exact_identity,
            ),
            "blocked",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "project_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "marker_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "attempt_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "host_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "source_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=True,
                candidates=1,
                **{**exact_identity, "base_matches": False},
            ),
            "stale",
        ),
        (
            dict(
                tool_available=False,
                candidates=0,
                **{key: False for key in exact_identity},
            ),
            "unavailable",
        ),
    ]
    for kwargs, expected in fixtures:
        actual = classify_resume(**kwargs)
        if actual != expected:
            fail(f"recovery fixture {kwargs}: expected {expected}, got {actual}")

    ownership_fixtures = [
        (
            dict(
                tool_available=True,
                same_coordinator=True,
                previous_coordinator_running=True,
                previous_coordinator_confirmed=True,
                explicit_resume=False,
                generation_matches=True,
            ),
            "owned",
        ),
        (
            dict(
                tool_available=True,
                same_coordinator=False,
                previous_coordinator_running=False,
                previous_coordinator_confirmed=True,
                explicit_resume=True,
                generation_matches=True,
            ),
            "takeover",
        ),
        (
            dict(
                tool_available=True,
                same_coordinator=False,
                previous_coordinator_running=True,
                previous_coordinator_confirmed=True,
                explicit_resume=True,
                generation_matches=True,
            ),
            "ambiguous",
        ),
        (
            dict(
                tool_available=True,
                same_coordinator=False,
                previous_coordinator_running=False,
                previous_coordinator_confirmed=True,
                explicit_resume=True,
                generation_matches=False,
            ),
            "stale",
        ),
        (
            dict(
                tool_available=False,
                same_coordinator=False,
                previous_coordinator_running=False,
                previous_coordinator_confirmed=False,
                explicit_resume=True,
                generation_matches=True,
            ),
            "unavailable",
        ),
    ]
    for kwargs, expected in ownership_fixtures:
        actual = classify_coordinator_ownership(**kwargs)
        if actual != expected:
            fail(f"coordinator ownership fixture {kwargs}: expected {expected}, got {actual}")

    with tempfile.TemporaryDirectory(prefix="qtim-mission-owner-") as temp_dir:
        root = pathlib.Path(temp_dir)
        first_run_root = root / "first-run"
        first_run_root.mkdir()
        if (
            atomic_registry_initialize_fixture(
                first_run_root,
                "first-mission",
                coordinator_thread_id="coordinator",
                host_id="local",
            )
            != "owned"
        ):
            fail("first-run registry initialization did not publish ownership")
        first_registry, _, _ = canonical_mission_runtime_paths(
            first_run_root,
            "first-mission",
        )
        first_registry_before = first_registry.read_bytes()
        if (
            atomic_registry_initialize_fixture(
                first_run_root,
                "first-mission",
                coordinator_thread_id="other",
                host_id="local",
            )
            != "ambiguous"
            or first_registry.read_bytes() != first_registry_before
        ):
            fail("duplicate first-run registry initialization clobbered ownership")
        collision_registry, _, _ = canonical_mission_runtime_paths(
            first_run_root,
            "collision",
        )
        collision_temporary = collision_registry.with_name(
            f"{collision_registry.name}.init.tmp"
        )
        collision_temporary.write_bytes(b"foreign temporary state\n")
        if (
            atomic_registry_initialize_fixture(
                first_run_root,
                "collision",
                coordinator_thread_id="coordinator",
                host_id="local",
            )
            != "ambiguous"
            or collision_registry.exists()
            or collision_temporary.read_bytes() != b"foreign temporary state\n"
        ):
            fail("first-run registry initialization clobbered adjacent state")

        portable_first_run_root = root / "portable-first-run"
        portable_first_run_root.mkdir()
        portable_first_run_target = (
            portable_first_run_root / "memory" / "missions" / "first-mission"
        )
        if initialize_local_state_parents_fixture(
            portable_first_run_root,
            portable_first_run_target,
            leaf_kind="directory",
            mode=0o755,
        ):
            fail("first-run portable hierarchy was not created safely")
        portable_target_stat = os.lstat(portable_first_run_target)
        if (
            not stat.S_ISDIR(portable_target_stat.st_mode)
            or stat.S_ISLNK(portable_target_stat.st_mode)
        ):
            fail("first-run portable hierarchy leaf is not a real directory")
        portable_target_identity = (
            portable_target_stat.st_dev,
            portable_target_stat.st_ino,
        )
        if initialize_local_state_parents_fixture(
            portable_first_run_root,
            portable_first_run_target,
            leaf_kind="directory",
            mode=0o755,
        ):
            fail("idempotent portable hierarchy revalidation was rejected")
        repeated_portable_stat = os.lstat(portable_first_run_target)
        if (
            repeated_portable_stat.st_dev,
            repeated_portable_stat.st_ino,
        ) != portable_target_identity:
            fail("portable hierarchy revalidation replaced the existing leaf")
        portable_collision_root = root / "portable-collision"
        portable_collision_root.mkdir()
        portable_collision_memory = portable_collision_root / "memory"
        portable_collision_memory.write_bytes(b"foreign state\n")
        if (
            not initialize_local_state_parents_fixture(
                portable_collision_root,
                portable_collision_root / "memory" / "missions" / "fixture",
                leaf_kind="directory",
                mode=0o755,
            )
            or portable_collision_memory.read_bytes() != b"foreign state\n"
        ):
            fail("portable first-run collision replaced a foreign component")

        missions_directory = root / ".codex" / "qtim-runtime" / "missions"
        missions_directory.mkdir(parents=True)
        registry_path, lock_path, _ = canonical_mission_runtime_paths(
            root,
            "fixture",
        )
        registry_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "missionId": "fixture",
                    "ownership": {
                        "coordinatorThreadId": "old",
                        "hostId": "local",
                        "generation": 1,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        lock_path.mkdir()
        if (
            atomic_takeover_fixture(
                root,
                "fixture",
                expected_generation=1,
                new_thread_id="new",
                new_host_id="local",
            )
            != "ambiguous"
        ):
            fail("concurrent coordinator ownership lock was not rejected")
        lock_path.rmdir()
        temporary_path = registry_path.with_suffix(".json.tmp")
        temporary_path.write_bytes(b"foreign temporary state\n")
        registry_before = registry_path.read_bytes()
        if (
            atomic_takeover_fixture(
                root,
                "fixture",
                expected_generation=1,
                new_thread_id="new",
                new_host_id="local",
            )
            != "ambiguous"
            or temporary_path.read_bytes() != b"foreign temporary state\n"
            or registry_path.read_bytes() != registry_before
        ):
            fail("takeover removed or changed a foreign adjacent temporary file")
        temporary_path.unlink()
        if (
            atomic_takeover_fixture(
                root,
                "fixture",
                expected_generation=1,
                new_thread_id="new",
                new_host_id="local",
            )
            != "takeover"
        ):
            fail("atomic coordinator takeover fixture did not succeed")
        updated = json.loads(registry_path.read_text(encoding="utf-8"))["ownership"]
        if updated != {
            "coordinatorThreadId": "new",
            "hostId": "local",
            "generation": 2,
        }:
            fail(f"atomic coordinator takeover wrote invalid ownership: {updated}")
        if (
            atomic_takeover_fixture(
                root,
                "fixture",
                expected_generation=1,
                new_thread_id="stale",
                new_host_id="local",
            )
            != "stale"
        ):
            fail("stale coordinator generation was not rejected under ownership lock")
        symlink_project = root / "symlink-project"
        external_runtime = root / "external-runtime"
        symlink_project.mkdir()
        external_runtime.mkdir()
        (symlink_project / ".codex").mkdir()
        os.symlink(
            external_runtime,
            symlink_project / ".codex" / "qtim-runtime",
            target_is_directory=True,
        )
        external_before = list(external_runtime.iterdir())
        if (
            atomic_registry_initialize_fixture(
                symlink_project,
                "fixture",
                coordinator_thread_id="escaped",
                host_id="local",
            )
            != "unavailable"
            or list(external_runtime.iterdir()) != external_before
        ):
            fail("symlinked runtime path allowed an external initialization write")
        portable_root = root / "portable-project"
        portable_external = root / "portable-external"
        portable_root.mkdir()
        portable_external.mkdir()
        os.symlink(
            portable_external,
            portable_root / "memory",
            target_is_directory=True,
        )
        portable_target = portable_root / "memory" / "missions" / "fixture"
        if not local_state_path_errors(
            portable_root,
            portable_target,
            leaf_kind="directory",
        ):
            fail("symlinked portable evidence path bypassed containment guard")


def check_git_integration_fixture() -> None:
    """Exercise transactional integration, promotion, red gate and conflict recovery."""
    with tempfile.TemporaryDirectory(prefix="qtim-mission-no-reflog-") as no_log_temp:
        no_log_root = pathlib.Path(no_log_temp)
        no_log_source = no_log_root / "source"
        no_log_writer = no_log_root / "writer"
        no_log_source.mkdir()
        git(no_log_source, "init", "-q")
        git(no_log_source, "config", "user.name", "qtim no-reflog fixture")
        git(
            no_log_source,
            "config",
            "user.email",
            "qtim-no-reflog@example.invalid",
        )
        git(no_log_source, "config", "core.logAllRefUpdates", "false")
        (no_log_source / "base.txt").write_text("base\n", encoding="utf-8")
        git(no_log_source, "add", "base.txt")
        git(no_log_source, "commit", "-q", "-m", "base")
        no_log_base = git(no_log_source, "rev-parse", "HEAD").stdout.strip()
        git(
            no_log_source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(no_log_writer),
            no_log_base,
        )
        no_log_baseline = writer_validation_baseline(
            no_log_writer,
            revision=no_log_base,
        )
        (no_log_writer / "writer.txt").write_text("writer\n", encoding="utf-8")
        git(no_log_writer, "add", "writer.txt")
        git(no_log_writer, "commit", "-q", "-m", "writer")
        no_log_commit = git(no_log_writer, "rev-parse", "HEAD").stdout.strip()
        no_log_git_dir = pathlib.Path(
            git(no_log_writer, "rev-parse", "--git-dir").stdout.strip()
        )
        if not no_log_git_dir.is_absolute():
            no_log_git_dir = pathlib.Path(
                os.path.abspath(no_log_writer / no_log_git_dir)
            )
        if (no_log_git_dir / "logs").exists():
            fail("no-reflog writer fixture unexpectedly created logs directory")
        if git_writer_target_errors(
            no_log_writer,
            expected_commit=no_log_commit,
            **no_log_baseline,
        ):
            fail("valid no-reflog linked writer target was rejected")

    with tempfile.TemporaryDirectory(prefix="qtim-mission-crlf-") as crlf_temp:
        crlf_repo = pathlib.Path(crlf_temp)
        git(crlf_repo, "init", "-q")
        git(crlf_repo, "config", "user.name", "qtim crlf fixture")
        git(crlf_repo, "config", "user.email", "qtim-crlf@example.invalid")
        (crlf_repo / ".gitattributes").write_text(
            "*.txt text eol=crlf\n",
            encoding="utf-8",
        )
        (crlf_repo / "portable.txt").write_text("one\ntwo\n", encoding="utf-8")
        git(crlf_repo, "add", ".gitattributes", "portable.txt")
        git(crlf_repo, "commit", "-q", "-m", "crlf fixture")
        crlf_revision = git(crlf_repo, "rev-parse", "HEAD").stdout.strip()
        (crlf_repo / "portable.txt").unlink()
        git(crlf_repo, "checkout", "--", "portable.txt")
        git(crlf_repo, "checkout", "-q", "--detach", crlf_revision)
        if b"\r\n" not in (crlf_repo / "portable.txt").read_bytes():
            fail("CRLF fixture did not materialize eol=crlf")
        crlf_writer_baseline = writer_validation_baseline(
            crlf_repo,
            revision=crlf_revision,
        )
        if git_writer_target_errors(
            crlf_repo,
            expected_commit=crlf_revision,
            **crlf_writer_baseline,
        ):
            fail("clean CRLF-filtered writer target was rejected")

    with tempfile.TemporaryDirectory(prefix="qtim-mission-submodule-") as sub_temp:
        sub_root = pathlib.Path(sub_temp)
        sub_repo = sub_root / "sub"
        super_repo = sub_root / "super"
        clone_repo = sub_root / "clone"
        sub_repo.mkdir()
        super_repo.mkdir()
        for repo, name in ((sub_repo, "sub"), (super_repo, "super")):
            git(repo, "init", "-q")
            git(repo, "config", "user.name", f"qtim {name} fixture")
            git(repo, "config", "user.email", f"qtim-{name}@example.invalid")
        (sub_repo / "component.txt").write_text("component\n", encoding="utf-8")
        git(sub_repo, "add", "component.txt")
        git(sub_repo, "commit", "-q", "-m", "submodule base")
        expected_sub_revision = git(
            sub_repo,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        (super_repo / "root.txt").write_text("root\n", encoding="utf-8")
        git(super_repo, "add", "root.txt")
        git(super_repo, "commit", "-q", "-m", "super base")
        git(
            super_repo,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-q",
            str(sub_repo),
            "deps/sub",
        )
        git(super_repo, "commit", "-q", "-am", "add submodule")
        super_revision = git(super_repo, "rev-parse", "HEAD").stdout.strip()
        git(super_repo, "checkout", "-q", "--detach", super_revision)
        super_writer_baseline = writer_validation_baseline(
            super_repo,
            revision=super_revision,
        )
        if git_writer_target_errors(
            super_repo,
            expected_commit=super_revision,
            **super_writer_baseline,
        ):
            fail("clean initialized submodule target was rejected")
        super_common_dir = pathlib.Path(
            git(super_repo, "rev-parse", "--git-common-dir").stdout.strip()
        )
        if not super_common_dir.is_absolute():
            super_common_dir = pathlib.Path(
                os.path.abspath(super_repo / super_common_dir)
            )
        modules_directory = super_common_dir / "modules"
        moved_modules_directory = sub_root / "moved-modules"
        os.replace(modules_directory, moved_modules_directory)
        os.symlink(
            moved_modules_directory,
            modules_directory,
            target_is_directory=True,
        )
        if (
            "writer common Git control files must match baseline"
            not in git_writer_target_errors(
                super_repo,
                expected_commit=super_revision,
                **super_writer_baseline,
            )
        ):
            fail("shared submodule modules symlink bypassed common topology proof")
        modules_directory.unlink()
        os.replace(moved_modules_directory, modules_directory)
        initialized_submodule = super_repo / "deps" / "sub"
        submodule_common_dir = pathlib.Path(
            git(
                initialized_submodule,
                "rev-parse",
                "--git-common-dir",
            ).stdout.strip()
        )
        if not submodule_common_dir.is_absolute():
            submodule_common_dir = pathlib.Path(
                os.path.abspath(initialized_submodule / submodule_common_dir)
            )
        submodule_config = submodule_common_dir / "config"
        submodule_config_before = submodule_config.read_bytes()
        submodule_config.write_bytes(
            submodule_config_before + b"\n[qtim]\n\tprobe = true\n"
        )
        if (
            "writer submodule initialization and admin state must match baseline"
            not in git_writer_target_errors(
                super_repo,
                expected_commit=super_revision,
                **super_writer_baseline,
            )
        ):
            fail("nested submodule common config drift bypassed baseline proof")
        submodule_config.write_bytes(submodule_config_before)
        submodule_hook = submodule_common_dir / "hooks" / "qtim-probe"
        submodule_hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        if (
            "writer submodule initialization and admin state must match baseline"
            not in git_writer_target_errors(
                super_repo,
                expected_commit=super_revision,
                **super_writer_baseline,
            )
        ):
            fail("nested submodule hook drift bypassed baseline proof")
        submodule_hook.unlink()
        submodule_packed_refs = submodule_common_dir / "packed-refs"
        submodule_packed_refs_existed = submodule_packed_refs.exists()
        submodule_packed_refs_before = (
            submodule_packed_refs.read_bytes()
            if submodule_packed_refs_existed
            else b""
        )
        submodule_packed_refs.write_bytes(
            submodule_packed_refs_before + b"# qtim probe\n"
        )
        if (
            "writer submodule initialization and admin state must match baseline"
            not in git_writer_target_errors(
                super_repo,
                expected_commit=super_revision,
                **super_writer_baseline,
            )
        ):
            fail("nested submodule packed-refs drift bypassed baseline proof")
        if submodule_packed_refs_existed:
            submodule_packed_refs.write_bytes(submodule_packed_refs_before)
        else:
            submodule_packed_refs.unlink()
        git(sub_repo, "rm", "-q", "component.txt")
        git(sub_repo, "commit", "-q", "-m", "empty submodule commit")
        empty_sub_revision = git(sub_repo, "rev-parse", "HEAD").stdout.strip()
        git(initialized_submodule, "fetch", "-q", "origin")
        git(initialized_submodule, "checkout", "-q", empty_sub_revision)
        git(super_repo, "config", "submodule.deps/sub.ignore", "all")
        if list(
            entry
            for entry in initialized_submodule.iterdir()
            if entry.name != ".git"
        ):
            fail("empty initialized submodule fixture is not empty")
        if not git_writer_target_errors(
            super_repo,
            expected_commit=super_revision,
            **super_writer_baseline,
        ):
            fail("initialized empty submodule with wrong HEAD was accepted")
        git(initialized_submodule, "checkout", "-q", expected_sub_revision)
        git(super_repo, "config", "--unset", "submodule.deps/sub.ignore")
        (super_repo / "deps" / "sub" / "component.txt").write_text(
            "dirty\n",
            encoding="utf-8",
        )
        if not git_writer_target_errors(
            super_repo,
            expected_commit=super_revision,
            **super_writer_baseline,
        ):
            fail("dirty initialized submodule target was accepted")
        git(super_repo / "deps" / "sub", "restore", "component.txt")
        initialized_submodule_backup = sub_root / "initialized-submodule-backup"
        os.replace(initialized_submodule, initialized_submodule_backup)
        initialized_submodule.mkdir()
        if (
            "writer submodule initialization and admin state must match baseline"
            not in git_writer_target_errors(
                super_repo,
                expected_commit=super_revision,
                **super_writer_baseline,
            )
        ):
            fail("initialized submodule deinitialization bypassed baseline proof")
        initialized_submodule.rmdir()
        os.replace(initialized_submodule_backup, initialized_submodule)
        git(
            sub_root,
            "-c",
            "protocol.file.allow=always",
            "clone",
            "-q",
            "--no-recurse-submodules",
            str(super_repo),
            str(clone_repo),
        )
        clone_revision = git(clone_repo, "rev-parse", "HEAD").stdout.strip()
        git(clone_repo, "checkout", "-q", "--detach", clone_revision)
        clone_writer_baseline = writer_validation_baseline(
            clone_repo,
            revision=clone_revision,
        )
        if git_writer_target_errors(
            clone_repo,
            expected_commit=clone_revision,
            **clone_writer_baseline,
        ):
            fail("clean uninitialized submodule target was rejected")
        uninitialized_submodule = clone_repo / "deps" / "sub"
        if uninitialized_submodule.exists():
            shutil.rmtree(uninitialized_submodule)
        os.symlink("missing-submodule-target", uninitialized_submodule)
        if not git_writer_target_errors(
            clone_repo,
            expected_commit=clone_revision,
            **clone_writer_baseline,
        ):
            fail("broken symlink at expected submodule path was accepted")

    with tempfile.TemporaryDirectory(prefix="qtim-mission-git-") as temp_dir:
        root = pathlib.Path(temp_dir)
        source = root / "source"
        source.mkdir()
        git(source, "init", "-q")
        git(source, "config", "user.name", "qtim mission fixture")
        git(source, "config", "user.email", "qtim-mission@example.invalid")
        git(source, "config", "commit.gpgsign", "false")
        (source / "shared.txt").write_text("base\n", encoding="utf-8")
        (source / ".gitignore").write_text(
            ".codex/qtim-runtime/\n",
            encoding="utf-8",
        )
        legacy_portable = source / "memory" / "missions" / "fixture"
        legacy_portable.mkdir(parents=True)
        (legacy_portable / "obsolete.md").write_text(
            "remove during final evidence delivery\n",
            encoding="utf-8",
        )
        git(
            source,
            "add",
            ".gitignore",
            "shared.txt",
            "memory/missions/fixture/obsolete.md",
        )
        git(source, "commit", "-q", "-m", "base")
        base = git(source, "rev-parse", "HEAD").stdout.strip()
        git(source, "pack-refs", "--all")

        read_only_clean = root / "read-only-clean"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "-b",
            "read-only-clean",
            str(read_only_clean),
            base,
        )
        read_only_clean_refs = git_ref_snapshot(read_only_clean)
        read_only_clean_config = git_common_config_snapshot(read_only_clean)
        read_only_clean_control = git_common_control_snapshot(read_only_clean)
        read_only_clean_common_worktrees = (
            git_common_worktree_admin_snapshot(read_only_clean)
        )
        read_only_clean_worktree_control = git_worktree_control_snapshot(
            read_only_clean
        )
        read_only_clean_filesystem = worktree_filesystem_snapshot(read_only_clean)
        unchanged_read_only_errors = git_read_only_target_errors(
            read_only_clean,
            expected_revision=base,
            expected_refs=read_only_clean_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_clean_config,
            expected_common_control=read_only_clean_control,
            expected_common_worktree_admin=read_only_clean_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_clean_worktree_control,
            expected_filesystem=read_only_clean_filesystem,
        )
        if unchanged_read_only_errors:
            current_common_worktrees = git_common_worktree_admin_snapshot(
                read_only_clean
            )
            changed_common_worktree_paths = sorted(
                path
                for path in (
                    set(read_only_clean_common_worktrees)
                    | set(current_common_worktrees)
                )
                if read_only_clean_common_worktrees.get(path)
                != current_common_worktrees.get(path)
            )
            fail(
                "unchanged read-only target was rejected: "
                f"{unchanged_read_only_errors}; "
                f"common worktree paths={changed_common_worktree_paths}"
            )
        (read_only_clean / "shared.txt").write_text(
            "committed mutation\n",
            encoding="utf-8",
        )
        git(read_only_clean, "add", "shared.txt")
        git(read_only_clean, "commit", "-q", "-m", "read-only contract violation")
        if git(read_only_clean, "status", "--short").stdout:
            fail("committed-change fixture unexpectedly remained dirty")
        committed_read_only_errors = git_read_only_target_errors(
            read_only_clean,
            expected_revision=base,
            expected_refs=read_only_clean_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_clean_config,
            expected_common_control=read_only_clean_control,
            expected_common_worktree_admin=read_only_clean_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_clean_worktree_control,
            expected_filesystem=read_only_clean_filesystem,
        )
        if not {
            "read-only HEAD must equal expected revision",
            "read-only tree must equal expected revision",
        } <= set(committed_read_only_errors):
            fail("clean committed mutation bypassed read-only snapshot guard")

        read_only_dirty = root / "read-only-dirty"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "-b",
            "read-only-dirty",
            str(read_only_dirty),
            base,
        )
        read_only_dirty_refs = git_ref_snapshot(read_only_dirty)
        read_only_dirty_config = git_common_config_snapshot(read_only_dirty)
        read_only_dirty_control = git_common_control_snapshot(read_only_dirty)
        read_only_dirty_common_worktrees = (
            git_common_worktree_admin_snapshot(read_only_dirty)
        )
        read_only_dirty_worktree_control = git_worktree_control_snapshot(
            read_only_dirty
        )
        read_only_dirty_filesystem = worktree_filesystem_snapshot(read_only_dirty)
        (read_only_dirty / "untracked.txt").write_text("unexpected\n", encoding="utf-8")
        if "read-only target must remain clean" not in git_read_only_target_errors(
            read_only_dirty,
            expected_revision=base,
            expected_refs=read_only_dirty_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_dirty_config,
            expected_common_control=read_only_dirty_control,
            expected_common_worktree_admin=read_only_dirty_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_dirty_worktree_control,
            expected_filesystem=read_only_dirty_filesystem,
        ):
            fail("untracked mutation bypassed read-only cleanliness guard")
        if git_read_only_target_errors(
            read_only_dirty,
            expected_revision="HEAD",
            expected_refs=read_only_dirty_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_dirty_config,
            expected_common_control=read_only_dirty_control,
            expected_common_worktree_admin=read_only_dirty_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_dirty_worktree_control,
            expected_filesystem=read_only_dirty_filesystem,
        ) != ["read-only expected revision must be a canonical commit id"]:
            fail("symbolic read-only expected revision was accepted")

        read_only_detached = root / "read-only-detached"
        state_ref = "refs/heads/codex/qtim-mission-state-fixture"
        git(source, "update-ref", "refs/heads/approved", base)
        git(source, "update-ref", state_ref, base)
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(read_only_detached),
            base,
        )
        read_only_detached_refs = git_ref_snapshot(read_only_detached)
        read_only_detached_config = git_common_config_snapshot(read_only_detached)
        read_only_detached_control = git_common_control_snapshot(read_only_detached)
        read_only_detached_common_worktrees = (
            git_common_worktree_admin_snapshot(read_only_detached)
        )
        read_only_detached_worktree_control = git_worktree_control_snapshot(
            read_only_detached
        )
        runtime_missions = (
            read_only_detached / ".codex" / "qtim-runtime" / "missions"
        )
        runtime_missions.mkdir(parents=True)
        registry_path = runtime_missions / "fixture.json"
        registry_before_bytes = (
            json.dumps(
                {
                    "schemaVersion": 1,
                    "missionId": "fixture",
                    "ownership": {
                        "coordinatorThreadId": "coordinator",
                        "hostId": "local",
                        "generation": 1,
                    },
                    "nodes": {},
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        registry_path.write_bytes(registry_before_bytes)
        read_only_detached_filesystem = worktree_filesystem_snapshot(read_only_detached)
        registry_relative = ".codex/qtim-runtime/missions/fixture.json"
        registry_before_fingerprint = read_only_detached_filesystem[
            registry_relative
        ]
        registry_after_bytes = (
            json.dumps(
                {
                    "schemaVersion": 1,
                    "missionId": "fixture",
                    "ownership": {
                        "coordinatorThreadId": "coordinator",
                        "hostId": "local",
                        "generation": 1,
                    },
                    "nodes": {
                        "read-only": {
                            "status": "running",
                            "threadId": "opaque",
                            "hostId": "opaque",
                        }
                    },
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        registry_path.write_bytes(registry_after_bytes)
        registry_after_stat = os.lstat(registry_path)
        registry_after_fingerprint = (
            f"file:{registry_after_stat.st_mode & 0o7777:o}:"
            f"{registry_after_stat.st_dev}:{registry_after_stat.st_ino}:"
            f"{registry_after_stat.st_nlink}:"
            f"{_sha256_bytes(registry_after_bytes)}"
        )
        registry_transition = {
            "beforeFingerprint": registry_before_fingerprint,
            "afterFingerprint": registry_after_fingerprint,
            "coordinatorThreadId": "coordinator",
            "hostId": "local",
            "generation": 1,
        }
        registry_transition_errors = git_read_only_target_errors(
            read_only_detached,
            expected_revision=base,
            expected_refs=read_only_detached_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_detached_config,
            expected_common_control=read_only_detached_control,
            expected_common_worktree_admin=read_only_detached_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_detached_worktree_control,
            expected_filesystem=read_only_detached_filesystem,
            coordinator_registry_transition=registry_transition,
        )
        if registry_transition_errors:
            fail(
                "coordinator-owned registry transition was rejected: "
                f"{registry_transition_errors}"
            )
        if (
            "read-only raw filesystem must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("un journaled coordinator registry mutation was accepted")
        foreign_runtime_path = runtime_missions / "foreign.json"
        foreign_runtime_path.write_text("foreign\n", encoding="utf-8")
        if (
            "read-only raw filesystem must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
                coordinator_registry_transition=registry_transition,
            )
        ):
            fail("foreign runtime mutation hid behind coordinator registry journal")
        foreign_runtime_path.unlink()
        wrong_owner_transition = dict(registry_transition)
        wrong_owner_transition["coordinatorThreadId"] = "foreign"
        if (
            "read-only coordinator registry transition must match baseline, "
            "final bytes, mission, owner, and generation"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
                coordinator_registry_transition=wrong_owner_transition,
            )
        ):
            fail("foreign registry owner bypassed final-read ownership proof")
        registry_path.write_bytes(registry_before_bytes)
        read_only_mutation = git(
            read_only_clean,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        git(
            read_only_detached,
            "update-index",
            "--assume-unchanged",
            "shared.txt",
        )
        (read_only_detached / "shared.txt").write_text(
            "hidden tracked mutation\n",
            encoding="utf-8",
        )
        hidden_mutation_errors = git_read_only_target_errors(
            read_only_detached,
            expected_revision=base,
            expected_refs=read_only_detached_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_detached_config,
            expected_common_control=read_only_detached_control,
            expected_common_worktree_admin=read_only_detached_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_detached_worktree_control,
            expected_filesystem=read_only_detached_filesystem,
        )
        if "read-only raw filesystem must match baseline" not in hidden_mutation_errors:
            fail("assume-unchanged mutation bypassed raw read-only fingerprint")
        if (
            "read-only per-worktree git control must match baseline"
            not in hidden_mutation_errors
        ):
            fail("assume-unchanged index mutation bypassed worktree control proof")
        git(
            read_only_detached,
            "update-index",
            "--no-assume-unchanged",
            "shared.txt",
        )
        git(read_only_detached, "restore", "--source", base, "shared.txt")
        git(read_only_detached, "status", "--short", "--untracked-files=all")
        read_only_detached_worktree_control = git_worktree_control_snapshot(
            read_only_detached
        )
        read_only_detached_common_worktrees = (
            git_common_worktree_admin_snapshot(read_only_detached)
        )
        read_only_detached_filesystem = worktree_filesystem_snapshot(
            read_only_detached
        )
        shared_path = read_only_detached / "shared.txt"
        shared_mode = os.stat(shared_path).st_mode & 0o7777
        os.chmod(shared_path, 0o400)
        if (
            "read-only raw filesystem must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("read-only regular-file permission mutation bypassed raw proof")
        os.chmod(shared_path, shared_mode)

        memory_directory = read_only_detached / "memory"
        memory_mode = os.stat(memory_directory).st_mode & 0o7777
        os.chmod(memory_directory, 0o500)
        if (
            "read-only raw filesystem must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("read-only directory permission mutation bypassed raw proof")
        os.chmod(memory_directory, memory_mode)

        original_shared_backup = root / "shared-original-backup"
        hardlink_source = root / "same-bytes-hardlink-source"
        shared_bytes = shared_path.read_bytes()
        os.replace(shared_path, original_shared_backup)
        hardlink_source.write_bytes(shared_bytes)
        os.chmod(hardlink_source, shared_mode)
        os.link(hardlink_source, shared_path)
        if (
            "read-only raw filesystem must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("same-bytes hardlink replacement bypassed raw topology proof")
        shared_path.unlink()
        hardlink_source.unlink()
        os.replace(original_shared_backup, shared_path)

        detached_dotgit = read_only_detached / ".git"
        detached_dotgit_before = detached_dotgit.read_bytes()
        detached_git_dir = pathlib.Path(
            git(read_only_detached, "rev-parse", "--git-dir").stdout.strip()
        )
        if not detached_git_dir.is_absolute():
            detached_git_dir = pathlib.Path(
                os.path.abspath(read_only_detached / detached_git_dir)
            )
        detached_git_dir_alias = root / "read-only-gitdir-alias"
        os.symlink(detached_git_dir, detached_git_dir_alias)
        detached_dotgit.write_text(
            f"gitdir: {detached_git_dir_alias}\n",
            encoding="utf-8",
        )
        if (
            "read-only per-worktree git control must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("read-only .git pointer alias bypassed worktree identity proof")
        detached_dotgit.write_bytes(detached_dotgit_before)
        detached_git_dir_alias.unlink()

        foreign_git_dir = pathlib.Path(
            git(read_only_clean, "rev-parse", "--git-dir").stdout.strip()
        )
        if not foreign_git_dir.is_absolute():
            foreign_git_dir = pathlib.Path(
                os.path.abspath(read_only_clean / foreign_git_dir)
            )
        foreign_head_path = foreign_git_dir / "HEAD"
        foreign_head_before = foreign_head_path.read_bytes()
        foreign_head_path.write_text(f"{read_only_mutation}\n", encoding="utf-8")
        if (
            "read-only common worktree admin violates coordinator journal"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("foreign linked-worktree HEAD mutation bypassed common admin proof")
        foreign_head_path.write_bytes(foreign_head_before)

        journaled_worktree = root / "journaled-worktree"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(journaled_worktree),
            base,
        )
        journaled_entry = assigned_common_worktree_entry(journaled_worktree)
        journaled_after = git_common_worktree_admin_snapshot(read_only_detached)
        journaled_prefix = f"{journaled_entry}/"
        journaled_subtree = {
            path: value
            for path, value in journaled_after.items()
            if path == journaled_entry or path.startswith(journaled_prefix)
        }
        journaled_addition_errors = git_read_only_target_errors(
            read_only_detached,
            expected_revision=base,
            expected_refs=read_only_detached_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_detached_config,
            expected_common_control=read_only_detached_control,
            expected_common_worktree_admin=read_only_detached_common_worktrees,
            coordinator_worktree_admin_additions={
                journaled_entry: journaled_subtree
            },
            expected_worktree_control=read_only_detached_worktree_control,
            expected_filesystem=read_only_detached_filesystem,
        )
        if journaled_addition_errors:
            fail(
                "exact coordinator-journaled worktree addition was rejected: "
                f"{journaled_addition_errors}"
            )
        git(
            source,
            "worktree",
            "remove",
            "--force",
            str(journaled_worktree),
        )
        git(
            read_only_detached,
            "update-ref",
            "refs/codex/snapshots/allowed-runtime-probe",
            read_only_mutation,
        )
        if git_ref_snapshot(read_only_detached) != read_only_detached_refs:
            fail("runtime-owned refs/codex churn polluted protected ref snapshot")
        git(
            read_only_detached,
            "update-ref",
            "-d",
            "refs/codex/snapshots/allowed-runtime-probe",
        )
        git(
            read_only_detached,
            "update-ref",
            state_ref,
            read_only_mutation,
            base,
        )
        state_checkpoint_errors = git_read_only_target_errors(
            read_only_detached,
            expected_revision=base,
            expected_refs=read_only_detached_refs,
            coordinator_authorized_ref_updates={
                state_ref: {"old": base, "new": read_only_mutation},
            },
            mission_slug="fixture",
            coordinator_owned_refs={state_ref},
            expected_common_config=read_only_detached_config,
            expected_common_control=read_only_detached_control,
            expected_common_worktree_admin=read_only_detached_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_detached_worktree_control,
            expected_filesystem=read_only_detached_filesystem,
        )
        if state_checkpoint_errors:
            current_worktree_control = git_worktree_control_snapshot(
                read_only_detached
            )
            changed_worktree_control = sorted(
                path
                for path in (
                    set(read_only_detached_worktree_control)
                    | set(current_worktree_control)
                )
                if read_only_detached_worktree_control.get(path)
                != current_worktree_control.get(path)
            )
            current_common_worktrees = git_common_worktree_admin_snapshot(
                read_only_detached
            )
            changed_common_worktrees = sorted(
                path
                for path in (
                    set(read_only_detached_common_worktrees)
                    | set(current_common_worktrees)
                )
                if read_only_detached_common_worktrees.get(path)
                != current_common_worktrees.get(path)
            )
            fail(
                "coordinator-journaled state ref checkpoint was rejected: "
                f"{state_checkpoint_errors}; current={changed_worktree_control}; "
                f"common={changed_common_worktrees}"
            )
        git(
            read_only_detached,
            "update-ref",
            state_ref,
            base,
            read_only_mutation,
        )
        git(
            read_only_detached,
            "update-ref",
            "refs/heads/approved",
            read_only_mutation,
            base,
        )
        if (
            "read-only protected refs violate authorized transitions"
            not in git_read_only_target_errors(
            read_only_detached,
            expected_revision=base,
            expected_refs=read_only_detached_refs,
            coordinator_authorized_ref_updates={},
            mission_slug="fixture",
            coordinator_owned_refs=set(),
            expected_common_config=read_only_detached_config,
            expected_common_control=read_only_detached_control,
            expected_common_worktree_admin=read_only_detached_common_worktrees,
            coordinator_worktree_admin_additions={},
            expected_worktree_control=read_only_detached_worktree_control,
            expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared Approved ref mutation bypassed read-only guard")
        git(
            read_only_detached,
            "update-ref",
            "refs/heads/approved",
            base,
            read_only_mutation,
        )
        git(read_only_detached, "config", "--local", "qtim.readonly-probe", "changed")
        if (
            "read-only common git config must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared git config mutation bypassed read-only guard")
        git(
            read_only_detached,
            "config",
            "--local",
            "--unset",
            "qtim.readonly-probe",
        )
        common_dir_raw = git(
            read_only_detached,
            "rev-parse",
            "--git-common-dir",
        ).stdout.strip()
        common_dir = pathlib.Path(common_dir_raw)
        if not common_dir.is_absolute():
            common_dir = (read_only_detached / common_dir).resolve()
        exclude_file = common_dir / "info" / "exclude"
        original_exclude = exclude_file.read_bytes()
        exclude_file.write_bytes(original_exclude + b"\nqtim-hidden-probe\n")
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared info/exclude mutation bypassed read-only guard")
        exclude_file.write_bytes(original_exclude)
        attributes_file = common_dir / "info" / "attributes"
        attributes_existed = attributes_file.exists()
        original_attributes = (
            attributes_file.read_bytes() if attributes_existed else b""
        )
        attributes_file.write_bytes(original_attributes + b"\n*.md -text\n")
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared info/attributes mutation bypassed read-only guard")
        if attributes_existed:
            attributes_file.write_bytes(original_attributes)
        else:
            attributes_file.unlink()
        if hasattr(os, "mkfifo"):
            grafts_file = common_dir / "info" / "grafts"
            if grafts_file.exists():
                fail("fresh Git fixture unexpectedly contains info/grafts")
            os.mkfifo(grafts_file)
            if (
                git_common_control_snapshot(read_only_detached)
                == read_only_detached_control
            ):
                fail("special common control file aliased a missing file")
            grafts_file.unlink()
        hook_path = common_dir / "hooks" / "pre-commit.sample"
        original_hook_mode = os.stat(hook_path).st_mode
        os.chmod(hook_path, original_hook_mode ^ 0o100)
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared hook mode mutation bypassed read-only guard")
        os.chmod(hook_path, original_hook_mode)
        hooks_directory = common_dir / "hooks"
        moved_hooks_directory = root / "moved-common-hooks"
        os.replace(hooks_directory, moved_hooks_directory)
        os.symlink(
            moved_hooks_directory,
            hooks_directory,
            target_is_directory=True,
        )
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared hooks directory symlink bypassed common-control proof")
        hooks_directory.unlink()
        os.replace(moved_hooks_directory, hooks_directory)
        objects_directory = common_dir / "objects"
        moved_objects_directory = root / "moved-common-objects"
        os.replace(objects_directory, moved_objects_directory)
        os.symlink(
            moved_objects_directory,
            objects_directory,
            target_is_directory=True,
        )
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("shared objects directory symlink bypassed common topology proof")
        objects_directory.unlink()
        os.replace(moved_objects_directory, objects_directory)
        packed_refs_path = common_dir / "packed-refs"
        moved_packed_refs = root / "moved-packed-refs"
        os.replace(packed_refs_path, moved_packed_refs)
        os.symlink(moved_packed_refs, packed_refs_path)
        if (
            "read-only common git control files must match baseline"
            not in git_read_only_target_errors(
                read_only_detached,
                expected_revision=base,
                expected_refs=read_only_detached_refs,
                coordinator_authorized_ref_updates={},
                mission_slug="fixture",
                coordinator_owned_refs=set(),
                expected_common_config=read_only_detached_config,
                expected_common_control=read_only_detached_control,
                expected_common_worktree_admin=read_only_detached_common_worktrees,
                coordinator_worktree_admin_additions={},
                expected_worktree_control=read_only_detached_worktree_control,
                expected_filesystem=read_only_detached_filesystem,
            )
        ):
            fail("packed-refs symlink bypassed common-control topology proof")
        packed_refs_path.unlink()
        os.replace(moved_packed_refs, packed_refs_path)

        integration = root / "integration"
        integration_target_ref = "refs/heads/mission-integration"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "-b",
            "mission-integration",
            str(integration),
            base,
        )
        state = root / "state"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "-b",
            "mission-state",
            str(state),
            base,
        )
        portable = state / "memory" / "missions" / "fixture"
        (portable / "mission.md").write_text(
            "status: Running\nstateSequence: 1\n",
            encoding="utf-8",
        )
        (portable / "receipts.md").write_text(
            "analysis: validated\n",
            encoding="utf-8",
        )
        (portable / "decisions.md").write_text("none\n", encoding="utf-8")
        (portable / "verification.md").write_text(
            "verdict: pending\n",
            encoding="utf-8",
        )
        git(state, "add", "memory/missions/fixture")
        git(state, "commit", "-q", "-m", "qtim-mission-state: fixture 1 running")
        state_checkpoint_1 = git(state, "rev-parse", "HEAD").stdout.strip()
        state_paths_1 = git(
            state,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            state_checkpoint_1,
        ).stdout.splitlines()
        if state_paths_1 != [
            "memory/missions/fixture/decisions.md",
            "memory/missions/fixture/mission.md",
            "memory/missions/fixture/receipts.md",
            "memory/missions/fixture/verification.md",
        ]:
            fail(f"portable checkpoint escaped mission state scope: {state_paths_1}")
        if git(state, "status", "--short").stdout:
            fail("portable state checkpoint worktree was not clean after commit")

        (portable / "mission.md").write_text(
            "status: Verifying\nstateSequence: 2\n",
            encoding="utf-8",
        )
        (portable / "verification.md").write_text(
            "globalGates: green\nverdict: pending\n",
            encoding="utf-8",
        )
        git(
            state,
            "add",
            "memory/missions/fixture/mission.md",
            "memory/missions/fixture/verification.md",
        )
        git(state, "commit", "-q", "-m", "qtim-mission-state: fixture 2 verifying")
        state_checkpoint_2 = git(state, "rev-parse", "HEAD").stdout.strip()
        parents_state_2 = git(
            source,
            "rev-list",
            "--parents",
            "-n",
            "1",
            state_checkpoint_2,
        ).stdout.split()
        if len(parents_state_2) != 2 or parents_state_2[1] != state_checkpoint_1:
            fail("portable state checkpoint sequence was not monotonic")
        if "stateSequence: 2" not in git(
            state,
            "show",
            f"{state_checkpoint_2}:memory/missions/fixture/mission.md",
        ).stdout:
            fail("portable state checkpoint content did not advance sequence")
        if git(integration, "status", "--short").stdout:
            fail("portable state leaked into clean integration worktree")
        integration_before_blocked_resume = git(
            integration,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        refs_before_blocked_resume = git(
            source,
            "for-each-ref",
            "--format=%(refname):%(objectname)",
            "refs/heads",
        ).stdout
        (portable / "verification.md").write_text(
            "globalGates: green\nverdict: APPROVED\npartial crash write\n",
            encoding="utf-8",
        )
        blocked_resume = classify_resume(
            tool_available=True,
            candidates=1,
            project_matches=True,
            marker_matches=True,
            attempt_matches=True,
            host_matches=True,
            source_matches=True,
            base_matches=True,
            portable_state_clean=not bool(git(state, "status", "--short").stdout),
            state_sequence_valid=True,
        )
        if blocked_resume != "blocked":
            fail("partial portable state write did not block resume")
        if (
            git(integration, "rev-parse", "HEAD").stdout.strip()
            != integration_before_blocked_resume
            or git(
                source,
                "for-each-ref",
                "--format=%(refname):%(objectname)",
                "refs/heads",
            ).stdout
            != refs_before_blocked_resume
        ):
            fail("blocked crash recovery produced a Git side effect")
        if (root / "node-a").exists():
            fail("blocked crash recovery created a writer before reconciliation")
        if git(integration, "status", "--short").stdout:
            fail("partial portable write dirtied integration worktree")
        git(state, "restore", "memory/missions/fixture/verification.md")
        if git(state, "status", "--short").stdout:
            fail("explicit crash reconciliation did not restore clean checkpoint")
        resumed = classify_resume(
            tool_available=True,
            candidates=1,
            project_matches=True,
            marker_matches=True,
            attempt_matches=True,
            host_matches=True,
            source_matches=True,
            base_matches=True,
            portable_state_clean=True,
            state_sequence_valid=True,
        )
        if resumed != "live":
            fail("clean monotonic checkpoint did not allow resume after reconciliation")

        node_a = root / "node-a"
        node_b = root / "node-b"
        red_node = root / "red-node"
        side_node = root / "side-node"
        late_node = root / "late-node"
        conflict_node = root / "conflict"
        transaction_evidence = root / "transaction-evidence"
        (source / ".codex" / "qtim-runtime" / "missions").mkdir(parents=True)
        (
            source_registry,
            ownership_lock,
            promotion_lock,
        ) = canonical_mission_runtime_paths(
            source,
            "fixture",
        )
        source_registry.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "missionId": "fixture",
                    "ownership": {
                        "coordinatorThreadId": "coordinator",
                        "hostId": "local",
                        "generation": 1,
                    },
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        wave_a = root / "wave-a"
        wave_b = root / "wave-b"
        for wave_target in (wave_a, wave_b):
            git(
                source,
                "worktree",
                "add",
                "-q",
                "--detach",
                str(wave_target),
                base,
            )
        wave_a_baseline = writer_validation_baseline(wave_a, revision=base)
        wave_b_baseline = writer_validation_baseline(wave_b, revision=base)
        wave_entries = {
            assigned_common_worktree_entry(wave_a),
            assigned_common_worktree_entry(wave_b),
        }
        if None in wave_entries:
            fail("parallel writer fixture did not create linked worktree entries")
        wave_a_baseline["assigned_worktree_entries"] = set(wave_entries)
        wave_b_baseline["assigned_worktree_entries"] = set(wave_entries)
        (wave_a / "wave-a.txt").write_text("wave A\n", encoding="utf-8")
        git(wave_a, "add", "wave-a.txt")
        git(wave_a, "commit", "-q", "-m", "wave A")
        wave_a_commit = git(wave_a, "rev-parse", "HEAD").stdout.strip()
        (wave_b / "wave-b.txt").write_text("wave B\n", encoding="utf-8")
        git(wave_b, "add", "wave-b.txt")
        git(wave_b, "commit", "-q", "-m", "wave B")
        wave_b_commit = git(wave_b, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            wave_a,
            expected_commit=wave_a_commit,
            **wave_a_baseline,
        ):
            fail("parallel sibling writer admin transition rejected writer A")
        if git_writer_target_errors(
            wave_b,
            expected_commit=wave_b_commit,
            **wave_b_baseline,
        ):
            fail("parallel sibling writer admin transition rejected writer B")
        wave_b_git_dir = pathlib.Path(
            git(wave_b, "rev-parse", "--git-dir").stdout.strip()
        )
        if not wave_b_git_dir.is_absolute():
            wave_b_git_dir = pathlib.Path(
                os.path.abspath(wave_b / wave_b_git_dir)
            )
        wave_b_foreign_control = wave_b_git_dir / "foreign-control"
        wave_b_foreign_control.write_text("unexpected\n", encoding="utf-8")
        if (
            "writer common worktree admin violates coordinator journal"
            not in git_writer_target_errors(
                wave_a,
                expected_commit=wave_a_commit,
                **wave_a_baseline,
            )
        ):
            fail("parallel sibling writer extra admin file bypassed frozen proof")
        wave_b_foreign_control.unlink()

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(node_a),
            base,
        )
        node_a_writer_baseline = writer_validation_baseline(
            node_a,
            revision=base,
        )
        (node_a / "a.txt").write_text("A\n", encoding="utf-8")
        git(node_a, "add", "a.txt")
        git(node_a, "commit", "-q", "-m", "node A")
        commit_a = git(node_a, "rev-parse", "HEAD").stdout.strip()
        node_a_writer_errors = git_writer_target_errors(
            node_a,
            expected_commit=commit_a,
            **node_a_writer_baseline,
        )
        if node_a_writer_errors:
            node_a_common_after = git_common_worktree_admin_snapshot(node_a)
            node_a_common_before = node_a_writer_baseline[
                "expected_common_worktree_admin"
            ]
            node_a_admin_changes = sorted(
                path
                for path in set(node_a_common_before) | set(node_a_common_after)
                if node_a_common_before.get(path) != node_a_common_after.get(path)
            )
            fail(
                "clean writer target did not match its exact commit tree: "
                f"{node_a_writer_errors}; admin={node_a_admin_changes}"
            )
        writer_hardlink_target = node_a / "a.txt"
        writer_hardlink_bytes = writer_hardlink_target.read_bytes()
        writer_hardlink_mode = os.stat(writer_hardlink_target).st_mode & 0o7777
        writer_hardlink_source = root / "writer-hardlink-source"
        writer_hardlink_source.write_bytes(writer_hardlink_bytes)
        os.chmod(writer_hardlink_source, writer_hardlink_mode)
        writer_hardlink_target.unlink()
        os.link(writer_hardlink_source, writer_hardlink_target)
        if (
            "writer filesystem must match commit tree"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("same-bytes writer hardlink bypassed commit-tree proof")
        writer_hardlink_target.unlink()
        writer_hardlink_target.write_bytes(writer_hardlink_bytes)
        os.chmod(writer_hardlink_target, writer_hardlink_mode)
        writer_hardlink_source.unlink()
        writer_untracked_probe = node_a / "untracked-writer-probe.txt"
        writer_untracked_probe.write_text("unexpected\n", encoding="utf-8")
        writer_dirty_errors = git_writer_target_errors(
            node_a,
            expected_commit=commit_a,
            **node_a_writer_baseline,
        )
        if not {
            "writer worktree must be clean including untracked files",
            "writer filesystem must match commit tree",
        } <= set(writer_dirty_errors):
            fail("untracked writer residue bypassed clean commit-tree guard")
        writer_untracked_probe.unlink()
        node_a_dotgit = node_a / ".git"
        node_a_dotgit_before = node_a_dotgit.read_bytes()
        node_a_git_dir = pathlib.Path(
            git(node_a, "rev-parse", "--git-dir").stdout.strip()
        )
        if not node_a_git_dir.is_absolute():
            node_a_git_dir = pathlib.Path(
                os.path.abspath(node_a / node_a_git_dir)
            )
        node_a_git_dir_alias = root / "node-a-gitdir-alias"
        os.symlink(node_a_git_dir, node_a_git_dir_alias)
        node_a_dotgit.write_text(
            f"gitdir: {node_a_git_dir_alias}\n",
            encoding="utf-8",
        )
        if (
            "writer Git admin identity must match assigned worktree"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("writer .git pointer alias bypassed assigned identity proof")
        node_a_dotgit.write_bytes(node_a_dotgit_before)
        node_a_git_dir_alias.unlink()

        config_worktree = node_a_git_dir / "config.worktree"
        config_worktree.write_text(
            "[core]\n\thooksPath = /external/qtim-probe\n",
            encoding="utf-8",
        )
        config_worktree_errors = git_writer_target_errors(
            node_a,
            expected_commit=commit_a,
            **node_a_writer_baseline,
        )
        if (
            "writer frozen per-worktree Git control must match baseline"
            not in config_worktree_errors
        ):
            fail("writer config.worktree mutation bypassed frozen admin proof")
        config_worktree.unlink()

        foreign_assigned_control = node_a_git_dir / "foreign-control"
        foreign_assigned_control.write_text("unexpected\n", encoding="utf-8")
        if (
            "writer common worktree admin violates coordinator journal"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("extra assigned worktree admin file bypassed common registry proof")
        foreign_assigned_control.unlink()

        common_dir_raw = git(node_a, "rev-parse", "--git-common-dir").stdout.strip()
        node_a_common_dir = pathlib.Path(common_dir_raw)
        if not node_a_common_dir.is_absolute():
            node_a_common_dir = pathlib.Path(
                os.path.abspath(node_a / node_a_common_dir)
            )
        common_config_path = node_a_common_dir / "config"
        common_config_before = common_config_path.read_bytes()
        common_config_path.write_bytes(
            common_config_before + b"\n[qtim]\n\tprobe = true\n"
        )
        common_config_errors = git_writer_target_errors(
            node_a,
            expected_commit=commit_a,
            **node_a_writer_baseline,
        )
        if not {
            "writer common Git config must match baseline",
            "writer common Git control files must match baseline",
        } <= set(common_config_errors):
            fail("writer common Git config mutation bypassed target validation")
        common_config_path.write_bytes(common_config_before)

        integration_git_dir = pathlib.Path(
            git(integration, "rev-parse", "--git-dir").stdout.strip()
        )
        if not integration_git_dir.is_absolute():
            integration_git_dir = pathlib.Path(
                os.path.abspath(integration / integration_git_dir)
            )
        integration_head_path = integration_git_dir / "HEAD"
        integration_head_before = integration_head_path.read_bytes()
        integration_head_path.write_text(f"{base}\n", encoding="utf-8")
        if (
            "writer common worktree admin violates coordinator journal"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("writer mutation of foreign worktree admin bypassed registry proof")
        integration_head_path.write_bytes(integration_head_before)

        git(node_a, "update-index", "--assume-unchanged", "shared.txt")
        if (
            "writer index must not contain unsafe flags or stages"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("writer assume-unchanged index flag bypassed canonical index proof")
        git(node_a, "update-index", "--no-assume-unchanged", "shared.txt")
        node_a_index = node_a_git_dir / "index"
        node_a_index_backup = root / "node-a-index-backup"
        os.replace(node_a_index, node_a_index_backup)
        os.link(node_a_index_backup, node_a_index)
        if (
            "writer common worktree admin violates coordinator journal"
            not in git_writer_target_errors(
                node_a,
                expected_commit=commit_a,
                **node_a_writer_baseline,
            )
        ):
            fail("writer hard-linked index bypassed assigned-admin shape proof")
        node_a_index.unlink()
        os.replace(node_a_index_backup, node_a_index)

        parents_a = git(source, "rev-list", "--parents", "-n", "1", commit_a).stdout.split()
        if len(parents_a) != 2 or parents_a[1] != base:
            fail("root writer did not produce one non-merge commit from mission base")
        paths_a = git(
            source, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_a
        ).stdout.splitlines()
        if paths_a != ["a.txt"]:
            fail(f"root writer fixture escaped scope: {commit_a}: {paths_a}")

        transaction_a = root / "transaction-a"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_a),
            base,
        )
        git(transaction_a, "cherry-pick", commit_a)
        staged_a = git(transaction_a, "rev-parse", "HEAD").stdout.strip()
        if not (transaction_a / "a.txt").is_file():
            fail("green affected gate fixture did not observe node A")
        alternate_promotion_lock = promotion_lock.with_name(
            "fixture.alternate-promotion.lock"
        )
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=alternate_promotion_lock,
            )
            != "unavailable"
            or alternate_promotion_lock.exists()
        ):
            fail("caller-chosen promotion lock path bypassed canonical fencing")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=2,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "stale"
            or promotion_lock.exists()
        ):
            fail("stale promotion owner generation bypassed registry binding")
        source_registry_before_generation_race = source_registry.read_bytes()
        generation_race_registry = json.loads(
            source_registry_before_generation_race
        )
        generation_race_registry["ownership"] = {
            "coordinatorThreadId": "takeover",
            "hostId": "local",
            "generation": 2,
        }
        source_registry.write_text(
            json.dumps(generation_race_registry, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        integration_before_generation_race = git(
            integration,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "stale"
            or git(integration, "rev-parse", "HEAD").stdout.strip()
            != integration_before_generation_race
            or ownership_lock.exists()
            or promotion_lock.exists()
        ):
            fail("generation takeover race moved Approved state before promotion")
        source_registry.write_bytes(source_registry_before_generation_race)
        ownership_lock.mkdir()
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "ambiguous"
            or promotion_lock.exists()
            or git(integration, "rev-parse", "HEAD").stdout.strip()
            != integration_before_generation_race
        ):
            fail("promotion bypassed ownership-before-promotion lock order")
        ownership_lock.rmdir()
        detached_integration = root / "detached-integration"
        wrong_integration = root / "wrong-integration"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(detached_integration),
            base,
        )
        git(
            source,
            "worktree",
            "add",
            "-q",
            "-b",
            "wrong-integration",
            str(wrong_integration),
            base,
        )
        wrong_integration_writer_baseline = writer_validation_baseline(
            wrong_integration,
            revision=base,
        )
        if (
            "writer HEAD must remain detached"
            not in git_writer_target_errors(
                wrong_integration,
                expected_commit=base,
                **wrong_integration_writer_baseline,
            )
        ):
            fail("attached writer target bypassed detached App contract")
        for wrong_target_worktree in (detached_integration, wrong_integration):
            if (
                fenced_ff_only_promotion(
                    wrong_target_worktree,
                    project_root=source,
                    mission_slug="fixture",
                    owner_token="coordinator",
                    owner_generation=1,
                    integration_target_ref=integration_target_ref,
                    expected_old=base,
                    transaction_head=staged_a,
                    lock_path=promotion_lock,
                )
                != "rejected"
            ):
                fail("detached or wrong-branch integration worktree was accepted")
            if (
                git(
                    source,
                    "rev-parse",
                    "--verify",
                    integration_target_ref,
                ).stdout.strip()
                != base
                or git(wrong_target_worktree, "rev-parse", "HEAD").stdout.strip()
                != base
            ):
                fail("wrong-target promotion moved a ref or worktree HEAD")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref="HEAD",
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "rejected"
        ):
            fail("non-canonical Approved integration target ref was accepted")
        for invalid_transaction_head in ("HEAD", staged_a[:12], base):
            if (
                fenced_ff_only_promotion(
                    integration,
                    project_root=source,
                    mission_slug="fixture",
                    owner_token="coordinator",
                    owner_generation=1,
                    integration_target_ref=integration_target_ref,
                    expected_old=base,
                    transaction_head=invalid_transaction_head,
                    lock_path=promotion_lock,
                )
                != "rejected"
            ):
                fail(
                    "non-canonical or no-op transaction revision was accepted: "
                    f"{invalid_transaction_head}"
                )
            if git(integration, "rev-parse", "HEAD").stdout.strip() != base:
                fail("rejected transaction revision moved Approved HEAD")
        dirty_probe = integration / "dirty-probe.txt"
        dirty_probe.write_text("dirty\n", encoding="utf-8")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "dirty"
        ):
            fail("dirty integration worktree was accepted for promotion")
        if git(integration, "rev-parse", "HEAD").stdout.strip() != base:
            fail("dirty promotion moved Approved HEAD")
        dirty_probe.unlink()
        promotion_lock.mkdir()
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "ambiguous"
        ):
            fail("concurrent integration promotion lock was not rejected")
        promotion_lock.rmdir()
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=base,
                transaction_head=staged_a,
                lock_path=promotion_lock,
            )
            != "integrated"
        ):
            fail("green transaction A was not promoted with exact-old guard")
        integrated_a = git(integration, "rev-parse", "HEAD").stdout.strip()
        if integrated_a != staged_a or not (integration / "a.txt").is_file():
            fail("green transaction did not fast-forward Approved integration branch")
        if (integration / "b.txt").exists():
            fail("first topological integration did not isolate node A")

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(node_b),
            integrated_a,
        )
        node_b_writer_baseline = writer_validation_baseline(
            node_b,
            revision=integrated_a,
        )
        (node_b / "b.txt").write_text("B\n", encoding="utf-8")
        git(node_b, "add", "b.txt")
        git(node_b, "commit", "-q", "-m", "node B after integrated A")
        commit_b = git(node_b, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            node_b,
            expected_commit=commit_b,
            **node_b_writer_baseline,
        ):
            fail("detached dependent writer target was rejected")
        parents_b = git(source, "rev-list", "--parents", "-n", "1", commit_b).stdout.split()
        if len(parents_b) != 2 or parents_b[1] != integrated_a:
            fail("dependent writer parent does not equal current integrated expectedBase")
        if git(source, "merge-base", "--is-ancestor", base, commit_b).returncode != 0:
            fail("mission base is not an ancestor of dependent writer commit")
        paths_b = git(
            source, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_b
        ).stdout.splitlines()
        if paths_b != ["b.txt"]:
            fail(f"dependent writer fixture escaped scope: {commit_b}: {paths_b}")

        transaction_b = root / "transaction-b"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_b),
            integrated_a,
        )
        git(transaction_b, "cherry-pick", commit_b)
        staged_b = git(transaction_b, "rev-parse", "HEAD").stdout.strip()
        if not (transaction_b / "b.txt").is_file():
            fail("green affected gate fixture did not observe node B")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=integrated_a,
                transaction_head=staged_b,
                lock_path=promotion_lock,
            )
            != "integrated"
        ):
            fail("green transaction B was not promoted with exact-old guard")
        integrated_b = git(integration, "rev-parse", "HEAD").stdout.strip()
        if integrated_b != staged_b or not (integration / "b.txt").is_file():
            fail("second topological integration did not advance revision")

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(red_node),
            integrated_b,
        )
        red_node_writer_baseline = writer_validation_baseline(
            red_node,
            revision=integrated_b,
        )
        (red_node / "red.txt").write_text("would fail gate\n", encoding="utf-8")
        git(red_node, "add", "red.txt")
        git(red_node, "commit", "-q", "-m", "red gate node")
        red_commit = git(red_node, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            red_node,
            expected_commit=red_commit,
            **red_node_writer_baseline,
        ):
            fail("detached red-gate writer target was rejected")
        transaction_red = root / "transaction-red"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_red),
            integrated_b,
        )
        git(transaction_red, "cherry-pick", red_commit)
        if git(integration, "rev-parse", "HEAD").stdout.strip() != integrated_b:
            fail("red affected gate advanced Approved integration branch")
        if (integration / "red.txt").exists():
            fail("red affected gate leaked unaccepted content into Approved branch")

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(side_node),
            integrated_b,
        )
        side_node_writer_baseline = writer_validation_baseline(
            side_node,
            revision=integrated_b,
        )
        (side_node / "shared.txt").write_text("integration-side\n", encoding="utf-8")
        git(side_node, "add", "shared.txt")
        git(side_node, "commit", "-q", "-m", "integration-side change")
        side_commit = git(side_node, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            side_node,
            expected_commit=side_commit,
            **side_node_writer_baseline,
        ):
            fail("detached side writer target was rejected")
        transaction_side = root / "transaction-side"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_side),
            integrated_b,
        )
        git(transaction_side, "cherry-pick", side_commit)
        staged_side = git(transaction_side, "rev-parse", "HEAD").stdout.strip()
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=integrated_b,
                transaction_head=staged_side,
                lock_path=promotion_lock,
            )
            != "integrated"
        ):
            fail("integration-side transaction was not promoted")
        integrated_side = git(integration, "rev-parse", "HEAD").stdout.strip()

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(late_node),
            integrated_side,
        )
        late_node_writer_baseline = writer_validation_baseline(
            late_node,
            revision=integrated_side,
        )
        (late_node / "late.txt").write_text("late\n", encoding="utf-8")
        git(late_node, "add", "late.txt")
        git(late_node, "commit", "-q", "-m", "late transaction")
        late_commit = git(late_node, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            late_node,
            expected_commit=late_commit,
            **late_node_writer_baseline,
        ):
            fail("detached late writer target was rejected")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=integrated_b,
                transaction_head=late_commit,
                lock_path=promotion_lock,
            )
            != "stale"
        ):
            fail("foreign Approved HEAD drift bypassed exact-old promotion guard")
        if git(integration, "rev-parse", "HEAD").stdout.strip() != integrated_side:
            fail("stale promotion changed Approved integration HEAD")

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(conflict_node),
            base,
        )
        conflict_node_writer_baseline = writer_validation_baseline(
            conflict_node,
            revision=base,
        )
        (conflict_node / "shared.txt").write_text("worker\n", encoding="utf-8")
        git(conflict_node, "add", "shared.txt")
        git(conflict_node, "commit", "-q", "-m", "conflicting node")
        conflict_commit = git(conflict_node, "rev-parse", "HEAD").stdout.strip()
        if git_writer_target_errors(
            conflict_node,
            expected_commit=conflict_commit,
            **conflict_node_writer_baseline,
        ):
            fail("detached conflicting writer target was rejected")
        transaction_conflict = root / "transaction-conflict"
        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_conflict),
            integrated_side,
        )
        conflict = git(transaction_conflict, "cherry-pick", conflict_commit, check=False)
        if conflict.returncode == 0:
            fail("conflicting writer commit unexpectedly integrated")
        git(transaction_conflict, "cherry-pick", "--abort")
        if git(integration, "rev-parse", "HEAD").stdout.strip() != integrated_side:
            fail("conflict transaction changed Approved integration HEAD")
        if git(transaction_conflict, "status", "--short").stdout:
            fail("conflict abort left transaction worktree dirty")

        (portable / "mission.md").write_text(
            "status: Verifying\nstateSequence: 3\n",
            encoding="utf-8",
        )
        (portable / "verification.md").write_text(
            "globalGates: green\nverdict: APPROVED\n",
            encoding="utf-8",
        )
        (portable / "obsolete.md").unlink()
        git(state, "add", "-A", "memory/missions/fixture")
        git(
            state,
            "commit",
            "-q",
            "-m",
            "qtim-mission-state: fixture 3 approved",
        )
        final_state_checkpoint = git(state, "rev-parse", "HEAD").stdout.strip()
        parents_final_state = git(
            source,
            "rev-list",
            "--parents",
            "-n",
            "1",
            final_state_checkpoint,
        ).stdout.split()
        if (
            len(parents_final_state) != 2
            or parents_final_state[1] != state_checkpoint_2
        ):
            fail("final portable checkpoint did not advance monotonic sequence")
        if git(state, "status", "--short").stdout:
            fail("final APPROVED portable checkpoint was not clean")
        expected_evidence_tree = git(
            state,
            "ls-tree",
            "-r",
            final_state_checkpoint,
            "--",
            "memory/missions/fixture",
        ).stdout
        expected_evidence_paths = git(
            state,
            "ls-tree",
            "-r",
            "--name-only",
            final_state_checkpoint,
            "--",
            "memory/missions/fixture",
        ).stdout.splitlines()
        if expected_evidence_paths != [
            "memory/missions/fixture/decisions.md",
            "memory/missions/fixture/mission.md",
            "memory/missions/fixture/receipts.md",
            "memory/missions/fixture/verification.md",
        ]:
            fail(f"final portable checkpoint tree is incomplete: {expected_evidence_paths}")
        final_verification = git(
            state,
            "show",
            f"{final_state_checkpoint}:memory/missions/fixture/verification.md",
        ).stdout
        if exact_verification_verdict(final_verification) != "APPROVED":
            fail("final portable checkpoint lacks APPROVED verification")
        if (
            mission_terminal_status(
                durable_status="Verifying",
                final_verdict="APPROVED",
                evidence_delivered=False,
                evidence_matches_checkpoint=False,
                done_checkpoint_clean=False,
                done_checkpoint_matches_delivery=False,
            )
            != "Verifying"
        ):
            fail("mission became Done before final evidence delivery")

        git(
            source,
            "worktree",
            "add",
            "-q",
            "--detach",
            str(transaction_evidence),
            integrated_side,
        )
        evidence_path = transaction_evidence / "memory" / "missions" / "fixture"
        if evidence_path.exists():
            shutil.rmtree(evidence_path)
        for portable_path in expected_evidence_paths:
            target = transaction_evidence / portable_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                git(
                    state,
                    "show",
                    f"{final_state_checkpoint}:{portable_path}",
                ).stdout,
                encoding="utf-8",
            )
        git(
            transaction_evidence,
            "add",
            "-A",
            "memory/missions/fixture",
        )
        git(
            transaction_evidence,
            "commit",
            "-q",
            "-m",
            "qtim-mission: deliver fixture evidence",
        )
        evidence_head = git(
            transaction_evidence,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        if (
            git(transaction_evidence, "cat-file", "-t", evidence_head)
            .stdout.strip()
            != "commit"
        ):
            fail("delivered evidence revision does not resolve to a commit")
        delivered_evidence_tree = git(
            transaction_evidence,
            "ls-tree",
            "-r",
            evidence_head,
            "--",
            "memory/missions/fixture",
        ).stdout
        if delivered_evidence_tree != expected_evidence_tree:
            fail("final evidence bundle did not exactly match checkpoint subtree")
        evidence_changed_paths = git(
            transaction_evidence,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            evidence_head,
        ).stdout.splitlines()
        if any(
            not path.startswith("memory/missions/fixture/")
            for path in evidence_changed_paths
        ):
            fail(f"final evidence bundle escaped portable scope: {evidence_changed_paths}")
        if "memory/missions/fixture/obsolete.md" not in evidence_changed_paths:
            fail("final evidence bundle did not preserve checkpoint deletion semantics")
        if (
            fenced_ff_only_promotion(
                integration,
                project_root=source,
                mission_slug="fixture",
                owner_token="coordinator",
                owner_generation=1,
                integration_target_ref=integration_target_ref,
                expected_old=integrated_side,
                transaction_head=evidence_head,
                lock_path=promotion_lock,
            )
            != "integrated"
        ):
            fail("final evidence bundle did not pass fenced promotion")
        promoted_evidence_head = git(
            integration,
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        if promoted_evidence_head != evidence_head:
            fail("promoted HEAD does not equal the evidence transaction revision")
        if (
            git(integration, "cat-file", "-t", promoted_evidence_head)
            .stdout.strip()
            != "commit"
        ):
            fail("promoted evidence HEAD does not resolve to a commit")
        integrated_evidence_tree = git(
            integration,
            "ls-tree",
            "-r",
            "HEAD",
            "--",
            "memory/missions/fixture",
        ).stdout
        if integrated_evidence_tree != expected_evidence_tree:
            fail("promoted evidence tree does not equal final clean checkpoint")
        if (
            integration / "memory" / "missions" / "fixture" / "obsolete.md"
        ).exists():
            fail("promoted evidence retained a file deleted by final checkpoint")
        delivered_verification = (
            integration / "memory" / "missions" / "fixture" / "verification.md"
        ).read_text(encoding="utf-8")
        if exact_verification_verdict(delivered_verification) != "APPROVED":
            fail("promoted evidence lacks final APPROVED verification")
        if (
            mission_terminal_status(
                durable_status="Verifying",
                final_verdict="APPROVED",
                evidence_delivered=True,
                evidence_matches_checkpoint=(
                    integrated_evidence_tree == expected_evidence_tree
                ),
                done_checkpoint_clean=False,
                done_checkpoint_matches_delivery=False,
            )
            != "Verifying"
        ):
            fail("mission became Done before the durable delivery checkpoint")
        if (
            reconcile_delivered_evidence(
                final_verdict="APPROVED",
                durable_status="Verifying",
                delivered_revision=evidence_head,
                promoted_revision=promoted_evidence_head,
                recorded_delivery_revision=None,
                evidence_matches_checkpoint=(
                    integrated_evidence_tree == expected_evidence_tree
                ),
                delivered_revision_resolves=True,
                promoted_revision_resolves=True,
            )
            != "checkpoint-done"
        ):
            fail("post-promotion crash window was not safely reconcilable")
        for invalid_revision, resolves in (
            ("", False),
            ("not-a-git-object", False),
            ("0" * 40, False),
        ):
            if (
                reconcile_delivered_evidence(
                    final_verdict="APPROVED",
                    durable_status="Verifying",
                    delivered_revision=invalid_revision,
                    promoted_revision=promoted_evidence_head,
                    recorded_delivery_revision=None,
                    evidence_matches_checkpoint=True,
                    delivered_revision_resolves=resolves,
                    promoted_revision_resolves=True,
                )
                != "blocked"
            ):
                fail(
                    "invalid delivered evidence revision allowed Done checkpoint"
                )
        if (
            reconcile_delivered_evidence(
                final_verdict="APPROVED",
                durable_status="Verifying",
                delivered_revision=integrated_side,
                promoted_revision=promoted_evidence_head,
                recorded_delivery_revision=None,
                evidence_matches_checkpoint=True,
                delivered_revision_resolves=True,
                promoted_revision_resolves=True,
            )
            != "blocked"
        ):
            fail("wrong resolved commit bypassed promoted-HEAD equality")

        # Simulate resume after a crash in the narrow window between fenced
        # evidence promotion and the terminal state checkpoint. Approved HEAD is
        # already the exact bundle, so reconciliation may write one monotonic
        # Done checkpoint and must record the delivered revision.
        (portable / "mission.md").write_text(
            "status: Done\n"
            "stateSequence: 4\n"
            f"deliveredEvidenceRevision: {evidence_head}\n",
            encoding="utf-8",
        )
        git(state, "add", "-A", "memory/missions/fixture")
        git(
            state,
            "commit",
            "-q",
            "-m",
            "qtim-mission-state: fixture 4 delivered",
        )
        done_state_checkpoint = git(state, "rev-parse", "HEAD").stdout.strip()
        parents_done_state = git(
            source,
            "rev-list",
            "--parents",
            "-n",
            "1",
            done_state_checkpoint,
        ).stdout.split()
        if (
            len(parents_done_state) != 2
            or parents_done_state[1] != final_state_checkpoint
        ):
            fail("Done checkpoint did not advance the final APPROVED checkpoint")
        if git(state, "status", "--short").stdout:
            fail("post-delivery Done checkpoint was not clean")
        delivered_mission_state = git(
            state,
            "show",
            f"{done_state_checkpoint}:memory/missions/fixture/mission.md",
        ).stdout
        if (
            "status: Done" not in delivered_mission_state
            or "stateSequence: 4" not in delivered_mission_state
            or f"deliveredEvidenceRevision: {evidence_head}"
            not in delivered_mission_state
        ):
            fail("Done checkpoint does not durably identify delivered evidence")
        if (
            mission_terminal_status(
                durable_status="Done",
                final_verdict="APPROVED",
                evidence_delivered=True,
                evidence_matches_checkpoint=(
                    integrated_evidence_tree == expected_evidence_tree
                ),
                done_checkpoint_clean=True,
                done_checkpoint_matches_delivery=(
                    f"deliveredEvidenceRevision: {evidence_head}"
                    in delivered_mission_state
                ),
            )
            != "Done"
        ):
            fail("mission did not reach durable Done after evidence delivery")
        if (
            reconcile_delivered_evidence(
                final_verdict="APPROVED",
                durable_status="Done",
                delivered_revision=evidence_head,
                promoted_revision=promoted_evidence_head,
                recorded_delivery_revision=evidence_head,
                evidence_matches_checkpoint=True,
                delivered_revision_resolves=True,
                promoted_revision_resolves=True,
            )
            != "noop"
        ):
            fail("matching Done checkpoint was not idempotent")
        if (
            reconcile_delivered_evidence(
                final_verdict="APPROVED",
                durable_status="Done",
                delivered_revision=evidence_head,
                promoted_revision=promoted_evidence_head,
                recorded_delivery_revision=integrated_side,
                evidence_matches_checkpoint=True,
                delivered_revision_resolves=True,
                promoted_revision_resolves=True,
            )
            != "blocked"
        ):
            fail("mismatched durable delivery revision was accepted")
        if (
            reconcile_delivered_evidence(
                final_verdict="APPROVED",
                durable_status="Done",
                delivered_revision=evidence_head,
                promoted_revision=promoted_evidence_head,
                recorded_delivery_revision="",
                evidence_matches_checkpoint=True,
                delivered_revision_resolves=True,
                promoted_revision_resolves=True,
            )
            != "blocked"
        ):
            fail("empty recorded delivery revision was accepted")
        if git(state, "rev-parse", "HEAD").stdout.strip() != done_state_checkpoint:
            fail("idempotent Done reconciliation created an extra checkpoint")
        if git(integration, "status", "--short").stdout:
            fail("transaction flow left Approved integration worktree dirty")


def check_contract_files() -> None:
    require(
        "plugins/qtim/skills/qtim-mission/SKILL.md",
        "AUTO-START", "PREVIEW", "RECOMMEND", "clientThreadId",
        "isolated-worktree-writer", "git cherry-pick", "execution: lazy",
        "expectedBase",
        "ESCALATION_REQUEST", "APPROVED", "NOT APPROVED",
        "detached", "transaction", "compare-and-swap", "coordinator ownership",
        "status <slug>", "resume <slug>", "stop <slug>",
        "несколько отдельных Codex", "planning/evaluation-only",
        "quoted command", "отложенное намерение",
        "terminalVerifier.dependsOn", "deliveredEvidenceRevision",
        "canonical safe", "идемпотентно", "App worktree не",
        "detached HEAD",
        "raw filesystem", "common-control", "coordinator-owned monotonic journal",
        "symlink/junction", "Per-worktree Git admin", "50 000", "512 MiB",
        "WRITER PREFLIGHT READY", "preflight-ready", "GIT_OPTIONAL_LOCKS=0",
        ".ownership.lock", ".promotion.lock", "common `.git/worktrees/*`",
        "submodule topology", "atomic no-clobber", "ownership -> promotion",
        "regular content file", "nested common config/control/hooks/",
    )
    require(
        "plugins/qtim/reference/mission-protocol.md",
        "list_threads", "wait_threads", "read_thread", "configured default",
        "topological order", "handoff_thread", "affected gate",
        "expectedBase", "clean-context", "detached transaction",
        "compare-and-swap", "coordinator ownership", "status", "resume", "stop",
        "terminalVerifier.dependsOn", "deliveredEvidenceRevision",
        "canonical safe", "идемпотентно", "shared writer ref",
        "symbolic-ref -q HEAD",
        "common-control", "coordinator-owned journal", "50 000", "512 MiB",
        "per-worktree admin snapshot",
        "WRITER PREFLIGHT READY", "GIT_OPTIONAL_LOCKS=0",
        ".ownership.lock", ".promotion.lock", "common `.git/worktrees/*`",
        "submodule", "atomic no-clobber", "ownership -> promotion",
        "regular writer content file",
    )
    require(
        "plugins/qtim/reference/mission-receipt.md",
        "WORKER RECEIPT", "INTEGRATION RECEIPT", "MISSION VERIFICATION",
        "succeeded -> validated", "expectedBase", "non-merge commit",
        "ESCALATION_REQUEST", "transaction-worktree", "approved local roles",
        "scope overlap", "product fork", "canonical safe repo-relative",
        "deliveredEvidenceRevision", "writer HEAD equals commit",
        "common git control files unchanged", "target scopes contained",
        "coordinator-owned journal", "50 000", "512 MiB",
        "read-only per-worktree git control unchanged",
        "WRITER PREFLIGHT READY", "assigned Git admin identity unchanged",
        "common worktree admin", "submodule state", "GIT_OPTIONAL_LOCKS=0",
        "regular content file", "nested admin identity",
    )
    require(
        "plugins/qtim/reference/mission-state-schema.md",
        "memory/missions/<slug>/", ".codex/qtim-runtime/missions/<slug>.json",
        "clientThreadId", "expectedBase", "integrated", "live", "pending", "stale", "orphan",
        "ambiguous", "unavailable", "blocked", "generation", "takeover", "Done",
        "deliveredEvidenceRevision", "Post-delivery reconciliation",
        "detached", "shared attempt refs", "refJournal",
        "preflight-ready", ".ownership.lock", ".promotion.lock",
        "same filesystem", "registry transition", "atomic no-clobber",
        "ownership -> promotion", "regular single-link registry",
    )
    require(
        "plugins/qtim/skills/qtim-team-lazy/SKILL.md",
        "Mission-child mode", "minimum-sufficient", "WORKER RECEIPT",
        "ESCALATION_REQUEST", "третий уровень", "standalone lazy mode",
    )
    require(
        "plugins/qtim/reference/feature-pipeline.md",
        "Что запускать дальше", "$qtim-mission", "Рекомендация", "Топология",
        "Альтернатива", "base/integration target", "RECOMMEND",
    )
    require(
        "plugins/qtim/skills/qtim-feature/SKILL.md",
        "../../reference/feature-pipeline.md", "Execution Recommendation Gate",
        "dev track/writers", "RECOMMEND", "Approved preview",
    )
    require(
        "plugins/qtim/skills/qtim-setup/SKILL.md",
        "Что запускать дальше", "$qtim-mission", "memory/missions/<slug>/",
        ".codex/qtim-runtime/", "topological integration",
    )
    require(
        "plugins/qtim/skills/qtim-doctor/SKILL.md",
        "validated/integrated", "topological receipt", "exact ignore",
        "stale/orphan/ambiguous/unavailable",
    )
    require(
        "plugins/qtim/skills/qtim-team-down/SKILL.md",
        "$qtim-mission, status|resume <slug>", "peer mission tasks",
        "handles запрещено копировать",
    )
    require(
        "plugins/qtim/reference/upgrade-notes.md",
        "## 2.12.0", "Миграция с 2.11.0", "qtim:track:pm:start/end",
        "memory/missions/<slug>/", ".codex/qtim-runtime/",
    )
    require(
        "plugins/qtim/hooks/session-start.sh",
        "qtim mission advisory", "Ничего не запущено",
        "$qtim-mission, resume <slug>", "head -n 51",
        "qtim-mission-state-$slug",
    )
    require(
        "examples/fullstack-codex/.codex/team-charter.md",
        "Что запускать дальше", "$qtim-mission", "recommendation ничего не запускает",
        "integrate topologically", "clean-context verifier",
    )
    require(
        "examples/fullstack-codex/AGENTS.md",
        "$qtim-mission", "worktree", "topologically", "workers не создают descendants",
    )
    require(
        "examples/fullstack-codex/.gitignore",
        ".codex/qtim-runtime/",
    )
    if read(".gitignore").splitlines().count(".codex/qtim-runtime/") != 1:
        fail("root .gitignore must contain exactly one qtim runtime entry")
    require(
        "examples/fullstack-codex/memory/MEMORY.md",
        "memory/missions/<slug>/", "явно запущенная mission",
        "несколько Codex peer tasks как одну mission",
    )
    require(
        "plugins/qtim/skills/qtim-mission/agents/openai.yaml",
        'default_prompt: "', "$qtim-mission", "allow_implicit_invocation: true",
    )
    require(
        "docs/cross-dialog-missions/mission-plan-codex.md",
        "APPROVED -> exact evidence bundle -> fenced delivery",
        "durable Done checkpoint с delivered revision",
        "deliveredEvidenceRevision",
        "validated -> verified (read-only)",
        "validated -> integrated -> verified (writer)",
        "atomic no-clobber",
        "Реальные Windows junctions",
    )
    require_order(
        "docs/cross-dialog-missions/mission-plan-codex.md",
        "APPROVED -> exact evidence bundle -> fenced delivery",
        "durable Done checkpoint с delivered revision",
        "mission Done",
    )
    require(
        "docs/cross-dialog-missions/plan-review-board.html",
        "APPROVED → evidence bundle",
        "Fenced delivery → Done checkpoint",
        "Delivered revision recorded",
        "read-only: validated → verified",
        "writer: validated → integrated → verified",
    )
    require_order(
        "docs/cross-dialog-missions/plan-review-board.html",
        "APPROVED → evidence bundle",
        "Fenced delivery → Done checkpoint",
        "Delivered revision recorded",
    )
    require(
        ".github/workflows/validate.yml",
        "check_missions.py --windows-filesystem-only",
    )
    require(
        "docs/cross-dialog-missions/app-smoke-receipt.md",
        "WRITER PREFLIGHT READY",
        "4388538c2031349a397d2d80fbcad590edb362d0",
        "READY -> coordinator baseline -> exact follow-up",
    )


def main() -> None:
    if sys.argv[1:] == ["--windows-filesystem-only"]:
        check_windows_junction_fixtures()
        print("OK: Windows mission junction fixtures are valid")
        return
    if sys.argv[1:]:
        fail(f"unsupported mission validator arguments: {sys.argv[1:]}")
    check_contract_files()
    check_activation_fixtures()
    check_routing_fixtures()
    check_dag_and_state_fixtures()
    check_writer_and_lazy_fixtures()
    check_recovery_fixtures()
    check_git_integration_fixture()
    print("OK: complete qtim mission contracts and semantic fixtures are valid")


if __name__ == "__main__":
    main()
