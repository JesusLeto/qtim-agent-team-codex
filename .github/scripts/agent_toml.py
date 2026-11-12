"""Read agent TOML, with a conservative canonical-template fallback."""
import ast
import re

try:
    import tomllib
except ImportError:
    tomllib = None


def load_agent_toml(text):
    if tomllib is not None:
        return tomllib.loads(text)

    # shortcut: Python <3.11 accepts only qtim's flat template; use tomllib for other TOML.
    text = text.replace("\r\n", "\n")
    if re.search(r"[\x00-\x08\x0b-\x1f\x7f]", text):
        raise ValueError("TOML contains a forbidden control character")
    parts = text.split("'''")
    if len(parts) != 3:
        raise ValueError("Python <3.11 requires one terminal literal instructions block")
    header, instructions, tail = parts
    boundary = re.search(r"^developer_instructions[ \t]*=[ \t]*$", header, re.MULTILINE)
    if not boundary or boundary.end() != len(header):
        raise ValueError("Python <3.11 requires instructions after all top-level fields")
    if any(line.strip(" \t") and not line.lstrip(" \t").startswith("#") for line in tail.split("\n")):
        raise ValueError("Python <3.11 cannot validate fields after instructions")

    scalar = r'''(?:"[^"\\\r\n]*"|'[^'\\\r\n]*')'''
    value = rf"(?:{scalar}|\[[ \t]*(?:{scalar}(?:[ \t]*,[ \t]*{scalar})*)?[ \t]*\])"
    assignment = re.compile(rf"([A-Za-z0-9_]+)[ \t]*=[ \t]*({value})[ \t]*(?:#.*)?")
    payload = {}
    for line in header[:boundary.start()].split("\n"):
        line = line.strip(" \t")
        if not line or line.startswith("#"):
            continue
        match = assignment.fullmatch(line)
        if not match or match[1] in payload or match[1] == "developer_instructions":
            raise ValueError("Python <3.11 requires unique flat string fields or string arrays")
        payload[match[1]] = ast.literal_eval(match[2])
    payload["developer_instructions"] = instructions
    return payload
