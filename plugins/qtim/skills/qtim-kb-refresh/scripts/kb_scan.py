#!/usr/bin/env python3
"""Codex qtim knowledge scan, snapshot, loss check, and guarded checked stamp.

Scan and loss check are read-only. No command fetches, checks out, deletes, or
reads external agent memory. All output uses JSON schema kb_scan/1.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

SCHEMA = "kb_scan/1"
FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
CHECKED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) @ ([0-9a-f]{7,40})$")
ANCHOR_RE = re.compile(r"\x60([^\x60\n]+)#([A-Za-z_][\w.:@/$*\[\]-]*)\x60")
LINE_REF_RE = re.compile(r"\x60[^\x60\n]+\.(?:ts|tsx|js|vue|py|go|rs|json|ya?ml|md):\d+\x60")
MARK_RE = re.compile(r"(?<!\w)(?:policy|claimed):")
OPEN_RE = re.compile(r"(?<!\w)open:")
WORD_RE = re.compile(r"[\w-]+", re.UNICODE)
CLAIM_RE = re.compile(r"^\s*(?:[-*+]\s+\S|\d+[.)]\s+\S|\|)")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}[\s:|-]*$")
RUN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
FEATURE_STATUS_RE = re.compile(r"^\s*(?:[-*>]\s*)?(?:\*\*)?(?:Status|Статус)(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*?)\s*$", re.I)
REQUIRED_META = ("type", "genre", "audience", "updated", "checked", "status")
CANON_FEATURES = {"feature-brief.md", "intake.md", "prd.md", "decomposition.md", "estimate.md", "plan.md"}
ENTRY_WARN_WORDS = 1800


class ScanError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def git(*args: str, cwd: Path, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    if check and proc.returncode:
        raise ScanError("git_failed", proc.stderr.strip() or "git command failed")
    return proc.stdout if proc.returncode == 0 else ""


def git_ok(*args: str, cwd: Path) -> bool:
    return subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode == 0


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd()).strip()).resolve()


def resolve_commit(repo: Path, ref: str) -> str | None:
    return git("rev-parse", "--verify", "--quiet", ref + "^{commit}", cwd=repo, check=False).strip() or None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = FM_RE.match(text)
    return (match.group(1), text[match.end():]) if match else (None, text)


def metadata(text: str) -> dict[str, str]:
    fm, _ = split_frontmatter(text)
    if fm is None:
        return {}
    values: dict[str, str] = {}
    in_meta = False
    for line in fm.splitlines():
        if line == "metadata:":
            in_meta = True
            continue
        if not line.startswith((" ", "\t")):
            in_meta = False
        match = re.match(r"^\s*([A-Za-z_][\w-]*):\s*(.*?)\s*$", line)
        if match and (match.group(1) in ("name", "description") or in_meta):
            values[match.group(1)] = match.group(2).strip("'\"")
    return values


def checked_sha(meta: dict[str, str]) -> str | None:
    match = CHECKED_RE.fullmatch(meta.get("checked", ""))
    return match.group(2) if match else None


def content_lines(text: str) -> list[tuple[int, str]]:
    fm, body = split_frontmatter(text)
    first = text[:len(text) - len(body)].count("\n") + 1 if fm is not None else 1
    lines: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(body.splitlines(), first):
        marker = re.match(r"^\s*(\x60\x60\x60|~~~)", line)
        if marker:
            fence = None if fence == marker.group(1) else marker.group(1)
        elif fence is None:
            lines.append((number, line))
    return lines


def anchors(lines: list[tuple[int, str]]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for number, line in lines:
        for match in ANCHOR_RE.finditer(line):
            path, symbol = match.groups()
            path = path.removeprefix("./")
            pure = PurePosixPath(path)
            if not path or pure.is_absolute() or ".." in pure.parts or ":" in path:
                continue
            if "/" not in path and "." not in pure.name and pure.name not in ("Dockerfile", "Makefile"):
                continue
            found.append({"line": number, "path": path, "symbol": symbol, "ref": path + "#" + symbol})
    return found


def md_files(root: Path, rel: str, skip_hidden: bool = False) -> list[Path]:
    top = root / rel
    if not top.is_dir():
        return []
    out: list[Path] = []
    for parent, dirs, names in os.walk(top, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(parent) / d).is_symlink()
                         and (not skip_hidden or not d.startswith(".")))
        for name in sorted(names):
            path = Path(parent) / name
            if name.endswith(".md") and path.is_file() and not path.is_symlink() and (not skip_hidden or not name.startswith(".")):
                out.append(path)
    return out


def ref_text(repo: Path, sha: str, path: str, cache: dict[tuple[str, str], str | None]) -> str | None:
    key = (sha, path)
    if key not in cache:
        proc = subprocess.run(["git", "show", sha + ":" + path], cwd=repo, text=True,
                              encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, check=False)
        cache[key] = proc.stdout if proc.returncode == 0 else None
    return cache[key]


def symbol_present(path: str, symbol: str, text: str) -> bool:
    parts = [part for part in symbol.split(".") if part]
    if path.endswith(".json"):
        try:
            value: object = json.loads(text)
            for part in parts:
                if isinstance(value, dict):
                    value = value[part]
                elif isinstance(value, list) and part.isdigit():
                    value = value[int(part)]
                else:
                    return False
            return True
        except (ValueError, KeyError, IndexError, TypeError):
            return False
    return all(re.search(r"(?<![\w$])" + re.escape(part) + r"(?![\w$])", text) for part in parts)


def format_issues(repo: Path, path: Path, text: str, meta: dict[str, str], refs: list[dict[str, object]]) -> list[dict[str, object]]:
    rel = path.relative_to(repo).as_posix()
    issues: list[dict[str, object]] = []

    def add(code: str, line: int | None = None) -> None:
        issues.append({"file": rel, "code": code, "line": line})

    if split_frontmatter(text)[0] is None:
        add("frontmatter_missing")
        return issues
    if not meta.get("name") or not meta.get("description"):
        add("identity_missing")
    for key in REQUIRED_META:
        if not meta.get(key):
            add("metadata_" + key + "_missing")
    if meta.get("checked") and not CHECKED_RE.fullmatch(meta["checked"]):
        add("checked_invalid")
    if rel.startswith("memory/") and not rel.startswith("memory/journal/") and word_count(split_frontmatter(text)[1]) > ENTRY_WARN_WORDS:
        add("entry_budget_exceeded")
    lines = content_lines(text)
    if rel.startswith("memory/") and not rel.startswith("memory/journal/") and not any("> **Когда читать:**" in line for _, line in lines):
        add("navigator_missing")
    for number, line in lines:
        if LINE_REF_RE.search(line):
            add("line_anchor", number)
    if rel == "memory/MEMORY.md":
        for match in re.finditer(r"memory/[\w./-]+\.md", split_frontmatter(text)[1]):
            target = match.group(0)
            if ".." not in PurePosixPath(target).parts and not (repo / target).is_file():
                add("dead_index_link")
    if not refs and meta.get("genre") not in ("index", "decision", "journal") and rel != "memory/epic-state.md":
        if any(CLAIM_RE.match(line) and not TABLE_SEP_RE.match(line) and not MARK_RE.search(line) for _, line in lines):
            add("unanchored_claims")
    return issues


def feature_summary(repo: Path) -> dict[str, object]:
    statuses: Counter[str] = Counter()
    done: list[str] = []
    for path in md_files(repo, "docs/features", skip_hidden=True):
        if path.name not in CANON_FEATURES:
            continue
        for _, line in content_lines(read_text(path)):
            match = FEATURE_STATUS_RE.match(line)
            if match:
                status = match.group(1).strip(" *")
                statuses[status] += 1
                if status.lower() == "done":
                    done.append(path.relative_to(repo).as_posix())
                break
    return {"status_counts": dict(sorted(statuses.items())), "done_artifacts": sorted(done)}


def overwrite_suspects(repo: Path, cache: dict[tuple[str, str], str | None]) -> list[dict[str, object]]:
    head = resolve_commit(repo, "HEAD")
    if not head:
        return []
    suspects: list[dict[str, object]] = []
    for rel in git("ls-files", "-z", "--", "memory", cwd=repo).split("\0"):
        if not rel.endswith(".md"):
            continue
        original = ref_text(repo, head, rel, cache)
        if original is None:
            continue
        path = repo / rel
        if not path.is_file():
            suspects.append({"file": rel, "reason": "vanished_from_disk", "head_words": word_count(original)})
            continue
        old_words, new_words = word_count(original), word_count(read_text(path))
        if old_words >= 40 and new_words < old_words * 0.7:
            suspects.append({"file": rel, "reason": "disk_shrunk_vs_head", "head_words": old_words, "disk_words": new_words})
    return suspects


def scan(repo: Path, ref: str | None) -> dict[str, object]:
    mem_paths = md_files(repo, "memory")
    if not mem_paths:
        return {"schema": SCHEMA, "scan_complete": True, "errors": [],
                "memory": {"present": False, "file_count": 0, "words": {"entry": 0, "journal": 0, "other": 0}, "total_words": 0},
                "base": {"ref": ref, "sha": resolve_commit(repo, ref) if ref else None,
                         "remote_freshness_verified": False},
                "delta": {"files": [], "stale_file_count": 0, "stale_file_claims_total": 0,
                          "base_choice_required": False, "sample": []},
                "validation": {"issues": [], "issue_count": 0, "entry_over_budget": []},
                "overwrite": {"suspects": []}, "features": feature_summary(repo)}
    base_ref = ref or git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", cwd=repo, check=False).strip()
    if not base_ref:
        return {"schema": SCHEMA, "scan_complete": False,
                "errors": [{"code": "base_required", "message": "No origin/HEAD; choose --base explicitly"}],
                "memory": {"present": bool(mem_paths)}}
    base_sha = resolve_commit(repo, base_ref)
    if not base_sha:
        return {"schema": SCHEMA, "scan_complete": False,
                "errors": [{"code": "base_unresolved", "message": "Base ref is not a local commit; fetch or choose --base"}],
                "memory": {"present": bool(mem_paths)}, "base": {"ref": base_ref, "sha": None}}
    text_cache: dict[tuple[str, str], str | None] = {}
    diff_cache: dict[str, set[str]] = {}
    issues: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    sample_pool: list[tuple[str, dict[str, object]]] = []
    words = {"entry": 0, "journal": 0, "other": 0}
    stale_claims = 0
    for path in mem_paths:
        rel = path.relative_to(repo).as_posix()
        text = read_text(path)
        _, body = split_frontmatter(text)
        meta = metadata(text)
        lines = content_lines(text)
        refs = anchors(lines)
        issues.extend(format_issues(repo, path, text, meta, refs))
        journal = rel.startswith("memory/journal/")
        if journal:
            words["journal"] += word_count(body)
        elif len(path.relative_to(repo / "memory").parts) == 1 and meta.get("status") != "archive":
            words["entry"] += word_count(body)
        else:
            words["other"] += word_count(body)
        if journal or meta.get("status") == "archive" or rel == "memory/epic-state.md":
            continue
        claim_lines = {n for n, line in lines if CLAIM_RE.match(line) and not TABLE_SEP_RE.match(line)}
        old_short = checked_sha(meta)
        old_full = resolve_commit(repo, old_short) if old_short else None
        sha_state = "none" if not old_short else ("unresolved" if not old_full else
                    ("ancestor" if git_ok("merge-base", "--is-ancestor", old_full, base_sha, cwd=repo) else "not_ancestor"))
        commits_behind: int | None = None
        changed: set[str] = set()
        if sha_state == "ancestor" and old_full:
            commits_behind = int(git("rev-list", "--count", old_full + ".." + base_sha, cwd=repo).strip())
            if old_full not in diff_cache:
                raw = git("diff", "--name-only", "-z", "--find-renames", old_full, base_sha, cwd=repo)
                diff_cache[old_full] = {p for p in raw.split("\0") if p}
            changed = diff_cache[old_full]
        stale_anchors: list[dict[str, object]] = []
        branch_only: list[dict[str, object]] = []
        for item in refs:
            anchor_path = str(item["path"])
            symbol = str(item["symbol"])
            base_text = ref_text(repo, base_sha, anchor_path, text_cache)
            state = "intact"
            if base_text is None:
                if (repo / anchor_path).exists() or ref_text(repo, "HEAD", anchor_path, text_cache) is not None:
                    state = "branch_only"
                else:
                    state = "deleted"
            elif not symbol_present(anchor_path, symbol, base_text):
                state = "symbol_missing"
            elif anchor_path in changed or any(p.startswith(anchor_path.rstrip("/") + "/") for p in changed):
                state = "modified"
            entry = {**item, "state": state}
            if state == "branch_only":
                branch_only.append(entry)
            elif state != "intact":
                stale_anchors.append(entry)
        reasons: list[str] = []
        if sha_state == "none":
            reasons.append("no_checked")
        elif sha_state == "unresolved":
            reasons.append("checked_unresolved")
        elif sha_state == "not_ancestor":
            reasons.append("checked_not_ancestor")
        if stale_anchors:
            reasons.append("anchor_changed")
        if branch_only:
            reasons.append("branch_only")
        if not refs and meta.get("genre") not in ("index", "decision") and any(
            n in claim_lines and not MARK_RE.search(line) for n, line in lines
        ):
            reasons.append("unanchored_claims")
        stale = bool(reasons)
        if stale:
            stale_claims += len(claim_lines)
        else:
            for n, line in lines:
                if n in claim_lines and len(line.strip()) >= 20:
                    key = hashlib.sha256(f"{base_sha}:{rel}:{n}".encode()).hexdigest()
                    sample_pool.append((key, {"file": rel, "line": n, "text": line.strip()[:300]}))
        results.append({
            "file": rel, "checked": meta.get("checked"), "checked_sha": old_full,
            "sha_state": sha_state, "commits_behind": commits_behind, "claims": len(claim_lines),
            "stale": stale, "reasons": reasons, "stale_anchors": stale_anchors,
            "branch_only_anchors": branch_only,
        })
    results.sort(key=lambda item: str(item["file"]))
    for item in results:
        if item["sha_state"] == "not_ancestor":
            issues.append({"file": item["file"], "code": "checked_not_ancestor", "line": None})
    if words["entry"] and words["journal"] > words["entry"]:
        issues.append({"file": "memory/journal/", "code": "journal_budget_exceeded", "line": None})
    return {
        "schema": SCHEMA, "scan_complete": True, "errors": [],
        "base": {"ref": base_ref, "sha": base_sha, "source": "argument" if ref else "origin_head",
                 "remote_freshness_verified": False},
        "memory": {"present": bool(mem_paths), "file_count": len(mem_paths), "words": words,
                   "total_words": sum(words.values())},
        "delta": {"files": results, "stale_file_count": sum(bool(r["stale"]) for r in results),
                  "stale_file_claims_total": stale_claims,
                  "base_choice_required": any(r["sha_state"] in ("not_ancestor", "unresolved") for r in results),
                  "sample": [item for _, item in sorted(sample_pool)[:30]]},
        "validation": {"issues": issues, "issue_count": len(issues),
                       "entry_over_budget": [i["file"] for i in issues if i["code"] == "entry_budget_exceeded"]},
        "overwrite": {"suspects": overwrite_suspects(repo, text_cache)},
        "features": feature_summary(repo),
        "foreign_stores": {"policy": "report_only", "paths": [".codex/", "AGENTS.md"]},
    }


def snapshot_dir(repo: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    suffix = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    return codex_home / "qtim-kb-snapshots" / (repo.name + "-" + suffix)


def ensure_run(run: str) -> None:
    if not RUN_RE.fullmatch(run):
        raise ScanError("bad_run", "Run id must be 1-64 alphanumeric, underscore, or hyphen characters")


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lock_data(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(read_text(path))
        return value if isinstance(value, dict) else {"invalid": True}
    except (OSError, ValueError):
        return {"invalid": True}


def copy_knowledge(repo: Path, dest: Path) -> None:
    stage = dest.with_name(dest.name + ".partial")
    if stage.exists() or dest.exists():
        raise ScanError("snapshot_exists", "Snapshot destination already exists; use --resume for the same run")
    stage.mkdir(parents=True)
    try:
        for rel in ("memory", "docs/features"):
            src = repo / rel
            if src.is_dir():
                target = stage / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, target, symlinks=True)
        stage.rename(dest)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def snapshot(repo: Path, args: argparse.Namespace) -> dict[str, object]:
    ensure_run(args.run)
    if sum(bool(flag) for flag in (args.after, args.resume, args.abandon)) > 1:
        raise ScanError("bad_args", "Choose only one of --after, --resume, or --abandon")
    root = snapshot_dir(repo, args.snapshots_dir)
    run_dir = root / args.run
    marker = run_dir / "manifest.json"
    lock = root / "lock.json"
    if args.abandon:
        manifest = json.loads(read_text(marker)) if marker.is_file() else None
        holder = lock_data(lock)
        if not holder or holder.get("run") != args.run or holder.get("repo") != str(repo):
            raise ScanError("lock_mismatch", "Cannot abandon a run held by another lock")
        if manifest is not None:
            if not isinstance(manifest, dict) or manifest.get("repo") != str(repo):
                raise ScanError("run_foreign", "Run manifest belongs to another repository")
            manifest["abandoned_at"] = datetime.now(timezone.utc).isoformat()
            write_json(marker, manifest)
        lock.unlink()
        return {"schema": SCHEMA, "state": "abandoned", "run": args.run, "path": str(run_dir),
                "before": str(run_dir / "before") if (run_dir / "before").is_dir() else None}
    if args.after:
        manifest = json.loads(read_text(marker)) if marker.is_file() else None
        if not isinstance(manifest, dict) or manifest.get("repo") != str(repo):
            raise ScanError("run_unknown", "Run manifest is absent or belongs to another repository")
        holder = lock_data(lock)
        if not holder or holder.get("run") != args.run or holder.get("repo") != str(repo):
            raise ScanError("lock_mismatch", "Run lock is absent or held by a different run")
        after = run_dir / "after"
        if after.is_dir():
            if tree_fingerprints(after) != tree_fingerprints(repo):
                raise ScanError("after_mismatch", "Existing after snapshot differs from disk; inspect before completing")
        else:
            copy_knowledge(repo, after)
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_json(marker, manifest)
        lock.unlink()
        return {"schema": SCHEMA, "state": "complete", "run": args.run, "path": str(run_dir),
                "before": str(run_dir / "before"), "after": str(run_dir / "after")}
    if args.resume:
        manifest = json.loads(read_text(marker)) if marker.is_file() else None
        if not isinstance(manifest, dict) or manifest.get("repo") != str(repo) or not (run_dir / "before").is_dir():
            raise ScanError("run_unknown", "Cannot resume: matching run and before snapshot are required")
        if manifest.get("completed_at") or manifest.get("abandoned_at"):
            raise ScanError("run_closed", "A closed run cannot be resumed; start a new run")
        holder = lock_data(lock)
        if holder and (holder.get("run") != args.run or holder.get("repo") != str(repo)):
            raise ScanError("locked", "A different knowledge refresh holds the lock")
        if not holder:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"run": args.run, "repo": str(repo), "started_at": manifest.get("started_at")}, stream)
        return {"schema": SCHEMA, "state": "resumed", "run": args.run, "path": str(run_dir),
                "before": str(run_dir / "before"), "base_sha": manifest.get("base_sha")}
    if not args.base:
        raise ScanError("base_required", "Snapshot requires --base")
    base_sha = resolve_commit(repo, args.base)
    if not base_sha:
        raise ScanError("base_unresolved", "Snapshot base does not resolve to a commit")
    root.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        raise ScanError("locked", "Another or interrupted knowledge refresh holds the lock; inspect it or use --resume")
    if run_dir.exists():
        raise ScanError("run_exists", "Run id already exists; choose another or use --resume")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"run": args.run, "repo": str(repo), "started_at": datetime.now(timezone.utc).isoformat()}, stream)
        run_dir.mkdir(mode=0o700)
        manifest = {
            "schema": SCHEMA, "repo": str(repo), "run": args.run,
            "base_ref": args.base, "base_sha": base_sha,
            "branch": git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=repo, check=False).strip() or None,
            "head_sha": resolve_commit(repo, "HEAD"),
            "started_at": datetime.now(timezone.utc).isoformat(), "completed_at": None,
        }
        write_json(marker, manifest)
        copy_knowledge(repo, run_dir / "before")
    except Exception:
        lock.unlink(missing_ok=True)
        raise
    return {"schema": SCHEMA, "state": "started", "run": args.run, "path": str(run_dir),
            "before": str(run_dir / "before"), "base_sha": base_sha}


def before_snapshot(repo: Path, supplied: str) -> tuple[Path, dict[str, object]]:
    path = Path(supplied).expanduser().resolve()
    run_dir = path.parent if path.name == "before" else path
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file() or not (run_dir / "before").is_dir():
        raise ScanError("snapshot_invalid", "Pass a run directory or its before directory")
    manifest = json.loads(read_text(manifest_path))
    if manifest.get("repo") != str(repo):
        raise ScanError("snapshot_foreign", "Snapshot belongs to another repository")
    return run_dir / "before", manifest


def knowledge_texts(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in md_files(root, "memory") + md_files(root, "docs/features", skip_hidden=True):
        found[path.relative_to(root).as_posix()] = read_text(path)
    return found


def tree_fingerprints(root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rel in ("memory", "docs/features"):
        top = root / rel
        if not top.is_dir():
            continue
        for parent, dirs, names in os.walk(top, followlinks=False):
            for name in dirs:
                path = Path(parent) / name
                if path.is_symlink():
                    fingerprints[path.relative_to(root).as_posix()] = "link:" + os.readlink(path)
            dirs[:] = sorted(d for d in dirs if not (Path(parent) / d).is_symlink())
            for name in sorted(names):
                path = Path(parent) / name
                key = path.relative_to(root).as_posix()
                if path.is_symlink():
                    fingerprints[key] = "link:" + os.readlink(path)
                elif path.is_file():
                    fingerprints[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprints


def text_units(text: str) -> list[str]:
    _, body = split_frontmatter(text)
    out: list[str] = []
    current: list[str] = []
    fence = False

    def flush() -> None:
        if current:
            out.append("\n".join(current))
            current.clear()

    for line in body.splitlines():
        if re.match(r"^\s*(\x60\x60\x60|~~~)", line):
            if not fence:
                flush()
            current.append(line)
            fence = not fence
            if not fence:
                flush()
        elif fence:
            current.append(line)
        elif not line.strip():
            flush()
        elif line.startswith("#") or line.lstrip().startswith("|") or re.match(r"^\s*[-*+]\s+", line):
            flush()
            current.append(line)
            flush()
        else:
            current.append(line)
    flush()
    return out


def normalized_unit(text: str) -> str:
    text = re.sub(r"^\s*(?:[-*+>]\s+|\d+[.)]\s+)", "", text)
    return re.sub(r"\s+", " ", text.replace("**", "").replace(chr(96), "")).strip().casefold()


def knowledge_counts(texts: dict[str, str]) -> dict[str, int]:
    result = {"entry_words": 0, "journal_words": 0, "other_words": 0, "bytes": 0}
    for rel, text in texts.items():
        result["bytes"] += len(text.encode("utf-8"))
        words = word_count(split_frontmatter(text)[1])
        if rel.startswith("memory/journal/"):
            result["journal_words"] += words
        elif rel.startswith("memory/") and len(PurePosixPath(rel).parts) == 2:
            result["entry_words"] += words
        else:
            result["other_words"] += words
    return result


def lost(repo: Path, supplied: str) -> dict[str, object]:
    before, manifest = before_snapshot(repo, supplied)
    old = knowledge_texts(before)
    current = knowledge_texts(repo)
    old_units = [(rel, unit) for rel, text in old.items() for unit in text_units(text)]
    current_all: set[str] = set()
    current_active: set[str] = set()
    for rel, text in current.items():
        for unit in text_units(text):
            norm = normalized_unit(unit)
            current_all.add(norm)
            if not rel.startswith("memory/journal/"):
                current_active.add(norm)
    open_lost: list[dict[str, str]] = []
    candidates: list[dict[str, str]] = []
    for rel, unit in old_units:
        norm = normalized_unit(unit)
        if len(norm) < 25:
            continue
        if OPEN_RE.search(unit):
            if norm not in current_active:
                open_lost.append({"file": rel, "text": unit[:600]})
        elif norm not in current_all:
            candidates.append({"file": rel, "text": unit[:600]})
    before_counts = knowledge_counts(old)
    after_counts = knowledge_counts(current)
    old_words = sum(v for k, v in before_counts.items() if k.endswith("_words"))
    new_words = sum(v for k, v in after_counts.items() if k.endswith("_words"))
    shrunk: list[dict[str, object]] = []
    for rel, text in old.items():
        if rel not in current:
            shrunk.append({"file": rel, "reason": "deleted"})
        else:
            old_n = word_count(split_frontmatter(text)[1])
            new_n = word_count(split_frontmatter(current[rel])[1])
            if old_n >= 40 and new_n < old_n * 0.5:
                shrunk.append({"file": rel, "reason": "shrunk", "before_words": old_n, "after_words": new_n})
    return {
        "schema": SCHEMA, "run": manifest["run"], "before": before_counts, "after": after_counts,
        "growth_pct": round(100 * (new_words - old_words) / old_words, 1) if old_words else None,
        "open_lost": open_lost, "candidates": candidates, "shrunk_files": shrunk,
        "shrink_alarm": bool(shrunk) or (bool(old_words) and new_words < old_words * 0.7),
        "files_added": sorted(set(current) - set(old)), "files_removed": sorted(set(old) - set(current)),
    }


def stamp(repo: Path, args: argparse.Namespace) -> dict[str, object]:
    if not args.verified:
        raise ScanError("verification_required", "Use --verified only after every claim in each file was checked against the selected base")
    _, manifest = before_snapshot(repo, args.snapshot)
    base_sha = resolve_commit(repo, args.base)
    if not base_sha or manifest.get("base_sha") != base_sha:
        raise ScanError("base_mismatch", "Stamp base must equal the snapshot base SHA")
    supplied = Path(args.snapshot).expanduser().resolve()
    run_dir = supplied.parent if supplied.name == "before" else supplied
    lock = run_dir.parent / "lock.json"
    if args.snapshots_dir and snapshot_dir(repo, args.snapshots_dir) != run_dir.parent:
        raise ScanError("snapshot_root_mismatch", "--snapshots-dir does not match the supplied snapshot")
    holder = lock_data(lock)
    if not holder or holder.get("run") != manifest.get("run") or holder.get("repo") != str(repo):
        raise ScanError("lock_mismatch", "Resume the run before stamping; another run may own the knowledge base")
    stamped: list[str] = []
    skipped: list[dict[str, str]] = []
    cache: dict[tuple[str, str], str | None] = {}
    for raw in args.files:
        rel = PurePosixPath(raw.removeprefix("./"))
        if rel.parts[:1] != ("memory",) or len(rel.parts) != 2 or rel.suffix != ".md" or ".." in rel.parts or rel.name == "epic-state.md":
            skipped.append({"file": raw, "reason": "not_entry_memory"})
            continue
        path = repo / rel
        if not path.is_file() or path.is_symlink():
            skipped.append({"file": raw, "reason": "missing_or_symlink"})
            continue
        text = read_text(path)
        fm = FM_RE.match(text)
        if fm is None:
            skipped.append({"file": raw, "reason": "frontmatter_missing"})
            continue
        meta = metadata(text)
        old = checked_sha(meta)
        old_full = resolve_commit(repo, old) if old else None
        if old and not old_full:
            skipped.append({"file": raw, "reason": "checked_unresolved"})
            continue
        if old_full and not git_ok("merge-base", "--is-ancestor", old_full, base_sha, cwd=repo) and not args.allow_nonancestor:
            skipped.append({"file": raw, "reason": "checked_not_ancestor"})
            continue
        invalid: list[str] = []
        for anchor in anchors(content_lines(text)):
            path_in_ref = str(anchor["path"])
            source = ref_text(repo, base_sha, path_in_ref, cache)
            if source is None or not symbol_present(path_in_ref, str(anchor["symbol"]), source):
                invalid.append(str(anchor["ref"]))
        if invalid:
            skipped.append({"file": raw, "reason": "anchors_unverified", "anchors": ", ".join(invalid[:10])})
            continue
        lines = fm.group(1).splitlines()
        if not any(re.match(r"^\s*checked:", line) for line in lines):
            skipped.append({"file": raw, "reason": "checked_key_missing"})
            continue
        checked = f"{date.today().isoformat()} @ {base_sha[:12]}"
        for index, line in enumerate(lines):
            match = re.match(r"^(\s*)(checked|updated):", line)
            if match:
                lines[index] = f"{match.group(1)}{match.group(2)}: {checked if match.group(2) == 'checked' else date.today().isoformat()}"
        changed = text[:fm.start(1)] + "\n".join(lines) + text[fm.end(1):]
        if changed != text:
            fd, temp = tempfile.mkstemp(prefix=".kb-stamp-", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(changed)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
        stamped.append(rel.as_posix())
    return {"schema": SCHEMA, "base_sha": base_sha, "stamped": stamped, "skipped": skipped}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan_p = sub.add_parser("scan", help="Read-only format, freshness, feature, and overwrite scan")
    scan_p.add_argument("--base", help="Local ref or SHA; defaults to origin/HEAD")
    snap_p = sub.add_parser("snapshot", help="Create or close a durable knowledge-base snapshot")
    snap_p.add_argument("--run", required=True)
    snap_p.add_argument("--base", help="Ref or SHA for a new run")
    snap_p.add_argument("--snapshots-dir", help="Override default durable snapshot directory")
    snap_p.add_argument("--resume", action="store_true", help="Use existing before snapshot without replacing it")
    snap_p.add_argument("--after", action="store_true", help="Copy final state and release run lock")
    snap_p.add_argument("--abandon", action="store_true", help="Release lock but preserve incomplete snapshot for inspection")
    lost_p = sub.add_parser("lost", help="Read-only comparison with a before snapshot")
    lost_p.add_argument("--snapshot", required=True)
    stamp_p = sub.add_parser("stamp", help="Stamp checked after explicit full-file verification")
    stamp_p.add_argument("--base", required=True)
    stamp_p.add_argument("--snapshot", required=True)
    stamp_p.add_argument("--snapshots-dir", help="Override default durable snapshot directory")
    stamp_p.add_argument("--files", nargs="+", required=True)
    stamp_p.add_argument("--verified", action="store_true")
    stamp_p.add_argument("--allow-nonancestor", action="store_true",
                         help="Allow stamping after explicitly reconciling memory from another branch")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        repo = repo_root()
        if args.command == "scan":
            result = scan(repo, args.base)
        elif args.command == "snapshot":
            result = snapshot(repo, args)
        elif args.command == "lost":
            result = lost(repo, args.snapshot)
        else:
            result = stamp(repo, args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("scan_complete", True) else 2
    except (ScanError, OSError, ValueError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, ScanError) else "io_or_data_error"
        print(json.dumps({"schema": SCHEMA, "scan_complete": False,
                          "errors": [{"code": code, "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
