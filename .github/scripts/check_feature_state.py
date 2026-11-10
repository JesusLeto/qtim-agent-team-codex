#!/usr/bin/env python3
"""Exercise the real feature guard CLI in disposable filesystem fixtures.

No App peers or live ledger. --helper permits the disposable broken-variant
control; --case wrong-owner isolates the independent owner-boundary assertion.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "plugins/qtim/skills/qtim-feature/scripts/feature_state.py"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class Fixture:
    def __init__(self, helper):
        self.temporary = tempfile.TemporaryDirectory(prefix="qtim-feature-state-")
        base = Path(self.temporary.name).resolve()
        self.root = base / "feature"
        self.workspace = base / "workspace"
        self.root.mkdir()
        self.workspace.mkdir()
        self.helper = helper
        (self.workspace / "file.txt").write_text("baseline\n", encoding="utf-8")
        self.evidence = self.ref("evidence.md", "synthetic coordinator/runtime/check evidence\n")
        self.plan = {
            "spec": {"revision": 2, "file": self.ref("spec.md", "approved specification r2\n")},
            "adr": {"revision": 2, "file": self.ref("adr.md", "accepted ADR r2\n")},
            "feature_acs": ["AC-01", "AC-02"], "queue": ["T01", "T02"],
            "tickets": [
                {"id": "T01", "stage": "S1", "source": {"revision": 1, "file": self.ref("tickets/T01.md", "first contract\n")},
                 "requires": [], "acs": [{"id": "T01-AC1", "feature_acs": ["AC-01"], "required": True}], "review_required": True},
                {"id": "T02", "stage": "S2", "source": {"revision": 1, "file": self.ref("tickets/T02.md", "second contract\n")},
                 "requires": ["T01"], "acs": [{"id": "T02-AC1", "feature_acs": ["AC-02"], "required": True}], "review_required": False},
            ],
            "stages": [{"id": "S1", "required": ["T01"], "gates": ["S1-ready"]},
                       {"id": "S2", "required": ["T02"], "gates": []}],
            "final_gates": ["integration"],
            "workspaces": [{"repository": "fixture/repository", "worktree": str(self.workspace), "base": "a" * 40,
                            "write_paths": ["file.txt"], "git_actions": []}],
        }
        self.plan["input"] = self.snapshot("input")
        for ticket in self.plan["tickets"]:
            ticket["scope"] = {name: [{"start": 0, "end": len((self.root / self.plan[name]["file"]["path"]).read_bytes())}]
                               for name in ("spec", "adr")}
        self.sequence = 0
        self.number = 0

    def close(self):
        self.temporary.cleanup()

    def ref(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        return {"path": name, "sha256": sha(path.read_bytes())}

    def snapshot(self, name):
        patch = self.ref("artifacts/" + name + ".patch", "synthetic patch " + name + "\n")
        files = [{"workspace": 0, "path": path.relative_to(self.workspace).as_posix(), "sha256": sha(path.read_bytes())}
                 for path in sorted(self.workspace.rglob("*")) if path.is_file()]
        value = {"patch": patch, "files": files, "untracked": []}
        value["sha256"] = identity({"workspaces": self.plan["workspaces"], "patch": patch["sha256"],
                                    "files": value["files"], "untracked": []})
        return value

    def owner_decision(self, scope):
        return {"id": "owner-" + scope[:12], "statement": "Fixture owner explicitly authorizes this exact scope",
                "evidence": self.evidence, "scope_sha256": scope}

    def authority(self):
        info = self.root.stat()
        return {"feature": "fixture", "repository": "fixture/repository", "root": str(self.root),
                "ledger": str(self.root / "execution.json"), "lock": str(self.root / "execution.lock"),
                "device": info.st_dev, "inode": info.st_ino, "owner": {"thread": "coordinator", "host": "local"}}

    def state(self):
        return json.loads((self.root / "execution.json").read_bytes())

    def attempt(self):
        state = self.state()
        return next(a for a in reversed(state["attempts"]) if a["ticket"] == state["current"])

    def source(self, ticket):
        table = {t["id"]: t for t in self.plan["tickets"]}
        return identity({"spec": self.plan["spec"], "adr": self.plan["adr"], "ticket": table[ticket],
                         "workspaces": self.plan["workspaces"],
                         "prerequisites": {t: self.source(t) for t in table[ticket]["requires"]}})

    def command(self, operation="transition", owner="coordinator", sequence=None):
        args = [str(self.helper), operation, "--root", str(self.root), "--feature", "fixture", "--repository", "fixture/repository"]
        if operation != "status":
            args += ["--owner-thread", owner, "--owner-host", "local"]
        if operation == "transition":
            args += ["--expected-sequence", str(self.sequence if sequence is None else sequence)]
        return args

    def call(self, payload=None, operation="transition", owner="coordinator", code=0, contains=None, sequence=None, raw=None, wrapper=None):
        args = self.command(operation, owner, sequence)
        command = [sys.executable, *args] if wrapper is None else [sys.executable, "-c", wrapper, *args]
        result = subprocess.run(command, input=raw if raw is not None else json.dumps(payload).encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, timeout=20)
        expect(result.returncode == code, "expected exit %s, actual %s: %s %s" % (code, result.returncode, result.stdout.decode(), result.stderr.decode()))
        if code in (71, 72, 73):
            expect(not result.stdout, "crashed transition returned dispatch")
            return None
        try:
            response = json.loads(result.stdout)
        except ValueError as err:
            raise AssertionError("CLI did not return JSON: " + result.stderr.decode()) from err
        if contains:
            expect(contains in response.get("error", ""), "unexpected rejection: " + str(response))
        if code == 0 and operation in {"transition", "init"}:
            self.sequence = response["sequence"]
        return response

    def init(self, plan=None, code=0, contains=None):
        plan = self.plan if plan is None else plan
        return self.call({"plan": plan, "decision": self.owner_decision(identity({"authority": self.authority(), "plan": plan}))},
                         "init", code=code, contains=contains)

    def launch_payload(self, restart=False):
        state = self.state()
        ticket = state["current"]
        self.number += 1
        number = sum(a["ticket"] == ticket for a in state["attempts"]) + 1
        observed = self.plan["input"] if not state["attempts"] else self.snapshot("launch-" + str(self.number))
        intent = {"marker": "fixture:" + ticket + ":a" + str(number), "project": "fixture-project", "context_sha256": "b" * 64}
        intent["decision"] = self.owner_decision(identity({"ticket": ticket, "attempt": number,
                    "source_sha256": self.source(ticket), "input": observed, "marker": intent["marker"],
                    "project": intent["project"], "context_sha256": intent["context_sha256"]}))
        return {"event": "launch", "intent": intent, "input": observed, "restart": restart}

    def launch(self, restart=False):
        response = self.call(self.launch_payload(restart))
        expect(response["dispatch"] is not None and self.attempt()["state"] == "Launching", "missing durable intent")
        self.launch_checkpoint = response["dispatch"]
        return response

    def bind(self):
        attempt = self.attempt()
        candidate = {k: attempt["intent"][k] for k in ("marker", "project", "context_sha256")}
        candidate["peer"] = {"thread": "peer-" + attempt["intent"]["marker"], "host": "local"}
        self.call({"event": "reconcile", "candidates": [candidate], "evidence": self.evidence})

    def write_go(self, name="write-1", observed=None):
        attempt = self.attempt()
        observed = observed or (attempt["release"]["result"] if attempt["write_go"] else attempt["input"])
        self.call({"event": "write-go", "id": name, "preflight": self.evidence, "observed": observed})

    def running(self):
        self.init()
        self.launch()
        self.bind()
        self.write_go()

    def result(self, name="result-1"):
        attempt = self.attempt()
        value = {"revision": 1, "file": self.ref("receipts/" + name + ".md", "fixture result " + name + "\n"),
                 "ticket": attempt["ticket"], "attempt": attempt["number"], "source_sha256": attempt["source_sha256"],
                 "write_go": attempt["write_go"], "result": self.snapshot(name),
                 "acs": [{"id": ac["id"], "verdict": "PASS" if ac["required"] else "BLOCKED", "expected": "contract holds",
                           "actual": "synthetic filesystem evidence", "evidence": [self.evidence]}
                          for ac in next(t for t in self.plan["tickets"] if t["id"] == attempt["ticket"])["acs"]],
                 "checks": [{"command": "fixture check", "exit_code": 0, "evidence": self.evidence}],
                 "review": {"id": None, "verdict": "NOT_REQUIRED", "evidence": self.evidence, "findings": []}}
        return value

    def review(self, value, kind="full", verdict="APPROVED", name=None):
        review_id = name or "review-" + str(self.sequence)
        response = self.call({"event": "review-reserve", "id": review_id, "kind": kind,
                              "candidate": value["result"], "quiescence": self.evidence})
        expect(response["review_dispatch"]["id"] == review_id, "no durable review checkpoint")
        self.call({"event": "review-complete", "id": review_id,
                   "binding_sha256": response["review_dispatch"]["binding_sha256"], "verdict": verdict,
                   "evidence": self.evidence, "observation": self.evidence})
        value["review"].update(id=review_id, verdict=verdict)
        return response

    def change(self, new, mode="revise", moves=None, dependencies=None, stages=None, gates=None, reuse=None,
               code=0, contains=None):
        fields = {"moves": moves or [], "dependencies": dependencies or [], "stages": stages or [],
                  "gates": gates or [], "reuse": reuse or []}
        scope = identity({"from_plan": identity(self.plan), "to_plan": identity(new), "ticket": self.state()["current"],
                          "mode": mode, **fields})
        payload = {"event": "revise" if mode == "revise" else "transfer", "plan": new,
                   **fields, "decision": self.owner_decision(scope)}
        if mode != "revise":
            payload["mode"] = mode
        response = self.call(payload, code=code, contains=contains)
        if code == 0:
            self.plan = new
        return response

    def release(self, value):
        attempt = self.attempt()
        return {"peer": attempt["peer"], "handles": [attempt["peer"]["thread"]], "verified_stopped": True,
                "worker_turn_finished": True, "evidence": self.evidence, "result": value["result"], "write_go": attempt["write_go"]}

    def await_result(self):
        value = self.result()
        if next(t for t in self.plan["tickets"] if t["id"] == self.state()["current"])["review_required"]:
            self.review(value)
        self.call({"event": "result", "receipt": value})
        self.call({"event": "writer-release", "release": self.release(value)})
        self.call({"event": "await"})
        return value

    def accept(self):
        self.call({"event": "accept", "decision": self.owner_decision(identity(self.attempt()["receipt"]))})

    def advance(self, code=0, contains=None):
        state = self.state()
        current = state["current"]
        target = next((t for t in self.plan["queue"][self.plan["queue"].index(current) + 1:] if t not in state["deferred"]), None)
        scope = identity({"from": current, "to": target, "plan": identity(self.plan)})
        return self.call({"event": "advance", "decision": self.owner_decision(scope)}, code=code, contains=contains)


def wrong_owner(f):
    f.init()
    before = (f.root / "execution.json").read_bytes()
    f.call(f.launch_payload(), owner="intruder", code=3, contains="authority/owner")
    expect((f.root / "execution.json").read_bytes() == before, "wrong owner changed ledger")
    expect(not (f.root / "execution.lock").exists(), "validation failure leaked owned lock")


def schema_paths(f):
    invalid = []
    for mutate in [lambda p: p.update(unknown=True),
                   lambda p: p["spec"].update(revision=True),
                   lambda p: p["queue"].append("T01"),
                   lambda p: p["tickets"][1].update(requires=["T99"]),
                   lambda p: p["tickets"][0].update(requires=["T02"]),
                   lambda p: p.update(feature_acs=["AC-01", "AC-02", "AC-03"]),
                   lambda p: p["tickets"][0]["acs"][0].update(required=False),
                   lambda p: p["spec"]["file"].update(path="../outside"),
                   lambda p: p["spec"]["file"].update(path="tickets/../spec.md")]:
        plan = copy.deepcopy(f.plan)
        mutate(plan)
        invalid.append(plan)
    for plan in invalid:
        f.init(plan, code=2)
        expect(not (f.root / "execution.json").exists(), "invalid init persisted")
    f.call(operation="init", raw=b'{"plan":', code=2, contains="invalid JSON")
    f.call(operation="init", raw=b'{"event":"launch","event":"stop"}', code=2, contains="duplicate JSON")
    linked = f.root / "linked"
    linked.symlink_to(f.workspace, target_is_directory=True)
    plan = copy.deepcopy(f.plan)
    plan["spec"]["file"] = {"path": "linked/file.txt", "sha256": sha((f.workspace / "file.txt").read_bytes())}
    f.init(plan, code=5)
    expect((f.root / "execution.lock").exists(), "parent-symlink I/O error did not retain uncertainty lock")
    (f.root / "execution.lock").unlink()
    linked.unlink()
    original = f.root / "spec.md"
    original.unlink()
    original.symlink_to(f.workspace / "file.txt")
    f.init(code=5)
    expect((f.root / "execution.lock").is_file(), "uncertain I/O lock not retained")
    # Fixture-only cleanup; the production guard never clears this stale lock.
    (f.root / "execution.lock").unlink()
    original.unlink()
    f.ref("spec.md", "approved specification r2\n")
    original.unlink()
    f.init(code=5, contains="No such file")


def race(f):
    f.init()
    payload = json.dumps(f.launch_payload()).encode()
    read_fd, write_fd = os.pipe()
    wrapper = "import os,runpy,sys; os.read(int(os.environ['GUARD_BARRIER_FD']),1); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"
    children = []
    try:
        for _ in range(2):
            child = subprocess.Popen([sys.executable, "-c", wrapper, *f.command()], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(read_fd,),
                     env={**ENV, "GUARD_BARRIER_FD": str(read_fd)})
            children.append(child)
            child.stdin.write(payload)
            child.stdin.close()
            child.stdin = None
        os.close(read_fd)
        read_fd = None
        os.write(write_fd, b"xx")
        os.close(write_fd)
        write_fd = None
        results = [child.communicate(timeout=20) for child in children]
        codes = sorted(child.returncode for child in children)
        expect(codes == [0, 3], "double launch race returned " + str(codes) + ": " + str(results))
        replies = [json.loads(out) for out, _ in results]
        expect(sum(bool(r.get("dispatch")) for r in replies) == 1, "two dispatch checkpoints")
        expect(f.state()["sequence"] == 1 and len(f.state()["attempts"]) == 1, "lost update/double attempt")
        f.sequence = 1
        f.call(f.launch_payload(), code=3, contains="already launched")
        f.call({"event": "block", "reason": "stale call"}, sequence=0, code=3, contains="sequence")
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate()
        for fd in (read_fd, write_fd):
            if fd is not None:
                os.close(fd)


def launch_recovery(f):
    f.init()
    f.call({"event": "pending", "handle": "unbound"}, code=4, contains="launch intent")
    f.call({"event": "write-go", "id": "bad", "preflight": f.evidence, "observed": f.plan["input"]}, code=4)
    f.launch()
    outcome = {"clientThreadId": "client-pending-1"}
    scripted_outcomes = [outcome]
    print("SCRIPTED App outcome:", json.dumps({"actor": "coordinator", "tool": "create_thread", "checkpoint": f.launch_checkpoint, "outcome": outcome}))
    f.call({"event": "pending", "handle": outcome["clientThreadId"]})
    expect(f.attempt()["peer"] is None, "pending became bound peer")
    f.call({"event": "reconcile", "candidates": [], "evidence": f.evidence})
    expect(f.attempt()["state"] == "Blocked", "unknown zero candidates did not block")
    before = {p.relative_to(f.root).as_posix(): p.read_bytes() for p in f.root.rglob("*") if p.is_file()}
    for operation in ("status", "resume"):
        result = f.call(operation=operation)
        expect(result["dispatch"] is None and result["reconciliation_required"], "resume blindly retried create")
    expect(before == {p.relative_to(f.root).as_posix(): p.read_bytes() for p in f.root.rglob("*") if p.is_file()}, "status/resume wrote files")
    candidate = {k: f.attempt()["intent"][k] for k in ("marker", "project", "context_sha256")}
    candidate["peer"] = {"thread": "peer", "host": "local"}
    f.call({"event": "reconcile", "candidates": [candidate, candidate], "evidence": f.evidence})
    expect(f.attempt()["state"] == "Blocked", "ambiguous peers accepted")
    wrong = copy.deepcopy(candidate)
    wrong["context_sha256"] = "c" * 64
    f.call({"event": "reconcile", "candidates": [wrong], "evidence": f.evidence}, code=4)
    f.call({"event": "reconcile", "candidates": [candidate], "evidence": f.evidence})
    print("SCRIPTED recovery:", json.dumps({"scripted_create_outcomes": len(scripted_outcomes), "unknown_zero": "Blocked", "duplicate": "Blocked", "bound_peer": candidate["peer"],
                                            "limit": "guard/protocol trace; no live App/skill execution"}))
    changed = copy.deepcopy(f.plan["input"])
    changed["sha256"] = "f" * 64
    f.call({"event": "write-go", "id": "bad", "preflight": f.evidence, "observed": changed}, code=4)
    f.write_go()


def receipts_release(f):
    f.running()
    f.advance(code=4, contains="not accepted")
    value = f.result()
    for field, replacement in (("ticket", "T02"), ("attempt", 2), ("source_sha256", "f" * 64), ("write_go", "old-write")):
        bad = copy.deepcopy(value)
        bad[field] = replacement
        f.call({"event": "result", "receipt": bad}, code=4, contains="stale result")
    f.call({"event": "result", "receipt": value})
    f.call({"event": "await"}, code=4)
    release = f.release(value)
    bad_release = {**release, "verified_stopped": False}
    f.call({"event": "writer-release", "release": bad_release}, code=4, contains="unverified")
    f.call({"event": "writer-release", "release": release})
    f.call({"event": "await"}, code=4, contains="review")
    # Each new malformed receipt is installed only by the public result event, before release.
    f.call({"event": "block", "reason": "bounded fixture fix"})
    f.write_go("write-2")
    expect(f.attempt()["release"] is None and f.attempt()["receipt"] is None, "fix reused release/result")
    f.call({"event": "writer-release", "release": release}, code=4, contains="unverified")
    value = f.result("result-2")
    for mutate in [lambda r: r.update(acs=[]), lambda r: r["acs"][0].update(verdict="BLOCKED"),
                   lambda r: r["checks"][0].update(exit_code=1)]:
        bad = copy.deepcopy(value)
        mutate(bad)
        f.call({"event": "result", "receipt": bad})
        f.call({"event": "writer-release", "release": f.release(bad)})
        f.call({"event": "await"}, code=4)
        f.call({"event": "block", "reason": "repair invalid proof"})
        f.write_go("write-" + str(f.sequence))
        value = f.result("result-" + str(f.sequence))
    f.review(value)
    f.call({"event": "result", "receipt": value})
    f.call({"event": "writer-release", "release": f.release(value)})
    (f.workspace / "file.txt").write_text("late writer change\n", encoding="utf-8")
    f.call({"event": "await"}, code=4, contains="stale workspace")
    (f.workspace / "file.txt").write_text("baseline\n", encoding="utf-8")
    old = (f.root / value["file"]["path"]).read_bytes()
    (f.root / value["file"]["path"]).write_text("changed receipt", encoding="utf-8")
    f.call({"event": "await"}, code=4, contains="stale artifact")
    (f.root / value["file"]["path"]).write_bytes(old)
    f.call({"event": "await"})
    f.call({"event": "accept", "decision": f.owner_decision("f" * 64)}, code=4, contains="scope mismatch")
    f.accept()
    f.advance(code=4, contains="stage gate")
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance()
    f.launch()
    expect(f.state()["current"] == "T02" and f.attempt()["state"] == "Launching", "valid next launch failed")


def dirty_handoff(f):
    baseline = f.workspace / "accepted-T02.md"
    baseline.write_text("accepted predecessor dirty content\n", encoding="utf-8")
    f.plan["input"] = f.snapshot("dirty-input")
    f.running()
    (f.workspace / "file.txt").write_text("authorized T03 change\n", encoding="utf-8")
    value = f.result("dirty-result")
    f.call({"event": "result", "receipt": value})
    bad = copy.deepcopy(value)
    bad["result"]["files"] = [item for item in bad["result"]["files"] if item["path"] != "accepted-T02.md"]
    bad["result"]["sha256"] = identity({"workspaces": f.plan["workspaces"], "patch": bad["result"]["patch"]["sha256"],
                                        "files": bad["result"]["files"], "untracked": []})
    f.call({"event": "result", "receipt": bad}, code=4, contains="omits baseline")
    baseline.write_text("unauthorized predecessor edit\n", encoding="utf-8")
    bad = f.result("bad-dirty-result")
    f.call({"event": "result", "receipt": bad}, code=4, contains="outside write scope")
    baseline.write_text("accepted predecessor dirty content\n", encoding="utf-8")
    f.review(value)
    f.call({"event": "result", "receipt": value})
    f.call({"event": "writer-release", "release": f.release(value)})
    f.call({"event": "await"})


def complete_feature(f):
    f.running()
    print("SCRIPTED App outcome:", json.dumps({"actor": "coordinator", "tool": "create_thread", "checkpoint": f.launch_checkpoint,
                                               "outcome": {"threadId": f.attempt()["peer"]["thread"], "hostId": "local"}}))
    (f.workspace / "file.txt").write_text("accepted predecessor result\n", encoding="utf-8")
    f.await_result()
    f.accept()
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance()
    before = {p.relative_to(f.root).as_posix(): p.read_bytes() for p in f.root.rglob("*") if p.is_file()}
    for operation in ("status", "resume"):
        response = f.call(operation=operation)
        expect(response["state"]["current"] == "T02" and response["dispatch"] is None,
               "Planned handoff read lost the next ticket or dispatched work")
    expect(before == {p.relative_to(f.root).as_posix(): p.read_bytes() for p in f.root.rglob("*") if p.is_file()},
           "Planned handoff status/resume changed ledger, budget or files")
    f.launch()
    f.bind()
    print("SCRIPTED App outcome:", json.dumps({"actor": "coordinator", "tool": "create_thread", "checkpoint": f.launch_checkpoint,
                                               "outcome": {"threadId": f.attempt()["peer"]["thread"], "hostId": "local"}}))
    f.write_go("write-t02")
    (f.workspace / "file.txt").write_text("final authorized result\n", encoding="utf-8")
    value = f.result("t02-result")
    f.call({"event": "result", "receipt": value})
    f.call({"event": "writer-release", "release": f.release(value)})
    f.call({"event": "await"})
    f.accept()
    scope = identity({"plan": identity(f.plan), "receipts": [a["receipt"]["file"] for a in f.state()["attempts"]]})
    f.call({"event": "done", "decision": f.owner_decision(scope)}, code=4, contains="final gate")
    f.call({"event": "gate", "stage": None, "id": "integration", "evidence": f.evidence})
    result = f.call({"event": "done", "decision": f.owner_decision(scope)})
    expect(result["state"] == "Done", "terminal state projection wrong")
    for operation in ("status", "resume"):
        response = f.call(operation=operation)
        expect(response["state"]["done"] and response["dispatch"] is None, "Done resume relaunched work")
    changed = copy.deepcopy(f.plan)
    changed["spec"] = {"revision": 3, "file": f.ref("spec-r3.md", "owner approved new scope r3\n")}
    f.change(changed)
    f.launch(restart=True)
    f.bind()
    f.write_go("write-reopened-t01")
    expect(f.state()["budgets"]["RB-T01"]["full_used"] == 1, "reopened scope reset review budget")


def output_limit(f):
    f.init()
    before = (f.root / "execution.json").read_bytes()
    payload = f.launch_payload()
    payload["intent"]["decision"]["statement"] = "x" * (2200 * 1024)
    expect(len(json.dumps(payload).encode()) < 4 * 1024 * 1024, "boundary request exceeds public input limit")
    response = f.call(payload, code=2, contains="serialized ledger exceeds size limit")
    expect(response.get("dispatch") is None, "oversize output returned a dispatch checkpoint")
    expect((f.root / "execution.json").read_bytes() == before, "oversize output replaced readable prior ledger")
    expect(not (f.root / "execution.lock").exists() and not list(f.root.glob(".execution-*.tmp")),
           "oversize refusal left a lock or temporary ledger")
    for operation in ("status", "resume"):
        response = f.call(operation=operation)
        expect(response["state"]["sequence"] == 0 and response["dispatch"] is None,
               "oversize refusal changed sequence or allowed dispatch")
    f.launch()


def preflight_stop_release(f):
    f.init()
    f.launch()
    f.bind()
    attempt = f.attempt()
    scope = identity({"ticket": "T01", "attempt": 1, "source": attempt["source_sha256"]})
    f.call({"event": "stop", "decision": f.owner_decision(scope)})
    f.call({"event": "writer-release", "release": f.release({"result": f.snapshot("preflight-stopped")})})
    f.launch(restart=True)
    f.bind()
    f.write_go("first-write-after-preflight-stop")


def stop_budget_revision(f):
    f.running()
    f.review(f.result("initial-review"))
    f.call({"event": "review-reserve", "id": "second-full", "kind": "full", "candidate": f.snapshot("second-full"),
            "quiescence": f.evidence}, code=4, contains="budget exhausted")
    before = (f.root / "execution.json").read_bytes()
    f.call(operation="resume")
    expect((f.root / "execution.json").read_bytes() == before, "resume reset review budget")
    attempt = f.attempt()
    stop_scope = identity({"ticket": "T01", "attempt": 1, "source": attempt["source_sha256"]})
    f.call({"event": "stop", "decision": f.owner_decision(stop_scope)})
    f.call(f.launch_payload(restart=True), code=4, contains="release")
    value = f.result("stopped-result")
    f.call({"event": "writer-release", "release": f.release(value)})
    f.launch(restart=True)

    f.bind()
    f.write_go("write-restart")
    expect(f.state()["budgets"]["RB-T01"]["full_used"] == 1, "restart reset review budget")
    f.call({"event": "review-reserve", "id": "restart-full", "kind": "full", "candidate": f.snapshot("restart-full"),
            "quiescence": f.evidence}, code=4)
    f.review(f.result("restart-fix"), kind="fix")
    f.call({"event": "block", "reason": "source revision change"})
    value = f.result("before-revise")
    f.call({"event": "writer-release", "release": f.release(value)})
    changed = copy.deepcopy(f.plan)
    changed["spec"] = {"revision": 3, "file": f.ref("spec-r3.md", "approved specification scope r3\n")}
    f.change(changed)
    f.call({"event": "write-go", "id": "stale-revision", "preflight": f.evidence, "observed": value["result"]}, code=4, contains="stale launch source")
    expect(f.state()["budgets"]["RB-T01"]["full_used"] == 1, "revision reset review budget")
    f.launch(restart=True)


def bump(f, plan, ticket):
    task = next(t for t in plan["tickets"] if t["id"] == ticket)
    revision = task["source"]["revision"] + 1
    task["source"] = {"revision": revision, "file": f.ref("tickets/" + ticket + "-r" + str(revision) + ".md", ticket + " contract r" + str(revision) + "\n")}


def receiver(f, plan, ticket, source, ac="AC1"):
    donor = next(t for t in plan["tickets"] if t["id"] == source)
    task = copy.deepcopy(donor)
    task.update(id=ticket, source={"revision": 1, "file": f.ref("tickets/" + ticket + ".md", ticket + " receiving contract\n")},
                acs=[{"id": ticket + "-" + ac, "feature_acs": ["AC-01"], "required": True}])
    plan["tickets"].append(task)
    return task


def move(source, ac, target, target_ac="AC1"):
    return {"from": {"ticket": source, "ac": source + "-" + ac}, "to": {"ticket": target, "ac": target + "-" + target_ac}}


def review_lifecycle(f):
    f.running()
    value = f.result("review-candidate")
    reserve = {"event": "review-reserve", "id": "review-crash", "kind": "full", "candidate": value["result"], "quiescence": f.evidence}
    wrapper = "import os,runpy,sys\nsys.argv=sys.argv[1:]\ntry: runpy.run_path(sys.argv[0],run_name='__main__')\nexcept SystemExit as e:\n if e.code == 0: os._exit(73)\n raise\n"
    f.call(reserve, code=73, wrapper=wrapper)
    state = f.state()
    f.sequence = state["sequence"]
    expect(state["reviews"][0]["phase"] == "reserved" and state["budgets"]["RB-T01"]["full_used"] == 1,
           "crash lost reservation/debit")
    before = (f.root / "execution.json").read_bytes()
    for command in ("status", "resume"):
        reply = f.call(operation=command)
        expect(reply["dispatch"] is None and reply["review_dispatch"] is None, "read regenerated review/peer grant")
    f.call(reserve, code=3, contains="already reserved")
    expect((f.root / "execution.json").read_bytes() == before, "retry debited or rewrote reservation")
    value["review"].update(id="review-crash", verdict="APPROVED")
    f.call({"event": "result", "receipt": value})
    f.call({"event": "await"}, code=4, contains="completed independent review")
    binding = state["reviews"][0]["binding_sha256"]
    completion = {"event": "review-complete", "id": "review-crash", "binding_sha256": binding,
                  "verdict": "APPROVED", "evidence": f.evidence, "observation": f.evidence}
    f.call(completion)
    before = (f.root / "execution.json").read_bytes()
    f.call(completion, code=3, contains="already completed")
    expect((f.root / "execution.json").read_bytes() == before, "duplicate completion mutated state")
    first_approved = copy.deepcopy(value)
    f.review(value, kind="fix", verdict="CHANGES_REQUESTED", name="review-later-rejection")
    f.call({"event": "result", "receipt": first_approved})
    f.call({"event": "writer-release", "release": f.release(first_approved)})
    before = (f.root / "execution.json").read_bytes()
    f.call({"event": "await"}, code=4, contains="completed independent review")
    f.call({"event": "accept", "decision": f.owner_decision(identity(first_approved))}, code=4, contains="not awaiting")
    expect((f.root / "execution.json").read_bytes() == before, "superseded proof refusal changed history or budget")
    f.call({"event": "result", "receipt": value}, code=4, contains="running writer")
    f.call({"event": "block", "reason": "review rejected candidate"})
    f.write_go("review-fix-write")
    (f.workspace / "file.txt").write_text("fixed reviewed candidate\n", encoding="utf-8")
    fixed = f.result("review-fixed")
    fixed["review"].update(id="review-crash", verdict="APPROVED")
    f.call({"event": "result", "receipt": fixed})
    f.call({"event": "await"}, code=4, contains="completed independent review")
    f.review(fixed, kind="fix", name="review-fix")
    f.call({"event": "result", "receipt": fixed})
    f.call({"event": "writer-release", "release": f.release(fixed)})
    f.call({"event": "await"})
    f.accept()
    state = f.state()
    expect(state["budgets"]["RB-T01"] == {"full_limit": 1, "fix_limit": 2, "full_used": 1, "fix_used": 2}, "completion/fix changed debit accounting")
    expect([(r["id"], r["verdict"]) for r in state["reviews"]] == [("review-crash", "APPROVED"),
           ("review-later-rejection", "CHANGES_REQUESTED"), ("review-fix", "APPROVED")], "fresh binding rewrote contradictory review history")


def failed_review(f):
    f.running()
    value = f.result("failed-review-candidate")
    f.review(value, verdict="FAILED")
    f.call({"event": "result", "receipt": value})
    f.call({"event": "writer-release", "release": f.release(value)})
    f.call({"event": "await"}, code=4, contains="completed independent review")


def transfer_pools(f):
    source = f.plan["tickets"][0]
    source["acs"] += [{"id": "T01-AC" + str(n), "feature_acs": ["AC-01"], "required": True} for n in (2, 3)]
    f.running()
    f.call({"event": "writer-release", "release": f.release(f.result("partial-input"))})
    split = copy.deepcopy(f.plan)
    for ac in split["tickets"][0]["acs"][1:]:
        ac["required"] = False
    bump(f, split, "T01")
    receiver(f, split, "T03", "T01")
    receiver(f, split, "T04", "T01")
    split["queue"] = ["T01", "T03", "T04", "T02"]
    split["stages"][0]["required"] = ["T01", "T03", "T04"]
    split["tickets"][1]["requires"] = ["T01", "T03", "T04"]
    bump(f, split, "T02")
    moves = [move("T01", "AC2", "T03"), move("T01", "AC3", "T04")]
    stages = [{"from": "S1", "to": ["S1"], "evidence": f.evidence}]
    deps = [{"ticket": "T02", "from": ["T01"], "to": ["T01", "T03", "T04"], "evidence": f.evidence}]
    before = (f.root / "execution.json").read_bytes()
    bad = copy.deepcopy(split)
    bad["tickets"][0]["acs"].pop(1)
    f.change(bad, "partial", moves=moves, stages=stages, dependencies=deps, code=4, contains="ticket AC lost")
    bad = copy.deepcopy(split)
    bad["tickets"][-2]["acs"][0]["required"] = False
    f.change(bad, "partial", moves=moves, stages=stages, dependencies=deps, code=4, contains="receiving AC")
    f.change(split, "partial", moves=moves + [moves[0]], stages=stages, dependencies=deps, code=2, contains="duplicate source move")
    bad = copy.deepcopy(split)
    bad["tickets"][1]["requires"] = []
    bump(f, bad, "T02")
    f.change(bad, "partial", moves=moves, stages=stages, code=4, contains="dependency remap")
    f.change(bad, "partial", moves=moves, stages=stages,
             dependencies=[{"ticket": "T02", "from": ["T01"], "to": [], "evidence": f.evidence}], code=4, contains="producer obligations")
    bad = copy.deepcopy(split)
    bad["stages"][0]["gates"] = []
    f.change(bad, "partial", moves=moves, stages=stages, dependencies=deps, code=4, contains="gate removal")
    expect((f.root / "execution.json").read_bytes() == before, "invalid transfer mutated ledger")
    f.change(split, "partial", moves=moves, stages=stages, dependencies=deps)
    expect(f.state()["current"] == "T01" and f.state()["ticket_pools"]["T03"] == ["RB-T01"]
           and f.state()["ticket_pools"]["T04"] == ["RB-T01"] and set(f.state()["budgets"]) == {"RB-T01", "RB-T02"}, "split multiplied pools or advanced")
    f.launch(restart=True)
    f.bind()
    f.write_go("partial-revision-write")
    f.await_result()
    f.accept()
    f.advance()
    f.launch()
    f.bind()
    f.write_go("receiver-t03-write")
    value = f.result("merge-input")
    f.review(value, kind="fix")
    f.call({"event": "result", "receipt": value})
    f.call({"event": "writer-release", "release": f.release(value)})
    merged = copy.deepcopy(f.plan)
    next(t for t in merged["tickets"] if t["id"] == "T03")["acs"][0]["required"] = False
    bump(f, merged, "T03")
    bump(f, merged, "T04")
    merged["stages"][0]["required"] = ["T01", "T04"]
    f.change(merged, "defer", moves=[move("T03", "AC1", "T04")], stages=stages)
    expect(f.state()["current"] == "T03" and f.state()["ticket_pools"]["T04"] == ["RB-T01"], "merge advanced or duplicated shared pool")
    f.advance()
    f.launch()
    f.bind()
    f.write_go("receiver-t04-write")
    value = f.result("repeat-input")
    f.review(value, kind="fix")
    f.call({"event": "writer-release", "release": f.release(value)})
    repeated = copy.deepcopy(f.plan)
    next(t for t in repeated["tickets"] if t["id"] == "T04")["acs"][0]["required"] = False
    bump(f, repeated, "T04")
    receiver(f, repeated, "T05", "T04")
    repeated["queue"].insert(-1, "T05")
    repeated["stages"][0]["required"] = ["T01", "T05"]
    repeated["tickets"][1]["requires"] = ["T01", "T05"]
    bump(f, repeated, "T02")
    f.change(repeated, "defer", moves=[move("T04", "AC1", "T05")], stages=stages,
             dependencies=[{"ticket": "T02", "from": ["T01", "T03", "T04"], "to": ["T01", "T05"], "evidence": f.evidence}])
    f.advance()
    f.launch()
    f.bind()
    f.write_go("receiver-t05-write")
    before = (f.root / "execution.json").read_bytes()
    f.call({"event": "review-reserve", "id": "exhausted-transfer", "kind": "fix", "candidate": f.snapshot("exhausted"), "quiescence": f.evidence}, code=4, contains="budget exhausted")
    expect((f.root / "execution.json").read_bytes() == before and f.state()["budgets"]["RB-T01"]["fix_used"] == 2, "repeated transfer reset/spent exhausted pool")
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence}, code=4, contains="not accepted")


def deferred_readiness(f):
    f.running()
    f.call({"event": "writer-release", "release": f.release(f.result("deferred-input"))})
    deferred = copy.deepcopy(f.plan)
    deferred["tickets"][0]["acs"][0]["required"] = False
    bump(f, deferred, "T01")
    receiver(f, deferred, "T03", "T01")
    deferred["queue"] = ["T01", "T03", "T02"]
    deferred["stages"][0]["required"] = ["T03"]
    stages = [{"from": "S1", "to": ["S1"], "evidence": f.evidence}]
    f.change(deferred, "defer", moves=[move("T01", "AC1", "T03")], stages=stages)
    f.call({"event": "accept", "decision": f.owner_decision("a" * 64)}, code=4, contains="not awaiting")
    f.advance()
    f.launch()
    f.bind()
    f.write_go("deferred-receiver-write")
    f.await_result()
    f.accept()
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance(code=4, contains="technical prerequisite")
    repaired = copy.deepcopy(f.plan)
    repaired["tickets"][1]["requires"] = ["T03"]
    bump(f, repaired, "T02")
    # The original dependency still names a Deferred producer: queue bypass never changes it.
    f.change(repaired, dependencies=[{"ticket": "T02", "from": ["T01"], "to": ["T03"], "evidence": f.evidence}])
    f.advance(code=4, contains="stage gate")
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance()
    f.launch()
    f.bind()
    f.write_go("dependency-remapped-write")
    f.await_result()
    f.accept()
    f.call({"event": "gate", "stage": None, "id": "integration", "evidence": f.evidence})
    # Final receipt order follows the approved queue, not attempt creation order.
    scope = identity({"plan": identity(f.plan), "receipts": [next(a for a in f.state()["attempts"] if a["ticket"] == t)["receipt"]["file"] for t in ("T03", "T02")]})
    reply = f.call({"event": "done", "decision": f.owner_decision(scope)})
    expect(reply["state"] == "Done" and f.state()["attempts"][0]["state"] == "Deferred", "completion relabeled Deferred as Accepted")


def pool_merge_atomic(f):
    f.plan["tickets"][1]["requires"] = []
    f.running()
    value = f.result("multi-pool-input")
    f.review(value)
    f.call({"event": "writer-release", "release": f.release(value)})
    merged = copy.deepcopy(f.plan)
    merged["tickets"][0]["acs"][0]["required"] = False
    merged["tickets"][0]["stage"] = "S2"
    merged["tickets"][1]["acs"].append({"id": "T02-AC2", "feature_acs": ["AC-01"], "required": True})
    merged["tickets"][1]["review_required"] = True
    bump(f, merged, "T01")
    bump(f, merged, "T02")
    merged["stages"] = [{"id": "S2", "required": ["T02"], "gates": ["S1-ready"]}]
    stages = [{"from": "S1", "to": ["S2"], "evidence": f.evidence}, {"from": "S2", "to": ["S2"], "evidence": f.evidence}]
    gates = [{"from": {"stage": "S1", "id": "S1-ready"}, "to": {"stage": "S2", "id": "S1-ready"}, "evidence": f.evidence}]
    f.change(merged, "defer", moves=[move("T01", "AC1", "T02", "AC2")], stages=stages, gates=gates)
    f.advance()
    f.launch()
    f.bind()
    f.write_go("multi-pool-write")
    expect(f.state()["ticket_pools"]["T02"] == ["RB-T01", "RB-T02"], "merge lost/doubled pool reference")
    before = (f.root / "execution.json").read_bytes()
    for kind in ("full", "fix"):
        f.call({"event": "review-reserve", "id": "multi-" + kind, "kind": kind, "candidate": f.snapshot("multi-" + kind),
                "quiescence": f.evidence}, code=4, contains="budget exhausted/incompatible")
        expect((f.root / "execution.json").read_bytes() == before, "multi-pool refusal partially debited counters")


def scoped_reuse(f, include_proof=True):
    producer = "producer invariant\n"
    original_spec = producer + "consumer v1\n"
    f.plan["spec"]["file"] = f.ref("spec.md", original_spec)
    f.plan["tickets"][0]["scope"]["spec"] = [{"start": 0, "end": len(producer.encode())}]
    f.plan["tickets"][1]["scope"]["spec"] = [{"start": len(producer.encode()), "end": len(original_spec.encode())}]
    f.running()
    (f.workspace / "file.txt").write_text("accepted producer output\n", encoding="utf-8")
    accepted_receipt = f.await_result()
    f.accept()
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance()
    f.launch()
    f.bind()
    f.write_go("consumer-before-transfer")
    candidate = f.result("consumer-before-transfer")
    f.call({"event": "writer-release", "release": f.release(candidate)})
    before = f.state()
    origin = copy.deepcopy(before["attempts"][0])
    changed = copy.deepcopy(f.plan)
    archive = f.ref("artifacts/spec-r2.md", original_spec)
    changed_spec = producer + "consumer v2 transferred\n"
    changed["spec"] = {"revision": 3, "file": f.ref("spec.md", changed_spec)}
    changed["tickets"][1]["acs"][0]["required"] = False
    changed["tickets"][1]["scope"]["spec"] = [{"start": len(producer.encode()), "end": len(changed_spec.encode())}]
    bump(f, changed, "T02")
    receiving = receiver(f, changed, "T03", "T02")
    receiving["acs"][0]["feature_acs"] = ["AC-02"]
    changed["queue"].append("T03")
    changed["stages"][1]["required"] = ["T03"]
    proof = {"ticket": "T01", "accepted_attempt": origin["number"], "accepted_plan_sha256": origin["plan_sha256"],
             "accepted_source_sha256": origin["source_sha256"], "receipt": origin["receipt"]["file"],
             "result_sha256": origin["receipt"]["result"]["sha256"], "release_sha256": identity(origin["release"]),
             "target_plan_sha256": identity(changed), "observed": candidate["result"],
             "archived_sources": [{"original": f.plan["spec"]["file"], "copy": archive}], "evidence": f.evidence}
    moves = [move("T02", "AC1", "T03")]
    stages = [{"from": "S2", "to": ["S2"], "evidence": f.evidence}]
    if not include_proof:
        f.change(changed, "defer", moves=moves, stages=stages)
        reply = f.call(operation="resume")
        expect(reply["state"]["current"] == "T01" and reply["effective_state"] == "Blocked", "missing proof reused stale approval")
        expect(f.state()["attempts"][0] == origin, "invalidation rewrote historical acceptance")
        return
    for mutate, message in [(lambda r: r.update(result_sha256="0" * 64), "historical binding"),
                            (lambda r: r.update(archived_sources=[]), "stale artifact")]:
        bad = copy.deepcopy(proof)
        mutate(bad)
        f.change(changed, "defer", moves=moves, stages=stages, reuse=[bad], code=4, contains=message)
    affected = copy.deepcopy(changed)
    affected["tickets"][0]["source"]["revision"] += 1
    bad = {**proof, "target_plan_sha256": identity(affected)}
    f.change(affected, "defer", moves=moves, stages=stages, reuse=[bad], code=4, contains="affected ticket scope")
    affected = copy.deepcopy(changed)
    affected["spec"]["file"] = f.ref("spec.md", "producer ALTERED!!\nconsumer v2 transferred\n")
    bad = {**proof, "target_plan_sha256": identity(affected)}
    f.change(affected, "defer", moves=moves, stages=stages, reuse=[bad], code=4, contains="source scope changed")
    f.ref("spec.md", changed_spec)
    f.change(changed, "defer", moves=moves, stages=stages, reuse=[proof])
    state = f.state()
    expect(state["current"] == "T02" and state["attempts"][0] == origin and state["reviews"] == before["reviews"]
           and state["budgets"] == before["budgets"] and state["history"][:len(before["history"])] == before["history"],
           "scoped reuse retargeted accepted identity, history or budget")
    f.call(operation="status")
    (f.workspace / "file.txt").write_text("changed accepted output\n", encoding="utf-8")
    f.call(operation="resume", code=4, contains="accepted output changed")
    (f.workspace / "file.txt").write_text("accepted producer output\n", encoding="utf-8")
    f.advance(code=4, contains="stage gate")
    f.call({"event": "gate", "stage": "S1", "id": "S1-ready", "evidence": f.evidence})
    f.advance()
    f.launch()
    f.bind()
    f.write_go("scoped-receiver-write")
    f.call({"event": "result", "receipt": accepted_receipt}, code=4, contains="stale result receipt")
    f.await_result()
    f.accept()


def root_lock_corruption(f):
    f.init()
    copy_root = f.root.parent / "copied-feature"
    shutil.copytree(f.root, copy_root)
    original = f.root
    f.root = copy_root
    f.call(operation="status", code=3, contains="authority")
    f.root = original
    ledger = f.root / "execution.json"
    original_bytes = ledger.read_bytes()
    state = f.state()
    state["schema"] = "unknown/99"
    ledger.write_text(json.dumps(state), encoding="utf-8")
    f.call(operation="status", code=2)
    ledger.write_bytes(b'{"broken":')
    f.call(operation="resume", code=2, contains="invalid JSON")
    ledger.write_bytes(original_bytes)
    lock = f.root / "execution.lock"
    lock.write_text("damaged/stale lock", encoding="utf-8")
    f.call(f.launch_payload(), code=3, contains="stale lock")
    expect(lock.read_text() == "damaged/stale lock", "stale lock was removed")
    f.call(operation="status", code=4, contains="existing lock")
    lock.unlink()
    original_spec = (f.root / "spec.md").read_bytes()
    (f.root / "spec.md").write_text("new source revision", encoding="utf-8")
    f.call(f.launch_payload(), code=4, contains="stale artifact")
    (f.root / "spec.md").write_bytes(original_spec)
    f.init(code=3, contains="already initialized")


FAULT_WRAPPER = r'''
import os,runpy,stat,sys
mode=os.environ['GUARD_FAULT']
root=sys.argv[sys.argv.index('--root')+1]
original_replace,original_fsync=os.replace,os.fsync
replaced=False
def replace(*args,**kwargs):
    global replaced
    if mode=='before-replace': os._exit(71)
    original_replace(*args,**kwargs)
    replaced=True
    if mode=='after-replace': os._exit(72)
def fsync(fd):
    info=os.fstat(fd)
    lock=os.stat(root+'/execution.lock')
    if mode=='file-fsync' and stat.S_ISREG(info.st_mode) and info.st_ino!=lock.st_ino:
        raise OSError('injected ledger file fsync failure')
    if mode=='directory-fsync' and stat.S_ISDIR(info.st_mode) and replaced:
        raise OSError('injected ledger directory fsync failure')
    original_fsync(fd)
os.replace,os.fsync=replace,fsync
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''


def faults(helper):
    for mode in ("before-replace", "after-replace", "file-fsync", "directory-fsync"):
        f = Fixture(helper)
        try:
            f.init()
            before = (f.root / "execution.json").read_bytes()
            payload = f.launch_payload()
            old = ENV.get("GUARD_FAULT")
            ENV["GUARD_FAULT"] = mode
            try:
                f.call(payload, code={"before-replace": 71, "after-replace": 72}.get(mode, 5),
                       contains="fsync failure" if mode.endswith("fsync") else None, wrapper=FAULT_WRAPPER)
            finally:
                if old is None:
                    ENV.pop("GUARD_FAULT", None)
                else:
                    ENV["GUARD_FAULT"] = old
            state = f.state()
            expect((f.root / "execution.lock").exists(), mode + " lost unresolved lock")
            if mode in {"before-replace", "file-fsync"}:
                expect((f.root / "execution.json").read_bytes() == before, mode + " replaced ledger")
            else:
                expect(state["sequence"] == 1 and state["attempts"][0]["state"] == "Launching", mode + " left torn ledger")
            f.sequence = state["sequence"]
            f.call(operation="status", code=4, contains="existing lock")
            f.call(payload, code=3, contains="stale lock")
            print("PASS:", mode, "(real filesystem; no dispatch response)")
        finally:
            f.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, default=HELPER)
    parser.add_argument("--case", help="Exact case name; omit for all CLI/filesystem checks")
    args = parser.parse_args()
    cases = [("wrong-owner", wrong_owner), ("schema/paths/I/O", schema_paths), ("two-process race/sequence", race),
             ("durable launch/reconciliation", launch_recovery), ("receipt/release/acceptance/stage", receipts_release),
             ("dirty baseline/scope", dirty_handoff), ("complete feature/final gate", complete_feature),
             ("serialized output limit", output_limit), ("preflight stop/release", preflight_stop_release), ("stop/restart/review/revision", stop_budget_revision), ("canonical root/lock/corruption", root_lock_corruption),
             ("review-lifecycle", review_lifecycle), ("failed-review", failed_review), ("transfer-pools", transfer_pools), ("deferred-readiness", deferred_readiness),
             ("pool-merge-atomic", pool_merge_atomic), ("scoped-reuse", scoped_reuse), ("reuse-absent", lambda f: scoped_reuse(f, False))]
    if args.case and args.case not in {name for name, _ in cases}:
        parser.error("unknown case")
    for name, case in cases:
        if args.case and args.case != name:
            continue
        fixture = Fixture(args.helper.resolve())
        try:
            case(fixture)
            print("PASS:", name)
        finally:
            fixture.close()
    if not args.case:
        faults(args.helper.resolve())
    print("OK: feature guard CLI/filesystem contracts; no App runtime claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
