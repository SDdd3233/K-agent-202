import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "setup_academic_mcp.py"
SPEC = importlib.util.spec_from_file_location("setup_academic_mcp", MODULE_PATH)
setup_academic_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_academic_mcp)


class ConfigDetectionTests(unittest.TestCase):
    def test_detects_exact_server_name_in_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / ".mcp.json"
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "academic-search": {
                                "command": "custom-python",
                                "args": ["custom_server.py"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = setup_academic_mcp.detect_in_config_files([config])

        self.assertEqual(result.status, "existing")
        self.assertEqual(result.name, "academic-search")
        self.assertEqual(result.source, str(config))

    def test_detects_server_signature_under_an_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / ".mcp.json"
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "existing-literature": {
                                "command": "uv",
                                "args": ["run", "D:/tools/academic_search_server.py"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = setup_academic_mcp.detect_in_config_files([config])

        self.assertEqual(result.status, "existing")
        self.assertEqual(result.name, "existing-literature")

    def test_detects_nested_claude_project_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / ".claude.json"
            config.write_text(
                json.dumps(
                    {
                        "projects": {
                            "D:/engineering": {
                                "mcpServers": {
                                    "academic-search": {
                                        "command": "custom-python",
                                        "args": ["custom_server.py"],
                                    }
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = setup_academic_mcp.detect_in_config_files([config])

        self.assertEqual(result.status, "existing")
        self.assertEqual(result.name, "academic-search")

    def test_detects_server_signature_in_codex_toml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        "[mcp_servers.existing-literature]",
                        'command = "uv"',
                        'args = ["run", "D:/tools/academic_search_server.py"]',
                    ]
                ),
                encoding="utf-8",
            )

            result = setup_academic_mcp.detect_in_config_files([config])

        self.assertEqual(result.status, "existing")
        self.assertEqual(result.name, "existing-literature")

    def test_returns_absent_for_unrelated_or_missing_configs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / ".mcp.json"
            config.write_text(
                json.dumps({"mcpServers": {"other": {"command": "other"}}}),
                encoding="utf-8",
            )

            result = setup_academic_mcp.detect_in_config_files(
                [config, Path(temp_dir) / "missing.json"]
            )

        self.assertEqual(result.status, "absent")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.server_dir = Path("D:/K Agent/vendor/academic-search-mcp")

    def test_builds_codex_add_command(self):
        command = setup_academic_mcp.build_add_command(
            "codex", "codex", self.server_dir
        )

        self.assertEqual(command[:5], ["codex", "mcp", "add", "academic-search", "--"])
        self.assertEqual(command[-2:], ["python", "academic_search_server.py"])
        self.assertIn(str(self.server_dir), command)
        self.assertIn(str(self.server_dir / "requirements.txt"), command)

    def test_builds_claude_add_command(self):
        command = setup_academic_mcp.build_add_command(
            "claude", "claude", self.server_dir
        )

        self.assertEqual(
            command[:9],
            [
                "claude",
                "mcp",
                "add",
                "--scope",
                "user",
                "--transport",
                "stdio",
                "academic-search",
                "--",
            ],
        )
        self.assertEqual(command[-2:], ["python", "academic_search_server.py"])


class EnsureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.server_dir = Path(self.temp_dir.name) / "academic-search-mcp"
        self.server_dir.mkdir()
        (self.server_dir / "academic_search_server.py").write_text("", encoding="utf-8")
        (self.server_dir / "requirements.txt").write_text("mcp>=1\n", encoding="utf-8")

    def test_existing_cli_registration_is_reused_without_add(self):
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                ["codex", "mcp", "get"], 0, stdout="{}", stderr=""
            )
        )

        result = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(result.action, "reused")
        self.assertEqual(runner.call_count, 1)

    def test_absent_registration_is_added_once(self):
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess([], 1, stdout="", stderr="not found"),
                subprocess.CompletedProcess([], 0, stdout="No MCP servers", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="Added", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="{}", stderr=""),
            ]
        )

        result = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(result.action, "registered")
        self.assertEqual(runner.call_count, 4)
        add_command = next(
            call.args[0]
            for call in runner.call_args_list
            if call.args[0][:4] == ["codex", "mcp", "add", "academic-search"]
        )
        self.assertEqual(add_command[:4], ["codex", "mcp", "add", "academic-search"])

    def test_unknown_cli_state_fails_closed(self):
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess([], 1, stdout="", stderr="connection error"),
                subprocess.CompletedProcess([], 1, stdout="", stderr="config unreadable"),
            ]
        )

        result = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(result.action, "unchanged")
        self.assertEqual(result.status, "unknown")
        self.assertEqual(runner.call_count, 2)

    def test_existing_config_is_preserved_byte_for_byte(self):
        config = Path(self.temp_dir.name) / ".mcp.json"
        original = b'{\n  "mcpServers": {"academic-search": {"command": "custom"}}\n}\n'
        config.write_bytes(original)
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess([], 1, stdout="", stderr="not found"),
                subprocess.CompletedProcess([], 0, stdout="No MCP servers", stderr=""),
            ]
        )

        result = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[config],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(result.action, "reused")
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(runner.call_count, 2)

    def test_repeated_setup_registers_only_once(self):
        state = {"registered": False, "add_count": 0}

        def runner(command, **_kwargs):
            if command[1:4] == ["mcp", "get", "academic-search"]:
                return subprocess.CompletedProcess(
                    command,
                    0 if state["registered"] else 1,
                    stdout="{}" if state["registered"] else "",
                    stderr="" if state["registered"] else "not found",
                )
            if command[1:3] == ["mcp", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout="No MCP servers", stderr="")
            if command[1:4] == ["mcp", "add", "academic-search"]:
                state["registered"] = True
                state["add_count"] += 1
                return subprocess.CompletedProcess(command, 0, stdout="Added", stderr="")
            raise AssertionError("Unexpected command: {}".format(command))

        first = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )
        second = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(first.action, "registered")
        self.assertEqual(second.action, "reused")
        self.assertEqual(state["add_count"], 1)

    def test_registration_fails_if_post_registration_verification_is_missing(self):
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess([], 1, stdout="", stderr="not found"),
                subprocess.CompletedProcess([], 0, stdout="No MCP servers", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="Added", stderr=""),
                subprocess.CompletedProcess([], 1, stdout="", stderr="not visible"),
                subprocess.CompletedProcess([], 0, stdout="No MCP servers", stderr=""),
            ]
        )

        result = setup_academic_mcp.ensure_mcp(
            client="codex",
            server_dir=self.server_dir,
            executable="codex",
            config_paths=[],
            runner=runner,
            uv_executable="uv",
        )

        self.assertEqual(result.action, "unchanged")
        self.assertEqual(result.status, "error")
        self.assertEqual(runner.call_count, 5)


if __name__ == "__main__":
    unittest.main()
