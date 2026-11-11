#!/usr/bin/env python3
"""Feature-local state guard. JSON stdin; no App calls, Git writes, or takeover.

Commands share --root, --feature, --repository. init/transition additionally
require --owner-thread/--owner-host; transition requires --expected-sequence.
status/resume are read-only. init consumes {plan, decision}; transition consumes
{event, ...event fields}. See the executable CLI fixtures for payload examples.
A successful launch response is a single dispatch checkpoint, never replayed by
status/resume. External evidence is a coordinator attestation, not a sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import uuid

SCHEMA = "qtim-feature-state/2"
LIMIT = 4 * 1024 * 1024


class GuardError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def need(ok, message, code="invalid"):
    if not ok:
        raise GuardError(code, message)


def text(value):
    need(type(value) is str and bool(value.strip()) and "\x00" not in value, "expected nonempty string")


def number(value):
    need(type(value) is int and value >= 0, "expected nonnegative integer")


def positive(value):
    number(value)
    need(value > 0, "expected positive integer")


def pattern(expression):
    def validate(value):
        text(value)
        need(re.fullmatch(expression, value) is not None, "invalid identifier/hash")
    return validate


SHA = pattern(r"[0-9a-f]{64}")
COMMIT = pattern(r"[0-9a-f]{40}")
TICKET = pattern(r"T[0-9]{2,}")
STAGE = pattern(r"S[1-9][0-9]*")
FEATURE_AC = pattern(r"AC-[0-9]{2,}")
AC = pattern(r"T[0-9]{2,}-AC[1-9][0-9]*")
SLUG = pattern(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def relative(value):
    text(value)
    path = PurePosixPath(value)
    need(not path.is_absolute() and path.parts and ".." not in path.parts
         and path.as_posix() == value and "\\" not in value, "unsafe relative path")


def absolute(value):
    text(value)
    need(Path(value).is_absolute() and str(Path(value)) == value, "expected canonical absolute path")


def mapping(spec):
    def validate(value):
        need(type(value) is dict, "expected object")
        for key, item in value.items():
            text(key)
            shape(item, spec)
    return validate


def shape(value, spec):
    if isinstance(spec, dict):
        need(type(value) is dict and set(value) == set(spec), "missing/unknown object fields")
        for key, field in spec.items():
            try:
                shape(value[key], field)
            except GuardError as err:
                raise GuardError(err.code, key + ": " + str(err)) from err
    elif isinstance(spec, list):
        need(type(value) is list, "expected array")
        for item in value:
            shape(item, spec[0])
    elif isinstance(spec, tuple):
        if value is not None:
            shape(value, spec[0])
    elif isinstance(spec, set):
        need(type(value) is str and value in spec, "unknown enum value")
    elif spec is bool:
        need(type(value) is bool, "expected boolean")
    else:
        spec(value)


def optional_fields(required, **optional):
    def validate(value):
        need(type(value) is dict, "expected object")
        shape(value, {**required, **{k: spec for k, spec in optional.items() if k in value}})
    return validate


REF = {"path": relative, "sha256": SHA}
SOURCE = {"revision": positive, "file": REF}
OWNER = {"thread": text, "host": text}
AUTHORITY = {"feature": SLUG, "repository": text, "root": absolute,
             "ledger": absolute, "lock": absolute, "device": number, "inode": positive,
             "owner": OWNER}
DECISION = {"id": text, "statement": text, "evidence": REF, "scope_sha256": SHA}
FILE = {"workspace": number, "path": relative, "sha256": (SHA,)}
SNAPSHOT = {"patch": REF, "files": [FILE], "untracked": [FILE], "sha256": SHA}
WORKSPACE = {"repository": text, "worktree": absolute, "base": COMMIT,
             "write_paths": [relative], "git_actions": [{"commit", "push", "integrate", "merge", "release", "deploy"}]}
SPAN = {"start": number, "end": positive}
TASK = optional_fields({"id": TICKET, "stage": STAGE, "source": SOURCE, "requires": [TICKET],
        "scope": {"spec": [SPAN], "adr": [SPAN]},
        "acs": [{"id": AC, "feature_acs": [FEATURE_AC], "required": bool}], "review_required": bool}, owner_stop={"condition": text, "decision": text})
PLAN = optional_fields({"spec": SOURCE, "adr": (SOURCE,), "feature_acs": [FEATURE_AC], "queue": [TICKET],
        "tickets": [TASK], "stages": [{"id": STAGE, "required": [TICKET], "gates": [text]}],
        "final_gates": [text], "workspaces": [WORKSPACE], "input": SNAPSHOT}, acceptance={"stage"})
BUDGET = {"full_limit": positive, "fix_limit": number, "full_used": number, "fix_used": number}
PEER = {"thread": text, "host": text}
INTENT = {"marker": text, "project": text, "context_sha256": SHA, "decision": (DECISION,)}
BINDING = {"marker": text, "project": text, "context_sha256": SHA, "peer": PEER}
RELEASE = {"peer": PEER, "handles": [text], "verified_stopped": bool,
           "worker_turn_finished": bool, "evidence": REF, "result": SNAPSHOT,
           "write_go": (text,)}
RECEIPT = {"revision": positive, "file": REF, "ticket": TICKET, "attempt": positive,
           "source_sha256": SHA, "write_go": text, "result": SNAPSHOT,
           "acs": [{"id": AC, "verdict": {"PASS", "FAIL", "BLOCKED"},
                    "expected": text, "actual": text, "evidence": [REF]}],
           "checks": [{"command": text, "exit_code": number, "evidence": REF}],
           "review": {"id": (text,), "verdict": {"APPROVED", "NOT_REQUIRED", "CHANGES_REQUESTED", "FAILED"}, "evidence": REF,
                      "findings": [{"id": text, "disposition": {"fixed", "rejected"}, "evidence": REF}]}}
VERIFICATION = {"stop": bool, "evidence": REF}
SATISFIED = {"Accepted", "Verified"}
ATTEMPT = optional_fields({"ticket": TICKET, "number": positive,
           "state": {"Launching", "Running", "Awaiting acceptance", "Accepted", "Verified", "Blocked", "Stopped", "Deferred"},
           "plan_sha256": SHA, "source_sha256": SHA, "intent": INTENT, "input": SNAPSHOT, "workspaces": [WORKSPACE],
           "dependencies": [{"ticket": TICKET, "source_sha256": SHA, "receipt": REF, "result_sha256": SHA}],
           "pending": (text,), "peer": (PEER,),
           "preflight": (REF,), "write_go": (text,), "receipt": (RECEIPT,),
           "release": (RELEASE,), "acceptance": (DECISION,)}, verification=VERIFICATION)
GATE = optional_fields({"stage": (STAGE,), "id": text, "plan_sha256": SHA, "evidence": REF}, result_sha256=SHA)
FAILED_GATE = {"id": text, "evidence": REF}
STAGE_DECISION = optional_fields({"stage": STAGE, "plan_sha256": SHA, "result_sha256": SHA,
                                  "action": {"accept", "accept-and-advance", "advance", "reject"},
                                  "target": (TICKET,), "decision": DECISION}, failed_gate=FAILED_GATE)
HISTORY = {"sequence": number, "event": text, "ticket": (TICKET,), "attempt": (positive,),
           "from": text, "to": text, "reason": text, "payload_sha256": SHA}
ENDPOINT = {"ticket": TICKET, "ac": AC}
MOVE = {"from": ENDPOINT, "to": ENDPOINT}
DEPENDENCY_REMAP = {"ticket": TICKET, "from": [TICKET], "to": [TICKET], "evidence": REF}
STAGE_REMAP = {"from": STAGE, "to": [STAGE], "evidence": REF}
GATE_KEY = {"stage": (STAGE,), "id": text}
GATE_REMAP = {"from": GATE_KEY, "to": GATE_KEY, "evidence": REF}
ARCHIVE = {"original": REF, "copy": REF}
REUSE = {"ticket": TICKET, "accepted_attempt": positive, "accepted_plan_sha256": SHA,
         "accepted_source_sha256": SHA, "receipt": REF, "result_sha256": SHA,
         "release_sha256": SHA, "target_plan_sha256": SHA, "observed": SNAPSHOT,
         "archived_sources": [ARCHIVE], "evidence": REF}
CHANGE_FIELDS = {"plan": PLAN, "moves": [MOVE], "dependencies": [DEPENDENCY_REMAP],
                 "stages": [STAGE_REMAP], "gates": [GATE_REMAP], "reuse": [REUSE], "decision": DECISION}
CHANGE = {"sequence": positive, "from_plan": SHA, "to_plan": SHA, "ticket": (TICKET,),
          "mode": {"revise", "partial", "defer"}, "moves": [MOVE],
          "dependencies": [DEPENDENCY_REMAP], "stages": [STAGE_REMAP], "gates": [GATE_REMAP],
          "reuse": [REUSE], "decision": DECISION}
REVIEW = {"id": text, "phase": {"reserved", "completed"}, "kind": {"full", "fix"},
          "ticket": TICKET, "attempt": positive, "write_go": text, "source_sha256": SHA,
          "candidate": SNAPSHOT, "pools": [text], "binding_sha256": SHA, "quiescence": REF,
          "verdict": ({"APPROVED", "CHANGES_REQUESTED", "FAILED"},),
          "evidence": (REF,), "observation": (REF,)}
STATE = optional_fields({"schema": {SCHEMA}, "authority": AUTHORITY, "sequence": number, "plan": PLAN,
         "current": (TICKET,), "attempts": [ATTEMPT], "budgets": mapping(BUDGET),
         "ticket_pools": mapping([text]), "reviews": [REVIEW], "plans": mapping(PLAN),
         "changes": [CHANGE], "deferred": mapping(SHA),
         "gates": [GATE], "decisions": [DECISION], "history": [HISTORY], "done": bool}, stage_decisions=[STAGE_DECISION])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(data):
    need(len(data) <= LIMIT, "JSON exceeds size limit")
    try:
        return json.loads(data, object_pairs_hook=no_duplicates,
                          parse_constant=lambda _x: (_ for _ in ()).throw(GuardError("invalid", "invalid JSON constant")))
    except (ValueError, UnicodeError) as err:
        raise GuardError("invalid", "invalid JSON: " + str(err)) from err


class Directory:
    """Descriptor-relative no-follow access; a renamed/symlinked child cannot escape."""
    def __init__(self, path):
        absolute(path)
        need(os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
             and os.open in os.supports_dir_fd, "safe filesystem primitives unavailable", "unavailable")
        self.path = Path(path)
        need(str(self.path.resolve(strict=True)) == path, "root contains symlink/noncanonical components")
        self.fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.stat = os.fstat(self.fd)

    def check(self):
        info = os.stat(self.path, follow_symlinks=False)
        need(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (self.stat.st_dev, self.stat.st_ino)
             and str(self.path.resolve(strict=True)) == str(self.path), "canonical root changed", "conflict")

    def close(self):
        os.close(self.fd)

    def parent(self, name):
        relative(name)
        parts = PurePosixPath(name).parts
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise

    def read(self, name, missing=False):
        parent, leaf = self.parent(name)
        try:
            try:
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                if missing:
                    return None
                raise
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "expected singly linked regular file")
                data = stream.read(LIMIT + 1)
                need(len(data) <= LIMIT, "file exceeds size limit")
                return data
        finally:
            os.close(parent)


def verify_ref(root, ref):
    shape(ref, REF)
    need(digest(root.read(ref["path"])) == ref["sha256"], "stale artifact: " + ref["path"], "blocked")


def unique(values, what):
    need(len(values) == len(set(values)), "duplicate " + what)


def tasks(plan):
    return {item["id"]: item for item in plan["tickets"]}


def source_identity(plan, ticket):
    return identity({"spec": plan["spec"], "adr": plan["adr"], "ticket": tasks(plan)[ticket],
                     "workspaces": plan["workspaces"],
                     "prerequisites": {t: source_identity(plan, t) for t in tasks(plan)[ticket]["requires"]}})


def snapshot_identity(plan, snapshot):
    return identity({"workspaces": plan["workspaces"], "patch": snapshot["patch"]["sha256"],
                     "files": snapshot["files"], "untracked": snapshot["untracked"]})


def snapshot(root, plan, value, check_files=True, scope=False):
    shape(value, SNAPSHOT)
    verify_ref(root, value["patch"])
    need(value["sha256"] == snapshot_identity(plan, value), "snapshot identity mismatch", "blocked")
    names = [(item["workspace"], item["path"]) for item in value["files"]]
    unique(names, "snapshot file")
    unique([(item["workspace"], item["path"]) for item in value["untracked"]], "untracked file")
    need(all(item in value["files"] and item["sha256"] is not None for item in value["untracked"]), "invalid untracked membership")
    baseline = plan.get("baseline", plan.get("input", {})).get("files", [])
    if scope:
        need({(i["workspace"], i["path"]) for i in baseline} <= set(names), "result omits baseline file", "blocked")
    for item in value["files"]:
        need(item["workspace"] < len(plan["workspaces"]), "unknown workspace")
        workspace = plan["workspaces"][item["workspace"]]
        if scope:
            need(any(item["path"] == path or item["path"].startswith(path + "/")
                     for path in workspace["write_paths"]) or item in baseline, "result outside write scope", "blocked")
        if check_files:
            directory = Directory(workspace["worktree"])
            try:
                data = directory.read(item["path"], missing=True)
                need((None if data is None else digest(data)) == item["sha256"],
                     "stale workspace file: " + item["path"], "blocked")
                directory.check()
            finally:
                directory.close()


def validate_plan(root, plan):
    shape(plan, PLAN)
    table = tasks(plan)
    need(plan.get("acceptance") == "stage" or not any("owner_stop" in t for t in table.values()),
         "ticket owner stop requires stage acceptance")
    need(table and plan["queue"] and plan["workspaces"], "empty execution plan")
    unique([t["id"] for t in plan["tickets"]], "ticket")
    unique(plan["queue"], "queue ticket")
    need(set(plan["queue"]) == set(table), "queue does not cover tickets")
    stages = {s["id"]: s for s in plan["stages"]}
    unique([s["id"] for s in plan["stages"]], "stage")
    unique(plan["feature_acs"], "feature AC")
    need(plan["feature_acs"], "empty feature AC coverage")
    feature_coverage = set()
    visiting, visited = set(), set()
    def visit(ticket):
        need(ticket not in visiting, "dependency cycle")
        if ticket in visited:
            return
        visiting.add(ticket)
        for predecessor in table[ticket]["requires"]:
            need(predecessor in table and predecessor != ticket, "missing/self dependency")
            need(plan["queue"].index(predecessor) < plan["queue"].index(ticket), "dependency follows ticket in queue")
            visit(predecessor)
        visiting.remove(ticket)
        visited.add(ticket)
    for ticket, task in table.items():
        need(task["stage"] in stages and task["acs"], "missing stage/AC")
        need(task["scope"]["spec"] and bool(task["scope"]["adr"]) == (plan["adr"] is not None), "missing declared source scope")
        for spans in task["scope"].values():
            end = 0
            for span in spans:
                need(end <= span["start"] < span["end"], "invalid/overlapping source spans")
                end = span["end"]
        unique(task["requires"], "dependency")
        unique([a["id"] for a in task["acs"]], "ticket AC")
        for ac in task["acs"]:
            need(ac["id"].startswith(ticket + "-AC") and ac["feature_acs"], "invalid AC ownership")
            unique(ac["feature_acs"], "AC link")
            need(set(ac["feature_acs"]) <= set(plan["feature_acs"]), "unknown feature AC")
            if ac["required"]:
                feature_coverage.update(ac["feature_acs"])
        visit(ticket)
    need(feature_coverage == set(plan["feature_acs"]), "uncovered feature AC")
    order = [table[t]["stage"] for t in plan["queue"]]
    need([s for i, s in enumerate(order) if i == 0 or s != order[i-1]] == list(stages), "stage order must be contiguous")
    for stage in plan["stages"]:
        unique(stage["required"], "required ticket")
        unique(stage["gates"], "stage gate")
        need(stage["required"] and all(t in table and table[t]["stage"] == stage["id"] for t in stage["required"]), "invalid required membership")
    required = {t for stage in plan["stages"] for t in stage["required"]}
    need(all(t in required for t, task in table.items() if any(a["required"] for a in task["acs"])), "required AC owner is not a required ticket")
    need(plan["final_gates"], "missing final integration gate")
    unique(plan["final_gates"], "final gate")
    unique([w["worktree"] for w in plan["workspaces"]], "workspace")
    for workspace in plan["workspaces"]:
        directory = Directory(workspace["worktree"])
        directory.close()
        unique(workspace["write_paths"], "write path")
        unique(workspace["git_actions"], "Git action")
    snapshot(root, plan, plan["input"], check_files=False)


def last(state, ticket=None):
    ticket = state["current"] if ticket is None else ticket
    return next((a for a in reversed(state["attempts"]) if a["ticket"] == ticket), None)


def dependencies(state, ticket):
    result = []
    for predecessor in tasks(state["plan"])[ticket]["requires"]:
        prior = last(state, predecessor)
        need(prior is not None and prior["receipt"] is not None, "missing prerequisite receipt", "blocked")
        result.append({"ticket": predecessor, "source_sha256": prior["source_sha256"],
                       "receipt": prior["receipt"]["file"], "result_sha256": prior["receipt"]["result"]["sha256"]})
    return result


def ticket_ready(state, ticket):
    attempt = last(state, ticket)
    reused = any(r["ticket"] == ticket and r["accepted_attempt"] == attempt["number"]
                 for c in state["changes"] if c["to_plan"] == identity(state["plan"])
                 for r in c["reuse"]) if attempt else False
    return bool(attempt and attempt["state"] in SATISFIED
                and (attempt["verification"] if attempt["state"] == "Verified" else attempt["acceptance"])
                and (attempt["source_sha256"] == source_identity(state["plan"], ticket) or reused)
                and all(ticket_ready(state, t) for t in tasks(state["plan"])[ticket]["requires"])
                and attempt["dependencies"] == dependencies(state, ticket))


def current_state(state):
    if state["done"]:
        return "Done"
    attempt = last(state)
    if state["current"] in state["deferred"]:
        return "Deferred"
    if attempt and attempt["state"] in SATISFIED and not ticket_ready(state, attempt["ticket"]):
        return "Blocked"
    return attempt["state"] if attempt else "Planned"


def verify_sources(root, plan):
    for source in [plan["spec"], plan["adr"]] + [t["source"] for t in plan["tickets"]]:
        if source is not None:
            verify_ref(root, source["file"])
    for task in plan["tickets"]:
        source_slices(root, plan, task, [])


def released(root, state, attempt, check_files=True):
    need(attempt is not None and attempt["release"] is not None, "writer release required", "blocked")
    release = attempt["release"]
    need(release["verified_stopped"] and release["worker_turn_finished"]
         and release["peer"] == attempt["peer"] and release["write_go"] == attempt["write_go"], "unverified writer release", "blocked")
    verify_ref(root, release["evidence"])
    snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]}, release["result"], check_files=check_files, scope=True)
    return release


def verify_handoff(root, state):
    need(not any(r["phase"] == "reserved" for r in state["reviews"]), "unresolved review reservation", "blocked")
    for index, previous in enumerate(state["attempts"]):
        # Earlier receipts describe intermediate code; only the last writer owns today's workspace.
        released(root, state, previous, check_files=index == len(state["attempts"]) - 1)


def receipt(root, state, attempt, historical=False):
    value = attempt["receipt"]
    plan = state["plans"][attempt["plan_sha256"]] if historical else state["plan"]
    need(value is not None, "validated receipt required", "blocked")
    need(value["ticket"] == attempt["ticket"] and value["attempt"] == attempt["number"]
         and value["source_sha256"] == attempt["source_sha256"] == source_identity(plan, attempt["ticket"])
         and value["write_go"] == attempt["write_go"], "stale receipt binding", "blocked")
    verify_ref(root, value["file"])
    snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]}, value["result"], check_files=not historical, scope=True)
    requirements = {a["id"]: a for a in tasks(plan)[attempt["ticket"]]["acs"]}
    unique([a["id"] for a in value["acs"]], "receipt AC")
    actual = {a["id"]: a for a in value["acs"]}
    need(set(actual) == set(requirements), "receipt AC coverage mismatch", "blocked")
    for key, requirement in requirements.items():
        ac = actual[key]
        need(not requirement["required"] or (ac["verdict"] == "PASS" and ac["evidence"]), "mandatory AC unproven", "blocked")
        for ref in ac["evidence"]:
            verify_ref(root, ref)
    need(value["checks"], "missing verification checks", "blocked")
    for check in value["checks"]:
        need(check["exit_code"] == 0, "failed mandatory check", "blocked")
        verify_ref(root, check["evidence"])
    reviews = [r for r in state["reviews"] if r["ticket"] == attempt["ticket"] and r["attempt"] == attempt["number"] and r["write_go"] == attempt["write_go"]]
    need(not any(r["phase"] == "reserved" for r in reviews), "required completed independent review missing/stale", "blocked")
    if tasks(plan)[attempt["ticket"]]["review_required"] or reviews:
        proof = next((r for r in reversed(reviews) if r["source_sha256"] == value["source_sha256"]
                      and r["candidate"]["sha256"] == value["result"]["sha256"]), None)
        need(proof is not None and proof["id"] == value["review"]["id"]
             and proof["phase"] == "completed" and proof["verdict"] == value["review"]["verdict"] == "APPROVED"
             and proof["ticket"] == attempt["ticket"] and proof["attempt"] == attempt["number"]
             and proof["write_go"] == attempt["write_go"] and proof["source_sha256"] == value["source_sha256"]
             and proof["candidate"]["sha256"] == value["result"]["sha256"] and proof["evidence"] == value["review"]["evidence"],
             "required completed independent review missing/stale", "blocked")
    elif plan.get("acceptance") == "stage":
        need(value["review"]["verdict"] == "NOT_REQUIRED" and value["review"]["id"] is None,
             "unverified review verdict", "blocked")
    verify_ref(root, value["review"]["evidence"])
    for finding in value["review"]["findings"]:
        verify_ref(root, finding["evidence"])
    release = released(root, state, attempt, check_files=not historical)
    need(release["result"] == value["result"], "release/result mismatch", "blocked")
    return value


def source_slices(root, plan, task, archives):
    result = {}
    for name in ("spec", "adr"):
        source = plan[name]
        if source is None:
            result[name] = []
            continue
        ref = source["file"]
        copies = [a["copy"] for a in archives if a["original"] == ref]
        need(len(copies) <= 1, "duplicate archived source")
        selected = copies[0] if copies else ref
        need(selected["sha256"] == ref["sha256"], "archive changes historical source", "blocked")
        verify_ref(root, selected)
        data = root.read(selected["path"])
        result[name] = []
        for span in task["scope"][name]:
            need(span["end"] <= len(data), "source span outside artifact", "blocked")
            part = data[span["start"]:span["end"]]
            part.decode("utf-8")
            result[name].append(part)
    return result


def review_binding(review):
    return identity({k: review[k] for k in ("id", "ticket", "attempt", "write_go", "source_sha256", "candidate", "pools", "kind")})


def gate_keys(plan):
    return {(s["id"], g) for s in plan["stages"] for g in s["gates"]} | {(None, g) for g in plan["final_gates"]}


def endpoint(value):
    return value["ticket"], value["ac"]


def conserve(root, old, new, moves, dependency_remaps, stage_remaps, gate_remaps, prior_links=None):
    need(old.get("acceptance") == new.get("acceptance"), "acceptance mode cannot change in an existing run", "blocked")
    prior, table = tasks(old), tasks(new)
    need(set(prior) <= set(table), "stable ticket IDs cannot be removed", "blocked")
    need(set(old["feature_acs"]) <= set(new["feature_acs"]), "feature obligation removed", "blocked")
    by_ac = {(t, a["id"]): a for t, task in prior.items() for a in task["acs"]}
    new_ac = {(t, a["id"]): a for t, task in table.items() for a in task["acs"]}
    unique([endpoint(m["from"]) for m in moves], "source move")
    links = {endpoint(m["from"]): endpoint(m["to"]) for m in moves}
    for source, target in links.items():
        need(source != target and source in by_ac and by_ac[source]["required"], "unknown/nonrequired source move", "blocked")
        need(target in new_ac and new_ac[target]["required"], "receiving AC must exist and be required", "blocked")
        need(set(by_ac[source]["feature_acs"]) <= set(new_ac[target]["feature_acs"]), "receiving AC loses feature links", "blocked")
        need(not prior[source[0]]["review_required"] or table[target[0]]["review_required"], "transfer removes review boundary", "blocked")
        if target[0] in prior:
            need(table[target[0]]["source"]["revision"] > prior[target[0]]["source"]["revision"], "receiving ticket needs a fresh revision", "blocked")
    receiving_links = {}
    for target in set(links.values()):
        features = set(by_ac[target]["feature_acs"]) if target in by_ac else set()
        for source, receiving in links.items():
            if receiving == target:
                features.update(by_ac[source]["feature_acs"])
        need(set(new_ac[target]["feature_acs"]) == features, "receiving AC adds unrelated feature links", "blocked")
        receiving_links[target] = features
    for key, ac in by_ac.items():
        expected = {**ac, "required": False} if key in links else ac
        actual = new_ac.get(key)
        if key in receiving_links and actual is not None:
            actual = {**actual, "feature_acs": ac["feature_acs"]}
        need(actual == expected, "ticket AC lost/changed without unique move: " + key[1], "blocked")
    for ticket in set(table) - set(prior):
        need({(ticket, a["id"]) for a in table[ticket]["acs"]} <= set(links.values()), "new receiving ticket adds unrelated AC", "blocked")
    lineage = {**(prior_links or {}), **links}
    def owner(key):
        seen = set()
        while key in lineage:
            need(key not in seen, "transfer provenance cycle", "blocked")
            seen.add(key)
            key = lineage[key]
        return key[0]
    def owners(ticket):
        required = [(ticket, a["id"]) for a in prior[ticket]["acs"] if a["required"] or (ticket, a["id"]) in lineage]
        return {owner(key) for key in required} or {ticket}
    unique([r["ticket"] for r in dependency_remaps], "dependency remap")
    changed_deps = {t for t in prior if prior[t]["requires"] != table[t]["requires"]}
    need({r["ticket"] for r in dependency_remaps} == changed_deps, "unaccounted dependency remap", "blocked")
    for remap in dependency_remaps:
        ticket = remap["ticket"]
        verify_ref(root, remap["evidence"])
        need(remap["from"] == prior[ticket]["requires"] and remap["to"] == table[ticket]["requires"], "dependency remap binding mismatch", "blocked")
        required = set().union(*(owners(t) for t in remap["from"]))
        need(required <= set(remap["to"]), "dependency remap loses producer obligations", "blocked")
    for task in prior.values():
        for producer in task["requires"]:
            if any(a["required"] for a in table[producer]["acs"]):
                need(owners(producer) <= set(table[task["id"]]["requires"]), "partial producer requires an explicit dependency remap", "blocked")
    for move in moves:
        donor, receiver = move["from"]["ticket"], move["to"]["ticket"]
        inherited = set().union(*(owners(t) for t in prior[donor]["requires"]))
        need(inherited <= set(table[receiver]["requires"]), "receiver loses technical prerequisite", "blocked")
    old_stages = {s["id"]: s for s in old["stages"]}
    new_stages = {s["id"]: s for s in new["stages"]}
    changed_stages = {s for s in old_stages if old_stages[s] != new_stages.get(s)}
    changed_stages.update(prior[m["from"]["ticket"]]["stage"] for m in moves
                          if prior[m["from"]["ticket"]]["stage"] != table[m["to"]["ticket"]]["stage"])
    unique([r["from"] for r in stage_remaps], "stage remap")
    need({r["from"] for r in stage_remaps} == changed_stages, "unaccounted stage boundary remap", "blocked")
    for remap in stage_remaps:
        verify_ref(root, remap["evidence"])
        unique(remap["to"], "replacement stage")
        need(remap["to"] and set(remap["to"]) <= set(new_stages), "missing replacement stage", "blocked")
        required = set().union(*(owners(t) for t in old_stages[remap["from"]]["required"]))
        provided = {t for s in remap["to"] for t in new_stages[s]["required"]}
        need(required <= provided, "stage remap loses required obligation owners", "blocked")
    for ticket, task in prior.items():
        current = table[ticket]
        need(not task["review_required"] or current["review_required"], "review requirement removed", "blocked")
        if task["stage"] != current["stage"]:
            need(any(r["from"] == task["stage"] and current["stage"] in r["to"] for r in stage_remaps), "ticket stage change lacks remap", "blocked")
        structural = lambda t: {k: v for k, v in t.items() if k not in {"source", "scope"}}
        need(current["source"]["revision"] >= task["source"]["revision"], "ticket revision regressed", "blocked")
        if structural(task) != structural(current) or task["source"]["file"] != current["source"]["file"]:
            need(current["source"]["revision"] > task["source"]["revision"], "changed ticket needs a fresh revision", "blocked")
    for name in ("spec", "adr"):
        if old[name] is not None:
            need(new[name] is not None and new[name]["revision"] >= old[name]["revision"], "source revision regressed", "blocked")
            if old[name]["file"] != new[name]["file"]:
                need(new[name]["revision"] > old[name]["revision"], "changed source needs a fresh revision", "blocked")
    before, after = gate_keys(old), gate_keys(new)
    key = lambda g: (g["stage"], g["id"])
    unique([key(r["from"]) for r in gate_remaps], "source gate remap")
    unique([key(r["to"]) for r in gate_remaps], "receiving gate remap")
    need({key(r["from"]) for r in gate_remaps} == before - after, "unaccounted gate removal/remap", "blocked")
    for remap in gate_remaps:
        verify_ref(root, remap["evidence"])
        need(key(remap["to"]) in after and key(remap["to"]) not in before, "missing/merged replacement gate", "blocked")
        if remap["from"]["stage"] is None:
            need(remap["to"]["stage"] is None, "final gate weakened to stage gate", "blocked")
        else:
            need(any(r["from"] == remap["from"]["stage"] and remap["to"]["stage"] in r["to"] for r in stage_remaps), "gate remap lacks stage boundary", "blocked")


def validate_reuse(root, state, proof, check_files=True):
    verify_ref(root, proof["evidence"])
    ticket = proof["ticket"]
    attempt = last(state, ticket)
    need(attempt is not None and attempt["state"] in SATISFIED
         and attempt["number"] == proof["accepted_attempt"] and attempt["plan_sha256"] == proof["accepted_plan_sha256"]
         and attempt["source_sha256"] == proof["accepted_source_sha256"] and attempt["receipt"]["file"] == proof["receipt"]
         and attempt["receipt"]["result"]["sha256"] == proof["result_sha256"]
         and identity(attempt["release"]) == proof["release_sha256"], "reuse historical binding mismatch", "blocked")
    origin = state["plans"][attempt["plan_sha256"]]
    target = state["plans"][proof["target_plan_sha256"]]
    old, new = tasks(origin)[ticket], tasks(target)[ticket]
    need({k: v for k, v in old.items() if k != "scope"} == {k: v for k, v in new.items() if k != "scope"}
         and origin["workspaces"] == target["workspaces"] and origin["final_gates"] == target["final_gates"]
         and next(s for s in origin["stages"] if s["id"] == old["stage"]) == next(s for s in target["stages"] if s["id"] == new["stage"]),
         "affected ticket scope cannot reuse acceptance", "blocked")
    unique([identity(a["original"]) for a in proof["archived_sources"]], "archive source")
    allowed = [s["file"] for s in (origin["spec"], origin["adr"]) if s is not None]
    for archive in proof["archived_sources"]:
        need(archive["original"] in allowed and archive["original"]["sha256"] == archive["copy"]["sha256"], "invalid historical archive", "blocked")
        verify_ref(root, archive["copy"])
    need(source_slices(root, origin, old, proof["archived_sources"]) == source_slices(root, target, new, []),
         "declared source scope changed", "blocked")
    receipt(root, state, attempt, historical=True)
    verify_ticket_decision(root, attempt)
    snapshot(root, target, proof["observed"], check_files=check_files)
    baseline = {(f["workspace"], f["path"]): f for f in attempt["input"]["files"]}
    output = {(f["workspace"], f["path"]): f for f in proof["observed"]["files"]}
    for item in attempt["receipt"]["result"]["files"]:
        if baseline.get((item["workspace"], item["path"])) != item:
            need(output.get((item["workspace"], item["path"])) == item, "accepted result changed; reuse refused", "blocked")
            if proof["target_plan_sha256"] == identity(state["plan"]):
                directory = Directory(target["workspaces"][item["workspace"]]["worktree"])
                try:
                    data = directory.read(item["path"], missing=True)
                    need((None if data is None else digest(data)) == item["sha256"], "accepted output changed after reuse", "blocked")
                    directory.check()
                finally:
                    directory.close()


def queue_satisfied(state, ticket):
    return ticket_ready(state, ticket) or ticket in state["deferred"]


def live_tickets(state):
    return [t for t in state["plan"]["queue"] if t not in state["deferred"]]


def change_scope(change):
    return identity({k: change[k] for k in ("from_plan", "to_plan", "ticket", "mode", "moves", "dependencies", "stages", "gates", "reuse")})


def change_plan(root, state, payload):
    verify_handoff(root, state)
    old, new = state["plan"], payload["plan"]
    current = state["current"]
    mode = payload["mode"] if payload["event"] == "transfer" else "revise"
    validate_plan(root, new)
    verify_sources(root, new)
    if mode == "revise":
        need(not payload["moves"] and set(tasks(old)) == set(tasks(new)), "membership/moves require transfer", "blocked")
    else:
        need(current is not None and not ticket_ready(state, current) and current not in state["deferred"], "transfer requires current unfinished scope", "blocked")
        need(payload["moves"] and all(m["from"]["ticket"] == current for m in payload["moves"]), "transfer only current ticket obligations", "blocked")
        remaining = [a for a in tasks(new)[current]["acs"] if a["required"]]
        need(bool(remaining) == (mode == "partial"), "partial/defer remaining scope mismatch", "blocked")
    prior_links = {endpoint(m["from"]): endpoint(m["to"]) for c in state["changes"] for m in c["moves"]}
    conserve(root, old, new, payload["moves"], payload["dependencies"], payload["stages"], payload["gates"], prior_links)
    change = {"sequence": state["sequence"] + 1, "from_plan": identity(old), "to_plan": identity(new),
              "ticket": current, "mode": mode,
              **{k: payload[k] for k in ("moves", "dependencies", "stages", "gates", "reuse", "decision")}}
    need(change["to_plan"] != change["from_plan"] and change["to_plan"] not in state["plans"], "plan identity already used", "conflict")
    decision(root, change["decision"], change_scope(change))
    state["plans"][identity(new)] = new
    state["changes"].append(change)
    for move in payload["moves"]:
        source, target = move["from"]["ticket"], move["to"]["ticket"]
        state["ticket_pools"][target] = sorted(set(state["ticket_pools"].get(target, [])) | set(state["ticket_pools"][source]))
    if mode == "defer":
        state["deferred"][current] = identity(change)
        if last(state) is not None:
            last(state)["state"] = "Deferred"
    else:
        attempt = last(state)
        if attempt and attempt["state"] in {"Launching", "Running", "Awaiting acceptance"}:
            attempt["state"] = "Blocked"
    state["plan"] = new
    state["done"] = False
    for proof in payload["reuse"]:
        need(proof["target_plan_sha256"] == identity(new), "reuse target plan mismatch", "blocked")
        need(not state["attempts"] or proof["observed"] == state["attempts"][-1]["release"]["result"], "reuse observed differs from released handoff", "blocked")
        validate_reuse(root, state, proof)
        need(ticket_ready(state, proof["ticket"]), "reuse prerequisite changed", "blocked")
    # Revisions can rewind invalidated prerequisites; advancing still needs a separate decision.
    end = new["queue"].index(current) + 1 if current is not None else len(new["queue"])
    earlier = next((t for t in new["queue"][:end] if t != current and not queue_satisfied(state, t)), None)
    if new.get("acceptance") == "stage":
        state["current"] = stage_entry(state, new["stages"][0]["id"])
    else:
        state["current"] = earlier or current or next((t for t in new["queue"] if not queue_satisfied(state, t)), new["queue"][-1])
    state["decisions"].append(change["decision"])


def validate_state(root, state, authority, check_reuse=True):
    shape(state, STATE)
    need(state["authority"] == authority, "canonical authority/owner mismatch", "conflict")
    validate_plan(root, state["plan"])
    table = tasks(state["plan"])
    need(("stage_decisions" in state) == (state["plan"].get("acceptance") == "stage"), "invalid stage decision ledger")
    for record in state.get("stage_decisions", []):
        plan = state["plans"].get(record["plan_sha256"])
        stage = next((x for x in plan["stages"] if x["id"] == record["stage"]), None) if plan else None
        need(plan is not None and plan.get("acceptance") == "stage" and stage is not None
             and ("failed_gate" not in record
                  or (record["action"] == "reject" and record["failed_gate"]["id"] in stage["gates"]))
             and (record["target"] is None or record["target"] in tasks(plan))
             and record["decision"] in state["decisions"]
             and record["decision"]["scope_sha256"] == stage_decision_scope(record), "invalid stored stage decision")
    for gate in state["gates"]:
        plan = state["plans"].get(gate["plan_sha256"])
        need(plan is not None and ("result_sha256" in gate) == (plan.get("acceptance") == "stage"), "invalid gate binding")
    need(state["current"] is None or state["current"] in table, "invalid current ticket")
    need(identity(state["plan"]) in state["plans"] and state["plans"][identity(state["plan"])] == state["plan"], "unregistered current plan")
    for key, plan in state["plans"].items():
        need(key == identity(plan), "historical plan hash mismatch")
        validate_plan(root, plan)
    initial = state["changes"][0]["from_plan"] if state["changes"] else identity(state["plan"])
    pools = {t: ["RB-" + t] for t in tasks(state["plans"][initial])}
    deferred = {}
    previous = initial
    prior_links = {}
    for change in state["changes"]:
        need(change["from_plan"] == previous and change["to_plan"] in state["plans"], "broken plan history")
        previous = change["to_plan"]
        before_plan, after_plan = state["plans"][change["from_plan"]], state["plans"][change["to_plan"]]
        decision(root, change["decision"], change_scope(change))
        conserve(root, before_plan, after_plan, change["moves"], change["dependencies"], change["stages"], change["gates"], prior_links)
        prior_links.update({endpoint(m["from"]): endpoint(m["to"]) for m in change["moves"]})
        for move in change["moves"]:
            target = move["to"]["ticket"]
            pools[target] = sorted(set(pools.get(target, [])) | set(pools[move["from"]["ticket"]]))
        if change["mode"] == "defer":
            deferred[change["ticket"]] = identity(change)
        unique([r["ticket"] for r in change["reuse"]], "reused ticket")
        need(all(r["target_plan_sha256"] == change["to_plan"] for r in change["reuse"]), "reuse target plan mismatch")
    need(previous == identity(state["plan"]) and pools == state["ticket_pools"] and deferred == state["deferred"], "plan/pool/deferral provenance mismatch")
    need(set(state["ticket_pools"]) == set(table) and set(state["budgets"]) == {"RB-" + t for t in tasks(state["plans"][initial])}, "missing review boundary pool")
    for budget in state["budgets"].values():
        need(budget["full_limit"] == 1 and budget["fix_limit"] == 2
             and budget["full_used"] <= budget["full_limit"] and budget["fix_used"] <= budget["fix_limit"], "review budget exceeded")
    unique([r["id"] for r in state["reviews"]], "review ID")
    charged = {p: {"full": 0, "fix": 0} for p in state["budgets"]}
    for review in state["reviews"]:
        need(review["pools"] == sorted(set(review["pools"])) and review["pools"]
             and set(review["pools"]) <= set(charged) and review["binding_sha256"] == review_binding(review), "invalid review pool/binding")
        writer = next((a for a in state["attempts"] if a["ticket"] == review["ticket"] and a["number"] == review["attempt"]), None)
        need(writer is not None and writer["source_sha256"] == review["source_sha256"], "unknown review writer/source")
        complete = review["phase"] == "completed"
        need(all((review[k] is not None) == complete for k in ("verdict", "evidence", "observation")), "incomplete review lifecycle")
        for pool in review["pools"]:
            charged[pool][review["kind"]] += 1
    need(all(state["budgets"][p][kind + "_used"] == count for p, counts in charged.items() for kind, count in counts.items()), "review debit history mismatch")
    for ticket in state["deferred"]:
        need(not any(a["required"] for a in table[ticket]["acs"])
             and not any(ticket in s["required"] for s in state["plan"]["stages"]), "Deferred still owns required scope")
    need(all(a["ticket"] == state["current"] for a in state["attempts"]
             if a["state"] in {"Launching", "Running", "Awaiting acceptance"}), "active attempt is not current")
    unique([item["id"] for item in state["decisions"]], "owner decision ID")
    unique([a["intent"]["marker"] for a in state["attempts"]], "launch marker")
    unique([a["peer"]["thread"] for a in state["attempts"] if a["peer"]], "bound peer")
    counts = {}
    for attempt in state["attempts"]:
        ticket = attempt["ticket"]
        need(ticket in table, "unknown attempt ticket")
        need(attempt["plan_sha256"] in state["plans"]
             and attempt["source_sha256"] == source_identity(state["plans"][attempt["plan_sha256"]], ticket), "attempt plan/source mismatch")
        counts[ticket] = counts.get(ticket, 0) + 1
        need(attempt["number"] == counts[ticket], "attempt sequence mismatch")
        need(all(d["ticket"] in table for d in attempt["dependencies"]), "unknown prerequisite binding")
        unique([d["ticket"] for d in attempt["dependencies"]], "prerequisite binding")
        if attempt["receipt"] is not None:
            value = attempt["receipt"]
            need(value["ticket"] == ticket and value["attempt"] == attempt["number"]
                 and value["source_sha256"] == attempt["source_sha256"] and value["write_go"] == attempt["write_go"],
                 "inconsistent stored receipt")
        if attempt["release"] is not None:
            need(attempt["release"]["peer"] == attempt["peer"] and attempt["release"]["write_go"] == attempt["write_go"],
                 "inconsistent stored release")
        stage_mode = state["plans"][attempt["plan_sha256"]].get("acceptance") == "stage"
        need(stage_mode or attempt["intent"]["decision"] is not None, "legacy launch without owner decision")
        need(stage_mode or (attempt["state"] != "Verified" and "verification" not in attempt),
             "legacy attempt with stage verification")
        if stage_mode and attempt["state"] in SATISFIED | {"Awaiting acceptance"}:
            verification = attempt.get("verification")
            need(verification is not None and verification["stop"] == (attempt["state"] != "Verified")
                 and (not verification["stop"] or "owner_stop" in tasks(state["plans"][attempt["plan_sha256"]])[ticket]),
                 "state without matching technical verification")
        if attempt["state"] in SATISFIED | {"Running", "Awaiting acceptance"}:
            need(attempt["peer"] is not None and attempt["preflight"] is not None
                 and attempt["write_go"] is not None, "state without bound preflight/write-go")
        if attempt["state"] in SATISFIED | {"Awaiting acceptance"}:
            need(attempt["receipt"] is not None and attempt["release"] is not None, "state without receipt/release")
        if attempt["state"] == "Accepted":
            need(attempt["acceptance"] is not None and attempt["acceptance"] in state["decisions"], "state without recorded owner acceptance")
    need(len(state["history"]) == state["sequence"] + 1, "history sequence length mismatch")
    for sequence, entry in enumerate(state["history"]):
        need(entry["sequence"] == sequence, "noncontiguous history")
    need(sum(1 for a in state["attempts"] if a["state"] in {"Launching", "Running", "Awaiting acceptance"}) <= 1,
         "multiple active attempts")
    need(not state["done"] or state["current"] is None, "Done with current ticket")
    if check_reuse:
        for change in state["changes"]:
            if change["to_plan"] == identity(state["plan"]):
                for proof in change["reuse"]:
                    if state["plan"].get("acceptance") == "stage":
                        ticket = proof["ticket"]
                        attempt = last(state, ticket)
                        # A repair can supersede this attempt or invalidate its dependencies.
                        if attempt is None or attempt["number"] != proof["accepted_attempt"] or not ticket_ready(state, ticket):
                            continue
                    validate_reuse(root, state, proof, check_files=False)
                    need(all(ticket_ready(state, t) for t in table[proof["ticket"]]["requires"])
                         and last(state, proof["ticket"])["dependencies"] == dependencies(state, proof["ticket"]), "reuse prerequisite changed", "blocked")


def decision(root, value, expected):
    shape(value, DECISION)
    verify_ref(root, value["evidence"])
    need(value["scope_sha256"] == expected, "owner decision scope mismatch", "blocked")


def ticket_decision_scope(attempt):
    if "verification" in attempt:
        return identity({"receipt": attempt["receipt"], "verification": attempt["verification"]})
    return identity(attempt["receipt"])


def verify_ticket_decision(root, attempt):
    if "verification" in attempt:
        verify_ref(root, attempt["verification"]["evidence"])
    if attempt["acceptance"] is not None:
        decision(root, attempt["acceptance"], ticket_decision_scope(attempt))


def stage_tickets(state, stage):
    table = tasks(state["plan"])
    return [t for t in live_tickets(state) if table[t]["stage"] == stage]


def stage_entry(state, stage):
    tickets = stage_tickets(state, stage)
    return next((t for t in tickets if not ticket_ready(state, t)), tickets[-1])


def result_set(root, state, stage):
    tickets = stage_tickets(state, stage) if stage is not None else live_tickets(state)
    need(all(ticket_ready(state, t) for t in tickets), "technical ticket results incomplete or stale", "blocked")
    results = []
    for ticket in tickets:
        attempt = last(state, ticket)
        value = receipt(root, state, attempt, historical=True)
        verify_ticket_decision(root, attempt)
        results.append({"ticket": ticket, "receipt": identity(value), "release": identity(attempt["release"]),
                        "verification": attempt["verification"], "acceptance": attempt["acceptance"]})
    return {"plan": identity(state["plan"]), "stage": stage, "results": results}


def gate_proofs(root, state, stage, ids, result_sha256=None):
    proofs = []
    for gate in ids:
        match = next((g for g in reversed(state["gates"]) if g["stage"] == stage and g["id"] == gate
                      and g["plan_sha256"] == identity(state["plan"]) and g.get("result_sha256") == result_sha256), None)
        need(match is not None, ("stage" if stage else "final") + " gate unproven: " + gate, "blocked")
        verify_ref(root, match["evidence"])
        proofs.append(match)
    return proofs


def stage_result(root, state, stage):
    results = result_set(root, state, stage)
    definition = next(s for s in state["plan"]["stages"] if s["id"] == stage)
    return identity({"results": results, "gates": gate_proofs(root, state, stage, definition["gates"], identity(results))})


def stage_decision_scope(record):
    return identity({k: v for k, v in record.items() if k != "decision"})


def stage_approval(root, state, stage, result, require_advance=False):
    actions = {"accept-and-advance", "advance"} if require_advance else {"accept", "accept-and-advance"}
    record = next((r for r in reversed(state["stage_decisions"]) if r["stage"] == stage
                   and r["plan_sha256"] == identity(state["plan"]) and r["result_sha256"] == result
                   and r["action"] in actions | {"reject"}), None)
    if record is None or record["action"] == "reject":
        return None
    decision(root, record["decision"], stage_decision_scope(record))
    return record


def stage_ready(root, state, stage, require_advance=False):
    if state["plan"].get("acceptance") == "stage":
        result = stage_result(root, state, stage)
        need(stage_approval(root, state, stage, result), "stage acceptance missing or stale", "blocked")
        if require_advance:
            need(stage_approval(root, state, stage, result, require_advance=True), "next stage not authorized", "blocked")
        return
    plan = state["plan"]
    definition = next(s for s in plan["stages"] if s["id"] == stage)
    need(all(ticket_ready(state, t) for t in definition["required"]), "required stage tickets not accepted", "blocked")
    for ticket in definition["required"]:
        # Historical intermediate workspaces may have moved on; their accepted receipt binds the prior result.
        value = last(state, ticket)["receipt"]
        verify_ref(root, value["file"])
    gate_proofs(root, state, stage, definition["gates"])


def next_stage_ticket(state, stage):
    stages = [s["id"] for s in state["plan"]["stages"]]
    index = stages.index(stage) + 1
    return stage_entry(state, stages[index]) if index < len(stages) else None


def final_scope(root, state):
    plan = state["plan"]
    results = result_set(root, state, None)
    gates = gate_proofs(root, state, None, plan["final_gates"], identity(results))
    return {"results": results, "gates": gates,
            "stages": [stage_result(root, state, s["id"]) for s in plan["stages"]]}


def stage_status(root, state):
    plan = state["plan"]
    stage = tasks(plan)[state["current"]]["stage"]
    view = {"stage": stage, "plan_sha256": identity(plan), "gate_result_sha256": None,
            "result_sha256": None, "accepted": False, "next_ticket": next_stage_ticket(state, stage),
            "final_gate_result_sha256": None, "done_scope_sha256": None}
    if not all(ticket_ready(state, t) for t in stage_tickets(state, stage)):
        return view
    verify_handoff(root, state)
    view["gate_result_sha256"] = identity(result_set(root, state, stage))
    if state["current"] != stage_tickets(state, stage)[-1]:
        return view
    try:
        view["result_sha256"] = stage_result(root, state, stage)
        view["accepted"] = bool(stage_approval(root, state, stage, view["result_sha256"]))
        if view["accepted"] and view["next_ticket"] is None:
            for definition in plan["stages"]:
                stage_ready(root, state, definition["id"])
            view["final_gate_result_sha256"] = identity(result_set(root, state, None))
            view["done_scope_sha256"] = identity(final_scope(root, state))
    except GuardError as err:
        if err.code != "blocked":
            raise
        view["blocked"] = str(err)
    return view


def decide_stage(root, state, payload):
    plan = state["plan"]
    ticket = state["current"]
    need(plan.get("acceptance") == "stage" and ticket is not None, "no active stage acceptance", "blocked")
    stage = tasks(plan)[ticket]["stage"]
    tickets = stage_tickets(state, stage)
    need(ticket == tickets[-1], "current ticket is not at the stage boundary", "blocked")
    verify_handoff(root, state)
    event = payload["event"]
    action = event[len("stage-"):]
    failed_gate = payload.get("failed_gate")
    if failed_gate is not None:
        definition = next(s for s in plan["stages"] if s["id"] == stage)
        need(failed_gate["id"] in definition["gates"], "unknown failed stage gate")
        verify_ref(root, failed_gate["evidence"])
        result = identity(result_set(root, state, stage))
    else:
        result = stage_result(root, state, stage)
    target = None
    if event == "stage-accept" and payload["advance"]:
        action = "accept-and-advance"
    if action in {"accept", "accept-and-advance"}:
        need(stage_approval(root, state, stage, result) is None, "stage already accepted", "conflict")
    if action == "advance":
        need(stage_approval(root, state, stage, result) is not None, "stage acceptance missing or stale", "blocked")
    if action in {"advance", "accept-and-advance"}:
        target = next_stage_ticket(state, stage)
        need(target is not None, "no next stage", "blocked")
    elif action == "reject":
        target = payload["repair"]
        need(target in tickets, "repair ticket outside the current stage", "blocked")
    record = {"stage": stage, "plan_sha256": identity(plan), "result_sha256": result,
              "action": action, "target": target, "decision": payload["decision"]}
    if failed_gate is not None:
        record["failed_gate"] = failed_gate
    decision(root, record["decision"], stage_decision_scope(record))
    state["stage_decisions"].append(record)
    state["decisions"].append(record["decision"])
    if action == "reject":
        for ticket in tickets[tickets.index(target):]:
            last(state, ticket)["state"] = "Blocked"
    if target is not None:
        state["current"] = target


def verify_launch_prerequisites(root, state, ticket):
    plan = state["plan"]
    stage_mode = plan.get("acceptance") == "stage"
    position = plan["queue"].index(ticket)
    need(all(queue_satisfied(state, t) for t in plan["queue"][:position]), "queue predecessor not accepted/deferred", "blocked")
    task = tasks(plan)[ticket]
    if stage_mode:
        for t in plan["queue"][:position]:
            if t not in state["deferred"] and tasks(plan)[t]["stage"] == task["stage"]:
                prior = last(state, t)
                receipt(root, state, prior, historical=True)
                verify_ticket_decision(root, prior)
    for predecessor in task["requires"]:
        need(ticket_ready(state, predecessor), "technical prerequisite not accepted", "blocked")
        verify_ref(root, last(state, predecessor)["receipt"]["file"])
    stages = [s["id"] for s in plan["stages"]]
    for stage in stages[:stages.index(task["stage"])]:
        stage_ready(root, state, stage, require_advance=stage_mode)


def apply(root, state, payload):
    need(type(payload) is dict and type(payload.get("event")) is str, "missing event")
    event = payload["event"]
    plan = state["plan"]
    ticket = state["current"]
    attempt = last(state)
    before = current_state(state)
    stage_mode = plan.get("acceptance") == "stage"
    common = {"event": {event}}
    schemas = {
        "launch": {"intent": INTENT, "input": SNAPSHOT, "restart": bool},
        "pending": {"handle": text},
        "reconcile": {"candidates": [BINDING], "evidence": REF},
        "write-go": {"id": text, "preflight": REF, "observed": SNAPSHOT},
        "block": {"reason": text},
        "result": {"receipt": RECEIPT},
        "writer-release": {"release": RELEASE},
        "await": {}, "verify": VERIFICATION, "accept": {"decision": DECISION},
        "advance": {} if stage_mode else {"decision": DECISION},
        "stage-accept": {"decision": DECISION, "advance": bool},
        "stage-advance": {"decision": DECISION},
        "stage-reject": {"decision": DECISION, "repair": TICKET,
                         **({"failed_gate": FAILED_GATE} if "failed_gate" in payload else {})},
        "stop": {"decision": DECISION},
        "review-reserve": {"id": text, "kind": {"full", "fix"}, "candidate": SNAPSHOT, "quiescence": REF},
        "review-complete": {"id": text, "binding_sha256": SHA,
                            "verdict": {"APPROVED", "CHANGES_REQUESTED", "FAILED"}, "evidence": REF, "observation": REF},
        "gate": {"stage": (STAGE,), "id": text, "evidence": REF, **({"result_sha256": SHA} if stage_mode else {})},
        "done": {"decision": DECISION},
        "revise": CHANGE_FIELDS,
        "transfer": {**CHANGE_FIELDS, "mode": {"partial", "defer"}},
    }
    need(event in schemas, "unknown event")
    shape(payload, {**common, **schemas[event]})
    if event not in {"revise", "transfer"}:
        verify_sources(root, plan)
    dispatch = None
    review_dispatch = None
    if event == "launch":
        need(ticket is not None and not state["done"], "no current ticket", "blocked")
        if attempt:
            need(payload["restart"] and before in {"Blocked", "Stopped"}, "attempt already launched", "conflict")
        else:
            need(not payload["restart"], "restart without attempt")
        verify_handoff(root, state)
        verify_launch_prerequisites(root, state, ticket)
        snapshot(root, plan, payload["input"])
        if stage_mode and state["attempts"]:
            need(payload["input"] == state["attempts"][-1]["release"]["result"],
                 "launch input differs from released handoff", "blocked")
        if not state["attempts"]:
            need(payload["input"] == plan["input"], "initial input mismatch", "blocked")
        intent = payload["intent"]
        expected = identity({"ticket": ticket, "attempt": sum(a["ticket"] == ticket for a in state["attempts"]) + 1,
                             "source_sha256": source_identity(plan, ticket), "input": payload["input"],
                             "marker": intent["marker"], "project": intent["project"],
                             "context_sha256": intent["context_sha256"]})
        if stage_mode and before != "Stopped":
            need(intent["decision"] is None, "stage launch uses existing stage authorization")
        else:
            decision(root, intent["decision"], expected)
        need(all(a["intent"]["marker"] != intent["marker"] for a in state["attempts"]), "reused launch marker")
        attempt = {"ticket": ticket, "number": sum(a["ticket"] == ticket for a in state["attempts"]) + 1,
                   "state": "Launching", "plan_sha256": identity(plan), "source_sha256": source_identity(plan, ticket), "intent": intent,
                   "input": payload["input"], "workspaces": plan["workspaces"], "dependencies": dependencies(state, ticket),
                   "pending": None, "peer": None, "preflight": None, "write_go": None,
                   "receipt": None, "release": None, "acceptance": None}
        state["attempts"].append(attempt)
        if intent["decision"] is not None:
            state["decisions"].append(intent["decision"])
        dispatch = {"marker": intent["marker"], "project": intent["project"],
                    "context_sha256": intent["context_sha256"]}
    elif event in {"pending", "reconcile"}:
        need(attempt is not None and before in {"Launching", "Blocked"} and attempt["peer"] is None,
             "no unresolved launch intent", "blocked")
        if event == "pending":
            need(before == "Launching" and attempt["pending"] is None, "pending already recorded", "conflict")
            attempt["pending"] = payload["handle"]
        else:
            verify_ref(root, payload["evidence"])
            candidates = payload["candidates"]
            if len(candidates) != 1:
                attempt["state"] = "Blocked"
            else:
                candidate = candidates[0]
                need(all(candidate[k] == attempt["intent"][k] for k in ("marker", "project", "context_sha256")), "reconciliation context mismatch", "blocked")
                need(not any(a["peer"] == candidate["peer"] for a in state["attempts"]), "peer already bound")
                attempt["peer"] = candidate["peer"]
                attempt["state"] = "Launching"
    elif event == "write-go":
        need(attempt is not None and before in {"Launching", "Blocked"} and attempt["peer"] is not None,
             "bound preflight required", "blocked")
        need(attempt["source_sha256"] == source_identity(plan, ticket), "stale launch source", "blocked")
        if stage_mode:
            need("verification" not in attempt, "verified attempt needs a fresh repair launch", "blocked")
            verify_launch_prerequisites(root, state, ticket)
        if attempt["write_go"] is not None:
            released(root, state, attempt)
        need(not any(r["phase"] == "reserved" for r in state["reviews"]), "unresolved review reservation", "blocked")
        need(payload["id"] not in [h["reason"] for h in state["history"] if h["event"] == "write-go"], "write-go ID reused")
        verify_ref(root, payload["preflight"])
        snapshot(root, plan, payload["observed"])
        need(payload["observed"] == (attempt["release"]["result"] if attempt["write_go"] else attempt["input"]),
             "preflight input differs from launch/released result", "blocked")
        attempt.update(state="Running", preflight=payload["preflight"], write_go=payload["id"], receipt=None, release=None, acceptance=None)
    elif event == "block":
        need(attempt is not None and before not in SATISFIED | {"Stopped"}, "cannot block current state")
        attempt["state"] = "Blocked"
    elif event == "result":
        need(attempt is not None and before == "Running" and attempt["release"] is None, "result needs current running writer", "blocked")
        attempt["receipt"] = payload["receipt"]
        value = attempt["receipt"]
        need(value["ticket"] == ticket and value["attempt"] == attempt["number"]
             and value["source_sha256"] == attempt["source_sha256"] and value["write_go"] == attempt["write_go"], "stale result receipt", "blocked")
        verify_ref(root, value["file"])
        snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]}, value["result"], scope=True)
    elif event == "writer-release":
        need(attempt is not None and before in {"Running", "Blocked", "Stopped", "Launching"}, "release unavailable")
        attempt["release"] = payload["release"]
        released(root, state, attempt)
    elif event in {"await", "verify"}:
        need(stage_mode == (event == "verify"), "wrong verification event for acceptance mode", "blocked")
        need(attempt is not None and before == "Running", "not running", "blocked")
        receipt(root, state, attempt)
        if stage_mode:
            need(not payload["stop"] or "owner_stop" in tasks(plan)[ticket], "undeclared owner stop", "blocked")
            verify_ref(root, payload["evidence"])
            attempt["verification"] = {k: payload[k] for k in VERIFICATION}
        attempt["state"] = "Awaiting acceptance" if not stage_mode or payload["stop"] else "Verified"
    elif event == "accept":
        need(attempt is not None and before == "Awaiting acceptance", "not awaiting acceptance", "blocked")
        receipt(root, state, attempt)
        verify_ticket_decision(root, attempt)
        decision(root, payload["decision"], ticket_decision_scope(attempt))
        attempt.update(state="Accepted", acceptance=payload["decision"])
        state["decisions"].append(payload["decision"])
    elif event == "advance":
        need(ticket is not None and queue_satisfied(state, ticket), "current ticket not accepted/deferred", "blocked")
        verify_handoff(root, state)
        if ticket_ready(state, ticket):
            receipt(root, state, attempt, historical=attempt is not state["attempts"][-1]
                    or attempt["source_sha256"] != source_identity(plan, ticket))
            if stage_mode:
                verify_ticket_decision(root, attempt)
        position = plan["queue"].index(ticket)
        target = next((t for t in plan["queue"][position + 1:] if t not in state["deferred"]), None)
        need(target is not None, "no next ticket")
        if stage_mode:
            need(tasks(plan)[ticket]["stage"] == tasks(plan)[target]["stage"], "stage boundary requires owner acceptance and advance", "blocked")
        else:
            decision(root, payload["decision"], identity({"from": ticket, "to": target, "plan": identity(plan)}))
        for prerequisite in tasks(plan)[target]["requires"]:
            need(ticket_ready(state, prerequisite), "technical prerequisite not accepted", "blocked")
        stages = [s["id"] for s in plan["stages"]]
        for stage in stages[:stages.index(tasks(plan)[target]["stage"])]:
            stage_ready(root, state, stage)
        state["current"] = target
        if not stage_mode:
            state["decisions"].append(payload["decision"])
    elif event in {"stage-accept", "stage-advance", "stage-reject"}:
        decide_stage(root, state, payload)
    elif event == "stop":
        need(attempt is not None and before not in SATISFIED, "no stoppable attempt")
        decision(root, payload["decision"], identity({"ticket": ticket, "attempt": attempt["number"], "source": attempt["source_sha256"]}))
        attempt["state"] = "Stopped"
        state["decisions"].append(payload["decision"])
    elif event == "review-reserve":
        need(attempt is not None and before == "Running" and attempt["release"] is None, "review needs current unreleased writer", "blocked")
        need(not any(r["id"] == payload["id"] for r in state["reviews"]), "review ID already reserved", "conflict")
        need(not any(r["phase"] == "reserved" for r in state["reviews"]), "unresolved review reservation", "blocked")
        need(attempt["source_sha256"] == source_identity(plan, ticket), "stale review source", "blocked")
        verify_ref(root, payload["quiescence"])
        snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]}, payload["candidate"], scope=True)
        pools = state["ticket_pools"][ticket]
        kind = payload["kind"]
        need(all(state["budgets"][p][kind + "_used"] < state["budgets"][p][kind + "_limit"]
                 and (kind != "fix" or state["budgets"][p]["full_used"] > 0) for p in pools), "review budget exhausted/incompatible pools", "blocked")
        review = {"id": payload["id"], "phase": "reserved", "kind": kind, "ticket": ticket,
                  "attempt": attempt["number"], "write_go": attempt["write_go"], "source_sha256": attempt["source_sha256"],
                  "candidate": payload["candidate"], "pools": pools[:], "quiescence": payload["quiescence"],
                  "binding_sha256": "", "verdict": None, "evidence": None, "observation": None}
        review["binding_sha256"] = review_binding(review)
        for pool in pools:
            state["budgets"][pool][kind + "_used"] += 1
        state["reviews"].append(review)
        review_dispatch = {"id": review["id"], "binding_sha256": review["binding_sha256"]}
    elif event == "review-complete":
        review = next((r for r in state["reviews"] if r["id"] == payload["id"]), None)
        need(review is not None and review["phase"] == "reserved", "review not reserved/already completed", "conflict")
        need(attempt is not None and before in {"Running", "Blocked", "Stopped"}
             and review["ticket"] == ticket and review["attempt"] == attempt["number"]
             and review["write_go"] == attempt["write_go"] and review["source_sha256"] == source_identity(plan, ticket)
             and review["binding_sha256"] == payload["binding_sha256"], "stale review completion binding", "blocked")
        snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]}, review["candidate"], scope=True)
        verify_ref(root, payload["evidence"])
        verify_ref(root, payload["observation"])
        review.update(phase="completed", verdict=payload["verdict"], evidence=payload["evidence"], observation=payload["observation"])
    elif event == "gate":
        verify_ref(root, payload["evidence"])
        stage = payload["stage"]
        definitions = next((s for s in plan["stages"] if s["id"] == stage), None)
        need((definitions is not None and payload["id"] in definitions["gates"])
             or (stage is None and payload["id"] in plan["final_gates"]), "unknown gate")
        required = definitions["required"] if stage else live_tickets(state)
        need(all(ticket_ready(state, t) for t in required), "gate tickets not accepted", "blocked")
        gate = {"stage": stage, "id": payload["id"], "plan_sha256": identity(plan), "evidence": payload["evidence"]}
        if stage_mode:
            verify_handoff(root, state)
            need(ticket is not None and (stage is None or tasks(plan)[ticket]["stage"] == stage), "gate outside the current stage", "blocked")
            if stage is None:
                for definition in plan["stages"]:
                    stage_ready(root, state, definition["id"])
            gate["result_sha256"] = identity(result_set(root, state, stage))
            need(payload["result_sha256"] == gate["result_sha256"], "stale gate result binding", "blocked")
        need(not any(all(g.get(k) == gate.get(k) for k in ("stage", "id", "plan_sha256", "result_sha256"))
                     and (not stage_mode or g["evidence"] == gate["evidence"]) for g in state["gates"]), "gate already recorded")
        state["gates"].append(gate)
    elif event == "done":
        need(not stage_mode or not state["done"], "feature already done", "conflict")
        need(all(ticket_ready(state, t) for t in live_tickets(state)), "unaccepted feature ticket", "blocked")
        verify_handoff(root, state)
        for stage in plan["stages"]:
            stage_ready(root, state, stage["id"])
        if stage_mode:
            scope = final_scope(root, state)
        else:
            gate_proofs(root, state, None, plan["final_gates"])
            scope = {"plan": identity(plan), "receipts": [last(state, t)["receipt"]["file"] for t in live_tickets(state)]}
        decision(root, payload["decision"], identity(scope))
        state.update(done=True, current=None)
        state["decisions"].append(payload["decision"])
    elif event in {"revise", "transfer"}:
        change_plan(root, state, payload)
    state["sequence"] += 1
    active = last(state)
    reason = payload.get("reason", payload.get("id", event))
    state["history"].append({"sequence": state["sequence"], "event": event,
                             "ticket": state["current"], "attempt": active["number"] if active else None,
                             "from": before, "to": current_state(state), "reason": reason,
                             "payload_sha256": identity(payload)})
    return dispatch, review_dispatch


def authority_for(root, args, owner):
    return {"feature": args.feature, "repository": args.repository, "root": str(root.path),
            "ledger": str(root.path / "execution.json"), "lock": str(root.path / "execution.lock"),
            "device": root.stat.st_dev, "inode": root.stat.st_ino, "owner": owner}


def transact(root, authority, args, payload):
    lock_created = False
    durable = False
    temporary = None
    lock_info = None
    try:
        try:
            fd = os.open("execution.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root.fd)
        except FileExistsError as err:
            raise GuardError("conflict", "existing/stale lock; manual reconciliation required") from err
        lock_created = True
        lock_info = os.fstat(fd)
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps({"owner": authority["owner"], "token": uuid.uuid4().hex}).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(root.fd)
        existing = root.read("execution.json", missing=True)
        dispatch = None
        review_dispatch = None
        if args.command == "init":
            need(existing is None, "ledger already initialized", "conflict")
            shape(payload, {"plan": PLAN, "decision": DECISION})
            validate_plan(root, payload["plan"])
            verify_sources(root, payload["plan"])
            snapshot(root, payload["plan"], payload["plan"]["input"])
            decision(root, payload["decision"], identity({"authority": authority, "plan": payload["plan"]}))
            state = {"schema": SCHEMA, "authority": authority, "sequence": 0, "plan": payload["plan"],
                     "current": payload["plan"]["queue"][0], "attempts": [],
                     "budgets": {"RB-" + t: {"full_limit": 1, "fix_limit": 2, "full_used": 0, "fix_used": 0} for t in tasks(payload["plan"])},
                     "ticket_pools": {t: ["RB-" + t] for t in tasks(payload["plan"])}, "reviews": [],
                     "plans": {identity(payload["plan"]): payload["plan"]}, "changes": [], "deferred": {},
                     "gates": [], "decisions": [payload["decision"]], "done": False,
                     "history": [{"sequence": 0, "event": "init", "ticket": payload["plan"]["queue"][0],
                                  "attempt": None, "from": "Absent", "to": "Planned", "reason": "owner execution start",
                                  "payload_sha256": identity(payload)}]}
            if payload["plan"].get("acceptance") == "stage":
                state["stage_decisions"] = []
        else:
            need(existing is not None, "ledger missing", "blocked")
            state = decode(existing)
            validate_state(root, state, authority, check_reuse=payload.get("event") not in {"revise", "transfer"})
            need(state["sequence"] == args.expected_sequence, "expected sequence mismatch", "conflict")
            dispatch, review_dispatch = apply(root, state, payload)
        validate_state(root, state, authority)
        serialized = json.dumps(state, ensure_ascii=False, indent=2).encode() + b"\n"
        need(len(serialized) <= LIMIT, "serialized ledger exceeds size limit")
        temporary = ".execution-" + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root.fd)
        with os.fdopen(fd, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, "execution.json", src_dir_fd=root.fd, dst_dir_fd=root.fd)
        temporary = None
        os.fsync(root.fd)
        root.check()
        durable = True
        return {"ok": True, "sequence": state["sequence"], "state": current_state(state), "dispatch": dispatch, "review_dispatch": review_dispatch}
    except GuardError:
        # Validation failure before replace is safe to retry with a new request.
        durable = temporary is None and lock_created
        raise
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=root.fd)
            except OSError:
                pass
        if lock_created and durable:
            current = os.stat("execution.lock", dir_fd=root.fd, follow_symlinks=False)
            need((current.st_dev, current.st_ino) == (lock_info.st_dev, lock_info.st_ino), "lock identity changed", "conflict")
            os.unlink("execution.lock", dir_fd=root.fd)
            os.fsync(root.fd)
        # An interrupted/uncertain write retains its lock; no automatic stale-lock removal.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "resume", "init", "transition"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--owner-thread")
    parser.add_argument("--owner-host")
    parser.add_argument("--expected-sequence", type=int)
    args = parser.parse_args()
    root = None
    try:
        SLUG(args.feature)
        text(args.repository)
        root = Directory(args.root)
        if args.command in {"status", "resume"}:
            state = decode(root.read("execution.json"))
            shape(state, STATE)
            owner = state["authority"]["owner"]
            if args.command == "resume":
                owner = {"thread": args.owner_thread, "host": args.owner_host}
                shape(owner, OWNER)
            authority = authority_for(root, args, owner)
            validate_state(root, state, authority)
            verify_sources(root, state["plan"])
            attempt = last(state) or (state["attempts"][-1] if state["done"] and state["attempts"] else None)
            if attempt is None and state["attempts"]:
                verify_handoff(root, state)
            elif attempt and attempt["receipt"] is not None:
                if attempt["state"] in SATISFIED | {"Awaiting acceptance"}:
                    historical = attempt["plan_sha256"] != identity(state["plan"]) or attempt is not state["attempts"][-1]
                    receipt(root, state, attempt, historical=historical)
                    if "verification" in attempt:
                        verify_ticket_decision(root, attempt)
                    if historical:
                        verify_handoff(root, state)
                else:
                    verify_ref(root, attempt["receipt"]["file"])
                    snapshot(root, {"workspaces": attempt["workspaces"], "baseline": attempt["input"]},
                             attempt["receipt"]["result"], check_files=attempt is state["attempts"][-1], scope=True)
                    if attempt is not state["attempts"][-1]:
                        verify_handoff(root, state)
            else:
                snapshot(root, state["plan"], state["plan"]["input"], check_files=attempt is None)
            try:
                os.stat("execution.lock", dir_fd=root.fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise GuardError("blocked", "existing lock; unresolved writer/durability")
            root.check()
            result = {"ok": True, "state": state, "effective_state": current_state(state), "dispatch": None, "review_dispatch": None,
                      "reconciliation_required": bool(attempt and attempt["state"] in {"Launching", "Blocked"} and attempt["peer"] is None)}
            if state["plan"].get("acceptance") == "stage" and state["current"] is not None:
                result["stage"] = stage_status(root, state)
        else:
            shape({"thread": args.owner_thread, "host": args.owner_host}, OWNER)
            if args.command == "transition":
                number(args.expected_sequence)
            else:
                need(args.expected_sequence is None, "init has no expected sequence")
            payload = decode(sys.stdin.buffer.read(LIMIT + 1))
            authority = authority_for(root, args, {"thread": args.owner_thread, "host": args.owner_host})
            result = transact(root, authority, args, payload)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (GuardError, OSError, ValueError, RecursionError) as err:
        code = err.code if isinstance(err, GuardError) else "unavailable"
        print(json.dumps({"ok": False, "code": code, "error": str(err)}, ensure_ascii=False))
        return {"invalid": 2, "conflict": 3, "blocked": 4, "unavailable": 5}.get(code, 5)
    finally:
        if root is not None:
            root.close()


if __name__ == "__main__":
    sys.exit(main())
