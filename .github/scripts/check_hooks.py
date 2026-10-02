#!/usr/bin/env python3
"""Validate qtim Codex hook schemas and event-specific output contracts."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

if os.name == "nt":
    # GitHub Actions may expose cp1252 even though hook output is UTF-8.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


ALLOWED_EVENTS = {
    "SessionStart",
    "SubagentStart",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
}
ROOT_KEYS = {"description", "hooks"}
GROUP_KEYS = {"matcher", "hooks"}
HANDLER_KEYS = {
    "type",
    "command",
    "commandWindows",
    "timeout",
    "statusMessage",
    "async",
}
FILES = {
    pathlib.Path("plugins/qtim/hooks/hooks.json"): {"SessionStart", "SubagentStop"},
    pathlib.Path("plugins/qtim/reference/project-hooks.json"): {"PostToolUse"},
}
EXPECTED_MATCHERS = {
    pathlib.Path("plugins/qtim/hooks/hooks.json"): {
        "SessionStart": ["startup|resume|clear|compact"],
        "SubagentStop": ["*", "^qtim-testing$"],
    },
    pathlib.Path("plugins/qtim/reference/project-hooks.json"): {
        "PostToolUse": ["Edit|Write|apply_patch"],
    },
}

bad = []
loaded = {}


def fail(path, message):
    bad.append(f"{path}: {message}")


for path, expected_events in FILES.items():
    if not path.is_file():
        fail(path, "файл отсутствует")
        continue

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        fail(path, f"невалидный JSON: {err}")
        continue

    loaded[path] = payload
    if not isinstance(payload, dict):
        fail(path, "корень должен быть JSON-объектом")
        continue

    unknown_root = sorted(set(payload) - ROOT_KEYS)
    if unknown_root:
        fail(path, f"неподдерживаемые top-level поля: {', '.join(unknown_root)}")

    description = payload.get("description")
    if description is not None and (
        not isinstance(description, str) or not description.strip()
    ):
        fail(path, "description должен быть непустой строкой")

    events = payload.get("hooks")
    if not isinstance(events, dict):
        fail(path, "обязательное поле hooks должно быть объектом")
        continue

    actual_events = set(events)
    if actual_events != expected_events:
        fail(
            path,
            "ожидались события "
            f"{sorted(expected_events)}, получены {sorted(actual_events)}",
        )

    for event, groups in events.items():
        if event not in ALLOWED_EVENTS:
            fail(path, f"неподдерживаемое событие {event}")
        if not isinstance(groups, list) or not groups:
            fail(path, f"{event} должен содержать непустой массив matcher groups")
            continue
        expected_group_count = len(EXPECTED_MATCHERS[path].get(event, []))
        if len(groups) != expected_group_count:
            fail(path, f"{event} должен содержать {expected_group_count} matcher group(s)")

        for group_index, group in enumerate(groups):
            location = f"{event}[{group_index}]"
            if not isinstance(group, dict):
                fail(path, f"{location} должен быть объектом")
                continue
            unknown_group = sorted(set(group) - GROUP_KEYS)
            if unknown_group:
                fail(
                    path,
                    f"{location}: неподдерживаемые поля: {', '.join(unknown_group)}",
                )

            matcher = group.get("matcher")
            if matcher is not None and not isinstance(matcher, str):
                fail(path, f"{location}.matcher должен быть строкой")
            expected_matchers = EXPECTED_MATCHERS[path].get(event, [])
            expected_matcher = (
                expected_matchers[group_index]
                if group_index < len(expected_matchers)
                else None
            )
            if matcher != expected_matcher:
                fail(
                    path,
                    f"{location}.matcher должен быть {expected_matcher!r}, "
                    f"получен {matcher!r}",
                )

            handlers = group.get("hooks")
            if not isinstance(handlers, list) or not handlers:
                fail(path, f"{location}.hooks должен быть непустым массивом")
                continue
            if len(handlers) != 1:
                fail(path, f"{location}.hooks должен содержать ровно один handler")

            for handler_index, handler in enumerate(handlers):
                handler_location = f"{location}.hooks[{handler_index}]"
                if not isinstance(handler, dict):
                    fail(path, f"{handler_location} должен быть объектом")
                    continue
                unknown_handler = sorted(set(handler) - HANDLER_KEYS)
                if unknown_handler:
                    fail(
                        path,
                        f"{handler_location}: неподдерживаемые поля: "
                        f"{', '.join(unknown_handler)}",
                    )
                if handler.get("type") != "command":
                    fail(path, f'{handler_location}.type должен быть "command"')
                command = handler.get("command")
                if not isinstance(command, str) or not command.strip():
                    fail(path, f"{handler_location}.command должен быть непустой строкой")
                elif ".claude/" in command:
                    fail(path, f"{handler_location}.command содержит Claude-only путь")

                command_windows = handler.get("commandWindows")
                if not isinstance(command_windows, str) or not command_windows.strip():
                    fail(
                        path,
                        f"{handler_location}.commandWindows обязателен для qtim hooks",
                    )

                timeout = handler.get("timeout")
                if timeout is not None and (
                    isinstance(timeout, bool)
                    or not isinstance(timeout, int)
                    or timeout <= 0
                ):
                    fail(
                        path,
                        f"{handler_location}.timeout должен быть целым числом > 0",
                    )

                if "async" in handler and handler["async"] is not False:
                    fail(
                        path,
                        f"{handler_location}.async должен отсутствовать или быть false",
                    )

                for key in ("statusMessage", "commandWindows"):
                    value = handler.get(key)
                    if value is not None and (
                        not isinstance(value, str) or not value.strip()
                    ):
                        fail(path, f"{handler_location}.{key} должен быть строкой")


bundled_path = pathlib.Path("plugins/qtim/hooks/hooks.json")
bundled = loaded.get(bundled_path, {}).get("hooks", {})
for event in ("SessionStart", "SubagentStop"):
    groups = bundled.get(event, [])
    for group in groups if isinstance(groups, list) else []:
        for handler in group.get("hooks", []) if isinstance(group, dict) else []:
            command = handler.get("command", "") if isinstance(handler, dict) else ""
            command_windows = (
                handler.get("commandWindows", "") if isinstance(handler, dict) else ""
            )
            screenshot_gate = event == "SubagentStop" and group.get("matcher") == "^qtim-testing$"
            windows_contract = command_windows
            for script_name in ("session-start.ps1", "subagent-stop.ps1"):
                if script_name in command_windows:
                    script_path = pathlib.Path("plugins/qtim/hooks") / script_name
                    if not script_path.is_file():
                        fail(bundled_path, f"commandWindows ссылается на отсутствующий {script_name}")
                    else:
                        windows_contract += "\n" + script_path.read_text(encoding="utf-8")
                    if "%PLUGIN_ROOT%" not in command_windows:
                        fail(bundled_path, f"{event}.commandWindows не использует %PLUGIN_ROOT%")
            if not screenshot_gate and "git rev-parse --show-toplevel" not in command:
                fail(bundled_path, f"{event} не резолвит charter от git root")
            if not screenshot_gate and (
                "git rev-parse --show-toplevel" not in windows_contract
                and not (
                    "Join-Path $root" in windows_contract
                    and '".git"' in windows_contract
                )
            ):
                fail(bundled_path, f"{event}.commandWindows не резолвит git root")
            if not screenshot_gate and "Test-Path -LiteralPath" not in windows_contract:
                fail(bundled_path, f"{event}.commandWindows не использует literal path")
            if not screenshot_gate and "-PathType Leaf" not in windows_contract:
                fail(
                    bundled_path,
                    f"{event}.commandWindows не проверяет charter как файл",
                )
            if not screenshot_gate and "OutputEncoding" not in windows_contract:
                fail(bundled_path, f"{event}.commandWindows не фиксирует UTF-8")
            if event == "SessionStart" and "Select-String -LiteralPath" not in windows_contract:
                fail(
                    bundled_path,
                    "SessionStart.commandWindows читает charter не через LiteralPath",
                )
            if event == "SessionStart":
                for marker in ("session-start.sh", "$PLUGIN_ROOT"):
                    if marker not in command:
                        fail(bundled_path, f"SessionStart command missing {marker}")
                session_script = pathlib.Path("plugins/qtim/hooks/session-start.sh")
                if not session_script.is_file():
                    fail(bundled_path, "SessionStart ссылается на отсутствующий session-start.sh")
            if event == "SubagentStop" and not screenshot_gate and '"systemMessage"' not in command:
                fail(
                    bundled_path,
                    "SubagentStop должен печатать JSON systemMessage, а не plain stdout",
                )
            if event == "SubagentStop" and not screenshot_gate and "systemMessage" not in windows_contract:
                fail(
                    bundled_path,
                    "SubagentStop.commandWindows должен печатать JSON systemMessage",
                )
            if screenshot_gate:
                for marker in ("screenshots-gate.sh", "$PLUGIN_ROOT"):
                    if marker not in command:
                        fail(bundled_path, f"screenshot gate command missing {marker}")
                for marker in ("screenshots-gate.ps1", "%PLUGIN_ROOT%"):
                    if marker not in command_windows:
                        fail(bundled_path, f"screenshot gate commandWindows missing {marker}")

project_path = pathlib.Path("plugins/qtim/reference/project-hooks.json")
project = loaded.get(project_path, {}).get("hooks", {})
groups = project.get("PostToolUse", []) if isinstance(project, dict) else []
for group in groups if isinstance(groups, list) else []:
    matcher = group.get("matcher") if isinstance(group, dict) else None
    if matcher != "Edit|Write|apply_patch":
        fail(project_path, "PostToolUse matcher должен быть Edit|Write|apply_patch")
    for handler in group.get("hooks", []) if isinstance(group, dict) else []:
        command = handler.get("command", "") if isinstance(handler, dict) else ""
        command_windows = (
            handler.get("commandWindows", "") if isinstance(handler, dict) else ""
        )
        for marker in (
            '"hookSpecificOutput"',
            '"hookEventName":"PostToolUse"',
            '"additionalContext"',
        ):
            if marker not in command:
                fail(
                    project_path,
                    f"PostToolUse command не содержит JSON marker {marker}",
                )
        for marker in ("hookSpecificOutput", "PostToolUse", "additionalContext"):
            if marker not in command_windows:
                fail(
                    project_path,
                    f"PostToolUse.commandWindows не содержит JSON marker {marker}",
                )
        if "OutputEncoding" not in command_windows:
            fail(project_path, "PostToolUse.commandWindows не фиксирует UTF-8")

setup_path = pathlib.Path("plugins/qtim/skills/qtim-setup/SKILL.md")
setup = setup_path.read_text(encoding="utf-8")
if "../../reference/project-hooks.json" not in setup:
    fail(setup_path, "setup не ссылается на канонический project hooks template")
for legacy in (
    "- hooks: SessionStart, SubagentStop, optional PostToolUse reminder after edits;",
    "- `SessionStart`: если есть `.codex/team-charter.md`",
    "- `SubagentStop`: напомнить main agent",
):
    if legacy in setup:
        fail(setup_path, f"setup всё ещё предлагает project-level дубль: {legacy}")


def first_command(payload, event):
    key = "commandWindows" if os.name == "nt" else "command"
    return payload["hooks"][event][0]["hooks"][0][key]


def command_at(payload, event, index):
    key = "commandWindows" if os.name == "nt" else "command"
    return payload["hooks"][event][index]["hooks"][0][key]


def run_command(command, cwd, payload):
    env = os.environ.copy()
    env["PLUGIN_ROOT"] = str(pathlib.Path.cwd() / "plugins" / "qtim")
    script_path = None
    if os.name == "nt":
        # Passing an inline `powershell -Command "$var=..."` directly as the
        # `cmd /c` argument lets Windows quoting eat `$var` before PowerShell.
        # A batch file matches how commandWindows is actually interpreted.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cmd",
            dir=cwd,
            delete=False,
            encoding="utf-8",
            newline="\r\n",
        ) as script:
            script.write("@echo off\nchcp 65001 >nul\n")
            script.write(command)
            script.write("\n")
            script_path = pathlib.Path(script.name)
        argv = ["cmd.exe", "/d", "/c", str(script_path)]
    else:
        argv = ["/bin/sh", "-c", command]
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Windows starts PowerShell for commandWindows on every invocation;
            # cold CI runners can exceed the previous five-second harness limit.
            timeout=15 if os.name == "nt" else 5,
            check=False,
            env=env,
        )
    finally:
        if script_path is not None:
            script_path.unlink(missing_ok=True)


if not bad:
    with tempfile.TemporaryDirectory(prefix="qtim-хуки-[literal]-") as temp_dir:
        root = pathlib.Path(temp_dir)
        init = subprocess.run(
            ["git", "init", "-q"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if init.returncode != 0:
            fail("runtime", f"не удалось создать temp git repo: {init.stderr!r}")
        nested = root / "nested" / "cwd"
        nested.mkdir(parents=True)

        session_payload = {
            "session_id": "session-test",
            "transcript_path": None,
            "cwd": str(nested),
            "hook_event_name": "SessionStart",
            "model": "test-model",
            "permission_mode": "default",
            "source": "startup",
        }
        subagent_payload = {
            "session_id": "session-test",
            "transcript_path": None,
            "cwd": str(nested),
            "hook_event_name": "SubagentStop",
            "model": "test-model",
            "permission_mode": "default",
            "turn_id": "turn-test",
            "agent_id": "agent-test",
            "agent_type": "reviewer",
            "agent_transcript_path": None,
            "stop_hook_active": False,
            "last_assistant_message": "Проверка завершена.",
        }

        commands = {
            "SessionStart": first_command(loaded[bundled_path], "SessionStart"),
            "SubagentStop": first_command(loaded[bundled_path], "SubagentStop"),
        }
        for event, payload in (
            ("SessionStart", session_payload),
            ("SubagentStop", subagent_payload),
        ):
            result = run_command(commands[event], nested, payload)
            if result.returncode != 0 or result.stdout or result.stderr:
                fail(
                    bundled_path,
                    f"{event} без charter должен завершаться 0 без вывода: "
                    f"rc={result.returncode}, stdout={result.stdout!r}, "
                    f"stderr={result.stderr!r}",
                )

        charter = root / ".codex" / "team-charter.md"
        charter.parent.mkdir()
        charter.write_text("<!-- qtim-version: 9.8.7 -->\n", encoding="utf-8")

        session = run_command(commands["SessionStart"], nested, session_payload)
        if session.returncode != 0 or session.stderr:
            fail(
                bundled_path,
                "SessionStart с charter завершился ошибкой: "
                f"rc={session.returncode}, stderr={session.stderr!r}",
            )
        elif "[qtim v9.8.7]" not in session.stdout.decode("utf-8"):
            fail(
                bundled_path,
                "SessionStart не прочитал version stamp от git root: "
                f"rc={session.returncode}, stdout={session.stdout!r}, stderr={session.stderr!r}",
            )

        mission_dir = root / "memory" / "missions" / "runtime-recovery"
        mission_dir.mkdir(parents=True)
        (mission_dir / "mission.md").write_text(
            "# Mission\nStatus: Running\n", encoding="utf-8"
        )
        unsafe_mission_dir = root / "memory" / "missions" / "unsafe slug"
        unsafe_mission_dir.mkdir(parents=True)
        (unsafe_mission_dir / "mission.md").write_text(
            "# Mission\nStatus: Running\n", encoding="utf-8"
        )
        session_advisory = run_command(
            commands["SessionStart"], nested, {**session_payload, "source": "resume"}
        )
        advisory_text = session_advisory.stdout.decode("utf-8")
        if (
            session_advisory.returncode != 0
            or session_advisory.stderr
            or "[qtim mission advisory]" not in advisory_text
            or "runtime-recovery:Running" not in advisory_text
            or "unsafe slug" in advisory_text
            or "Ничего не запущено" not in advisory_text
            or "$qtim-mission, resume <slug>" not in advisory_text
        ):
            fail(
                bundled_path,
                "SessionStart не вернул bounded passive mission advisory: "
                f"rc={session_advisory.returncode}, stdout={session_advisory.stdout!r}, "
                f"stderr={session_advisory.stderr!r}",
            )

        for git_args in (
            ("config", "user.name", "qtim hook fixture"),
            ("config", "user.email", "qtim-hooks@example.invalid"),
            ("add", ".codex/team-charter.md", "memory/missions/runtime-recovery/mission.md"),
            ("commit", "-q", "-m", "portable verifying fixture"),
        ):
            git_result = subprocess.run(
                ["git", *git_args],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if git_result.returncode != 0:
                fail(
                    bundled_path,
                    f"не удалось подготовить SessionStart state fixture: {git_result.stderr!r}",
                )
                break
        main_branch = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).stdout.strip()
        state_branch = "codex/qtim-mission-state-runtime-recovery"
        subprocess.run(
            ["git", "switch", "-q", "-c", state_branch],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        (mission_dir / "mission.md").write_text(
            "# Mission\nStatus: Done\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", "memory/missions/runtime-recovery/mission.md"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        state_commit = subprocess.run(
            ["git", "commit", "-q", "-m", "terminal state fixture"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        switch_back = subprocess.run(
            ["git", "switch", "-q", main_branch],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if state_commit.returncode != 0 or switch_back.returncode != 0:
            fail(bundled_path, "не удалось создать authoritative Done state ref")
        (mission_dir / "mission.md").write_text(
            "# Mission\nStatus: Verifying\n", encoding="utf-8"
        )
        session_done = run_command(commands["SessionStart"], nested, session_payload)
        if b"[qtim mission advisory]" in session_done.stdout:
            fail(
                bundled_path,
                "SessionStart не подавил portable Verifying при authoritative Done",
            )

        (mission_dir / "mission.md").write_text(
            "# Mission\nStatus: Done\n", encoding="utf-8"
        )
        for index in range(60):
            capped_dir = root / "memory" / "missions" / f"bounded-{index:02d}"
            capped_dir.mkdir()
            (capped_dir / "mission.md").write_text(
                "# Mission\nStatus: Running\n",
                encoding="utf-8",
            )
        bounded_session = run_command(
            commands["SessionStart"],
            nested,
            {**session_payload, "source": "resume"},
        )
        bounded_text = bounded_session.stdout.decode("utf-8")
        if (
            bounded_session.returncode != 0
            or bounded_session.stderr
            or "+more" not in bounded_text
            or len(bounded_text) > 2048
        ):
            fail(
                bundled_path,
                "SessionStart не ограничил scan/output при множестве missions: "
                f"rc={bounded_session.returncode}, stdout={bounded_session.stdout!r}, "
                f"stderr={bounded_session.stderr!r}",
            )

        subagent = run_command(commands["SubagentStop"], nested, subagent_payload)
        if subagent.returncode != 0 or subagent.stderr:
            fail(
                bundled_path,
                "SubagentStop с charter завершился ошибкой: "
                f"rc={subagent.returncode}, stderr={subagent.stderr!r}",
            )
        else:
            try:
                output = json.loads(subagent.stdout.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as err:
                fail(
                    bundled_path,
                    f"SubagentStop stdout не JSON UTF-8: {err}; "
                    f"rc={subagent.returncode}, stdout={subagent.stdout!r}, stderr={subagent.stderr!r}",
                )
            else:
                if set(output) != {"systemMessage"} or not output["systemMessage"]:
                    fail(
                        bundled_path,
                        "SubagentStop должен вернуть только непустой systemMessage",
                    )

        gate_command = command_at(loaded[bundled_path], "SubagentStop", 1)
        gate_no_config = run_command(gate_command, nested, {**subagent_payload, "agent_type": "qtim-testing"})
        if gate_no_config.returncode != 0 or gate_no_config.stdout or gate_no_config.stderr:
            fail(bundled_path, "screenshot gate без config должен быть тихим no-op")

        gate_config = root / ".codex" / "screenshots-gate.json"
        gate_config.write_text(
            json.dumps({"mode": "blocking", "directory": "artifacts/screenshots", "freshnessMinutes": 180}),
            encoding="utf-8",
        )
        gate_missing = run_command(gate_command, nested, {**subagent_payload, "agent_type": "qtim-testing"})
        if gate_missing.returncode != 2 or b"no fresh tester screenshots" not in gate_missing.stderr:
            fail(
                bundled_path,
                "screenshot gate должен один раз блокировать отсутствие evidence: "
                f"rc={gate_missing.returncode}, stdout={gate_missing.stdout!r}, stderr={gate_missing.stderr!r}",
            )
        gate_retry = run_command(
            gate_command,
            nested,
            {**subagent_payload, "agent_type": "qtim-testing", "stop_hook_active": True},
        )
        if gate_retry.returncode != 0:
            fail(bundled_path, "screenshot gate обязан пропускать повторный stop_hook_active")
        shots = root / "artifacts" / "screenshots"
        shots.mkdir(parents=True)
        (shots / "front-selfcheck-mobile.png").write_bytes(b"test")
        gate_selfcheck = run_command(gate_command, nested, {**subagent_payload, "agent_type": "qtim-testing"})
        if gate_selfcheck.returncode != 2:
            fail(
                bundled_path,
                "front-selfcheck-* не должен закрывать tester screenshot gate: "
                f"rc={gate_selfcheck.returncode}, stdout={gate_selfcheck.stdout!r}, stderr={gate_selfcheck.stderr!r}",
            )
        (shots / "epic-phase-mobile-screen.png").write_bytes(b"test")
        gate_fresh = run_command(gate_command, nested, {**subagent_payload, "agent_type": "qtim-testing"})
        if gate_fresh.returncode != 0:
            fail(bundled_path, "fresh tester screenshot должен закрывать gate")

        post_payload = {
            "session_id": "session-test",
            "transcript_path": None,
            "cwd": str(nested),
            "hook_event_name": "PostToolUse",
            "model": "test-model",
            "permission_mode": "default",
            "turn_id": "turn-test",
            "tool_name": "apply_patch",
            "tool_use_id": "tool-test",
            "tool_input": {"command": "*** Begin Patch\n*** End Patch"},
            "tool_response": {"output": "Done!"},
        }
        post = run_command(
            first_command(loaded[project_path], "PostToolUse"), nested, post_payload
        )
        if post.returncode != 0 or post.stderr:
            fail(
                project_path,
                "PostToolUse завершился ошибкой: "
                f"rc={post.returncode}, stderr={post.stderr!r}",
            )
        else:
            try:
                output = json.loads(post.stdout.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as err:
                fail(project_path, f"PostToolUse stdout не JSON UTF-8: {err}")
            else:
                specific = output.get("hookSpecificOutput", {})
                if (
                    specific.get("hookEventName") != "PostToolUse"
                    or not specific.get("additionalContext")
                    or set(output) != {"hookSpecificOutput"}
                ):
                    fail(
                        project_path,
                        "PostToolUse должен вернуть только валидный additionalContext",
                    )

if bad:
    print("Codex hooks validation failed:")
    print("\n".join(bad))
    sys.exit(1)

print("OK: bundled и project hooks соответствуют Codex schema/output contract")
