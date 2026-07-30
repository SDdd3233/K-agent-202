#!/usr/bin/env python3
"""Reuse an existing academic-search MCP or register K-Agent's fallback.

The setup is intentionally conservative: an existing server is never changed,
and an ambiguous CLI/config state never triggers a registration attempt.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SERVER_NAME = "academic-search"
SERVER_SCRIPT = "academic_search_server.py"


class Detection:
    def __init__(self, status, source, name=None, detail=""):
        self.status = status
        self.source = source
        self.name = name
        self.detail = detail


class EnsureResult:
    def __init__(self, status, action, source, detail=""):
        self.status = status
        self.action = action
        self.source = source
        self.detail = detail


def _entry_matches(name, value):
    if str(name).lower() == SERVER_NAME:
        return True
    try:
        serialized = json.dumps(value, ensure_ascii=True).lower()
    except (TypeError, ValueError):
        serialized = str(value).lower()
    return SERVER_SCRIPT in serialized


def _iter_mcp_containers(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("mcpServers", "mcp_servers") and isinstance(child, dict):
                yield child
            yield from _iter_mcp_containers(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mcp_containers(child)


def _detect_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return Detection("unknown", str(path), detail=str(exc))

    for servers in _iter_mcp_containers(data):
        for name, value in servers.items():
            if _entry_matches(name, value):
                return Detection("existing", str(path), str(name))
    return Detection("absent", str(path))


def _load_toml(path):
    try:
        import tomllib
    except ImportError:
        return None
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _detect_toml(path):
    try:
        data = _load_toml(path)
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        return Detection("unknown", str(path), detail=str(exc))

    if isinstance(data, dict):
        servers = data.get("mcp_servers", {})
        if isinstance(servers, dict):
            for name, value in servers.items():
                if _entry_matches(name, value):
                    return Detection("existing", str(path), str(name))

    section_pattern = re.compile(r"^\s*\[mcp_servers\.(?:\"([^\"]+)\"|([^\]]+))\]\s*$", re.MULTILINE)
    sections = list(section_pattern.finditer(text))
    for index, match in enumerate(sections):
        name = (match.group(1) or match.group(2) or "").strip()
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        block = text[match.end():end]
        if _entry_matches(name, block):
            return Detection("existing", str(path), name)

    if SERVER_SCRIPT in text.lower():
        return Detection("existing", str(path), detail="server command signature")
    return Detection("absent", str(path))


def detect_in_config_files(paths):
    found_existing = None
    found_unknown = None
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            continue
        if path.suffix.lower() == ".toml":
            result = _detect_toml(path)
        else:
            result = _detect_json(path)
        if result.status == "existing":
            found_existing = result
            break
        if result.status == "unknown" and found_unknown is None:
            found_unknown = result
    if found_existing is not None:
        return found_existing
    if found_unknown is not None:
        return found_unknown
    return Detection("absent", "configuration files")


def default_config_paths(client, home=None, environ=None, cwd=None):
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    cwd = Path.cwd() if cwd is None else Path(cwd)
    if client == "codex":
        codex_root = environ.get("CODEX_HOME")
        root = Path(codex_root).expanduser() if codex_root else home / ".codex"
        return [root / "config.toml"]
    if client == "claude":
        return [home / ".claude.json", home / ".claude" / ".mcp.json", cwd / ".mcp.json"]
    raise ValueError("Unsupported client: {}".format(client))


def _run(runner, command):
    try:
        return runner(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(command, 127, stdout="", stderr=str(exc))


def detect_via_cli(client, executable, runner=subprocess.run):
    if not executable:
        return Detection("unavailable", "{} CLI".format(client), detail="command not found")

    get_command = [executable, "mcp", "get", SERVER_NAME]
    if client == "codex":
        get_command.append("--json")
    result = _run(runner, get_command)
    if result.returncode == 0:
        return Detection("existing", "{} CLI".format(client), SERVER_NAME)

    list_result = _run(runner, [executable, "mcp", "list"])
    if list_result.returncode != 0:
        detail = (list_result.stderr or result.stderr or "MCP registry query failed").strip()
        return Detection("unknown", "{} CLI".format(client), detail=detail)

    listing = "{}\n{}".format(list_result.stdout or "", list_result.stderr or "").lower()
    if SERVER_NAME in listing or SERVER_SCRIPT in listing:
        return Detection("existing", "{} CLI list".format(client), SERVER_NAME)
    return Detection("absent", "{} CLI".format(client))


def build_server_command(server_dir, uv_executable="uv"):
    server_dir = Path(server_dir)
    return [
        uv_executable,
        "run",
        "--no-project",
        "--directory",
        str(server_dir),
        "--with-requirements",
        str(server_dir / "requirements.txt"),
        "python",
        SERVER_SCRIPT,
    ]


def build_add_command(client, executable, server_dir, uv_executable="uv"):
    runtime = build_server_command(server_dir, uv_executable=uv_executable)
    if client == "codex":
        return [executable, "mcp", "add", SERVER_NAME, "--"] + runtime
    if client == "claude":
        return [
            executable,
            "mcp",
            "add",
            "--scope",
            "user",
            "--transport",
            "stdio",
            SERVER_NAME,
            "--",
        ] + runtime
    raise ValueError("Unsupported client: {}".format(client))


def ensure_mcp(
    client,
    server_dir,
    executable=None,
    config_paths=None,
    runner=subprocess.run,
    uv_executable=None,
):
    if client not in ("codex", "claude"):
        raise ValueError("Unsupported client: {}".format(client))

    executable = executable or shutil.which(client)
    cli_detection = detect_via_cli(client, executable, runner=runner)
    paths = default_config_paths(client) if config_paths is None else config_paths
    config_detection = detect_in_config_files(paths)

    for detection in (cli_detection, config_detection):
        if detection.status == "existing":
            detail = "existing MCP '{}' preserved".format(detection.name or SERVER_NAME)
            return EnsureResult("existing", "reused", detection.source, detail)

    if cli_detection.status in ("unknown", "unavailable"):
        return EnsureResult(
            cli_detection.status,
            "unchanged",
            cli_detection.source,
            cli_detection.detail,
        )
    if config_detection.status == "unknown":
        return EnsureResult("unknown", "unchanged", config_detection.source, config_detection.detail)

    server_dir = Path(server_dir).expanduser().resolve()
    required = [server_dir / SERVER_SCRIPT, server_dir / "requirements.txt"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return EnsureResult(
            "invalid",
            "unchanged",
            str(server_dir),
            "missing fallback runtime files: {}".format(", ".join(missing)),
        )

    uv_executable = uv_executable or shutil.which("uv")
    if not uv_executable:
        return EnsureResult("unavailable", "unchanged", "uv", "uv command not found")

    add_command = build_add_command(client, executable, server_dir, uv_executable)
    add_result = _run(runner, add_command)
    if add_result.returncode != 0:
        detail = (add_result.stderr or add_result.stdout or "MCP registration failed").strip()
        return EnsureResult("error", "unchanged", "{} CLI".format(client), detail)
    return EnsureResult("configured", "registered", "{} CLI".format(client), SERVER_NAME)


def resolve_client(requested):
    if requested != "auto":
        return requested
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return "claude"
    if os.environ.get("CODEX_HOME"):
        return "codex"
    available = [name for name in ("codex", "claude") if shutil.which(name)]
    if len(available) == 1:
        return available[0]
    return None


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    ensure_parser = subparsers.add_parser("ensure", help="reuse or register academic-search MCP")
    ensure_parser.add_argument("--client", choices=("auto", "codex", "claude"), default="auto")
    ensure_parser.add_argument("--server-dir", required=True)
    ensure_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    client = resolve_client(args.client)
    if client is None:
        result = EnsureResult(
            "unknown",
            "unchanged",
            "client detection",
            "cannot choose host safely; pass --client codex or --client claude",
        )
    else:
        result = ensure_mcp(client=client, server_dir=args.server_dir)

    payload = {
        "status": result.status,
        "action": result.action,
        "source": result.source,
        "detail": result.detail,
    }
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        label = "OK" if result.action in ("reused", "registered") else "WARN"
        print("[{}] academic-search MCP: {} ({})".format(label, result.action, result.source))
        if result.detail:
            print("     {}".format(result.detail))
    return 0 if result.action in ("reused", "registered") else 2


if __name__ == "__main__":
    sys.exit(main())
