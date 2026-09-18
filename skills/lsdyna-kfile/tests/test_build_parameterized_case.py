import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parameter_contract = load_module("parameter_contract_for_case", SCRIPTS_DIR / "parameter_contract.py")
case_builder = load_module("build_parameterized_case", SCRIPTS_DIR / "build_parameterized_case.py")


def project_data():
    return {
        "schema_version": 1,
        "project_id": "case-test",
        "unit_system": "mm-ton-s",
        "baseline": {"root": "baseline", "main_deck": "model.k"},
        "parameters": [{
            "parameter_id": "initial_velocity", "name": "初始速度", "aliases": ["冲击速度"],
            "type": "number", "dimension": "velocity", "accepted_units": ["m/s"],
            "deck_multiplier": -1, "allowed_range": {"min": -20000, "max": 0},
            "required": True, "requires_confirmation": True,
        }],
        "keyword_mappings": [{
            "parameter_id": "initial_velocity", "target_file": "model.k",
            "keyword": "INITIAL_VELOCITY_GENERATION", "occurrence": 1,
            "data_line": 1, "field": 5, "format": "csv", "expected": -1000,
            "value_format": ".9g",
        }],
    }


class BuildParameterizedCaseTests(unittest.TestCase):
    def make_fixture(self, root):
        baseline = root / "baseline"
        baseline.mkdir()
        deck = baseline / "model.k"
        deck.write_text(
            "*KEYWORD\n*INITIAL_VELOCITY_GENERATION\n1,2,0,0,-1000,0\n*END\n",
            encoding="ascii",
        )
        project = root / "project.json"
        project.write_text(json.dumps(project_data(), ensure_ascii=False), encoding="utf-8")
        extracted = parameter_contract.extract_text(project_data(), "初始速度为 8 m/s")
        confirmed = parameter_contract.confirm_extraction(project_data(), extracted, "reviewer")
        confirmed_path = root / "confirmed.json"
        confirmed_path.write_text(json.dumps(confirmed, ensure_ascii=False), encoding="utf-8")
        return project, deck, confirmed_path, confirmed

    def test_builds_isolated_case_and_preserves_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project, baseline, confirmed_path, _ = self.make_fixture(root)
            result = case_builder.build_case(project, confirmed_path, root / "case-001", "case-001")

            rendered = Path(result["main_deck"]).read_text(encoding="ascii")
            self.assertIn("1,2,0,0,-8000,0", rendered)
            self.assertIn("1,2,0,0,-1000,0", baseline.read_text(encoding="ascii"))
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "rendered")
            self.assertEqual(manifest["case_id"], "case-001")
            self.assertNotEqual(manifest["changes"][0]["before_sha256"], manifest["changes"][0]["after_sha256"])
            self.assertTrue((root / "case-001" / "input" / "confirmed-parameters.json").is_file())

    def test_rejects_unconfirmed_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project, _, confirmed_path, confirmed = self.make_fixture(root)
            confirmed["state"] = "pending_review"
            confirmed_path.write_text(json.dumps(confirmed, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(case_builder.ContractError):
                case_builder.build_case(project, confirmed_path, root / "case")

    def test_rejects_values_changed_after_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project, _, confirmed_path, confirmed = self.make_fixture(root)
            confirmed["parameters"]["initial_velocity"]["normalized_value"] = -9000
            confirmed_path.write_text(json.dumps(confirmed, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(case_builder.ContractError):
                case_builder.build_case(project, confirmed_path, root / "case")

    def test_baseline_guard_detects_model_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project, baseline, confirmed_path, _ = self.make_fixture(root)
            baseline.write_text(
                "*KEYWORD\n*INITIAL_VELOCITY_GENERATION\n1,2,0,0,-2000,0\n*END\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(case_builder.ContractError, "baseline guard failed"):
                case_builder.build_case(project, confirmed_path, root / "case")

    def test_fixed_width_mapping_changes_only_selected_field(self):
        mapping = {
            "keyword": "CONTROL_TERMINATION", "occurrence": 1, "data_line": 1,
            "field": 2, "format": "fixed", "width": 10, "expected": 5,
            "value_format": ".3g",
        }
        source = "*CONTROL_TERMINATION\n" + "1".rjust(10) + "5".rjust(10) + "9".rjust(10) + "\n"
        rendered = case_builder.apply_mapping(source, mapping, 12)
        self.assertEqual(rendered.splitlines()[1], "1".rjust(10) + "12".rjust(10) + "9".rjust(10))

    def test_project_rejects_non_whitelisted_mapping(self):
        project = project_data()
        project["keyword_mappings"][0]["parameter_id"] = "undeclared"
        with self.assertRaises(case_builder.ContractError):
            case_builder.validate_mapping_contract(project)


if __name__ == "__main__":
    unittest.main()
