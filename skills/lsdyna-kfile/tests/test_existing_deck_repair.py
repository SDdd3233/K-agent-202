import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare_existing_deck = load_module(
    "prepare_existing_deck",
    SKILL_DIR / "scripts" / "prepare_existing_deck.py",
)
run_dyna = load_module("run_dyna", SKILL_DIR / "scripts" / "run_dyna.py")


class ExistingDeckRepairTests(unittest.TestCase):
    def test_prepare_existing_deck_copies_recursive_includes_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "model.k"
            mesh_dir = root / "mesh"
            mesh_dir.mkdir()
            mesh = mesh_dir / "mesh.k"
            nested = mesh_dir / "nested.inc"
            main.write_text("*KEYWORD\n*INCLUDE\nmesh/mesh.k\n*END\n", encoding="ascii")
            mesh.write_text("$ mesh\n*INCLUDE\nnested.inc\n", encoding="ascii")
            nested.write_text("$ nested\n", encoding="ascii")

            result = prepare_existing_deck.prepare(main, root / "repair_model", "debug")

            workspace = Path(result["workspace"])
            self.assertTrue((workspace / "source" / "model.k").is_file())
            self.assertTrue((workspace / "working" / "mesh" / "mesh.k").is_file())
            self.assertTrue((workspace / "working" / "mesh" / "nested.inc").is_file())
            self.assertEqual(result["missing_includes"], [])

            manifest = json.loads((workspace / "deck-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "existing-deck-repair")
            self.assertEqual(manifest["objective"], "debug")
            self.assertEqual(len(manifest["include_graph"]), 3)

            main.write_text("changed original\n", encoding="ascii")
            self.assertIn("*KEYWORD", (workspace / "source" / "model.k").read_text(encoding="ascii"))

    def test_run_dyna_rundir_stages_includes_without_cleaning_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "model.k"
            mesh = root / "mesh.k"
            source_output = root / "glstat"
            main.write_text("*KEYWORD\n*INCLUDE\nmesh.k\n*END\n", encoding="ascii")
            mesh.write_text("$ mesh\n", encoding="ascii")
            source_output.write_text("do not delete\n", encoding="ascii")

            rundir = root / "iteration001"
            staged = run_dyna.stage_deck_for_rundir(main, rundir)
            removed = run_dyna.clean_rundir(rundir)

            self.assertEqual(staged, rundir / "model.k")
            self.assertTrue((rundir / "mesh.k").is_file())
            self.assertTrue(source_output.is_file())
            self.assertEqual(source_output.read_text(encoding="ascii"), "do not delete\n")
            self.assertEqual(removed, 0)

    def test_skill_and_agent_route_existing_decks(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        agent_path = Path(__file__).resolve().parents[3] / "agents" / "lsdyna-writer.md"

        self.assertIn("已有 deck 模式", skill_text)
        self.assertIn("prepare_existing_deck.py", skill_text)
        self.assertIn("跳过 §1 需求头脑风暴", skill_text)
        if agent_path.exists():
            agent_text = agent_path.read_text(encoding="utf-8")
            self.assertIn("不得直接修改用户原文件", agent_text)


if __name__ == "__main__":
    unittest.main()
