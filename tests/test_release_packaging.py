import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_release_metadata_is_consistent(self):
        plugin = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(plugin["name"], "lsdyna-kagent")
        self.assertEqual(plugin["version"], "0.3.3")
        self.assertIn("v0.3.3", (REPO_ROOT / "docs" / "release-v0.3.3.md").read_text(encoding="utf-8"))
        self.assertIn("v0.3.3", (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("v0.3.3", (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8"))

    def test_codex_and_claude_installers_are_one_click_entrypoints(self):
        codex_cmd = (REPO_ROOT / "install-codex.cmd").read_text(encoding="utf-8")
        codex_sh = (REPO_ROOT / "install-codex.sh").read_text(encoding="utf-8")
        claude_cmd = (REPO_ROOT / "install-claude.cmd").read_text(encoding="utf-8")
        claude_sh = (REPO_ROOT / "install-claude.sh").read_text(encoding="utf-8")

        for installer in (codex_cmd, codex_sh):
            self.assertIn("skills/lsdyna-kfile", installer.replace("\\", "/"))
            self.assertIn("academic-search", installer)

        for installer in (claude_cmd, claude_sh):
            self.assertIn("plugin marketplace add", installer)
            self.assertIn("plugin install", installer)
            self.assertIn("lsdyna-kagent@lsdyna-kagent-marketplace", installer)
            self.assertIn("academic-search", installer)


if __name__ == "__main__":
    unittest.main()
