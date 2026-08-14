from typing import Any


def parse(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[dict[str, Any]] = [root]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("{"):
            key = line[:-1].strip().rstrip(":").strip()
            child: dict[str, Any] = {}
            _add(stack[-1], key, child)
            stack.append(child)
        elif line == "}":
            stack.pop()
        elif ":" in line:
            key, _, value = line.partition(":")
            _add(stack[-1], key.strip(), _parse_value(value.strip()))
    if len(stack) != 1:
        raise ValueError("unbalanced braces in METADATA.pb")
    return root


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _add(target: dict[str, Any], key: str, value: Any) -> None:
    if key in target:
        if not isinstance(target[key], list):
            target[key] = [target[key]]
        target[key].append(value)
    else:
        target[key] = value


def _parse_value(token: str) -> Any:
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        inner = token[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n")
    if token in ("true", "false"):
        return token == "true"
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token
