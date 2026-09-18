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


parameter_contract = load_module("parameter_contract", SCRIPTS_DIR / "parameter_contract.py")


def contract():
    return {
        "schema_version": 1,
        "project_id": "test-project",
        "unit_system": "mm-ton-s",
        "parameters": [
            {
                "parameter_id": "initial_velocity",
                "name": "初始速度",
                "aliases": ["装填速度", "冲击速度"],
                "type": "number",
                "dimension": "velocity",
                "accepted_units": ["m/s", "mm/s", "km/h"],
                "deck_multiplier": -1,
                "allowed_range": {"min": -20000, "max": 0},
                "required": True,
                "requires_confirmation": True,
            },
            {
                "parameter_id": "friction_coefficient",
                "name": "摩擦系数",
                "aliases": ["摩擦因数"],
                "type": "number",
                "dimension": "dimensionless",
                "allowed_range": {"min": 0, "max": 1},
                "required": False,
                "requires_confirmation": True,
            },
        ],
    }


class ParameterContractTests(unittest.TestCase):
    def test_extracts_from_long_text_and_normalizes_units(self):
        text = ("背景信息。" * 5000) + "装填速度调整为 8 m/s，摩擦系数为0.12。" + ("补充说明。" * 5000)
        result = parameter_contract.extract_text(contract(), text, "request.txt")

        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["state"], "pending_review")
        self.assertEqual(result["parameters"]["initial_velocity"]["normalized_value"], -8000.0)
        self.assertEqual(result["parameters"]["initial_velocity"]["normalized_unit"], "mm/s")
        self.assertEqual(result["parameters"]["friction_coefficient"]["normalized_value"], 0.12)
        evidence = result["parameters"]["initial_velocity"]["candidates"][0]["evidence"]
        self.assertEqual(text[evidence["start"]:evidence["end"]], "装填速度调整为 8 m/s")

    def test_missing_required_parameter_fails_closed(self):
        result = parameter_contract.extract_text(contract(), "摩擦系数为 0.2")
        self.assertFalse(result["validation"]["valid"])
        self.assertEqual(result["state"], "validation_failed")
        self.assertEqual(result["missing_required"], ["initial_velocity"])

    def test_missing_unit_is_reported_not_guessed(self):
        result = parameter_contract.extract_text(contract(), "初始速度为 8")
        self.assertFalse(result["validation"]["valid"])
        errors = result["parameters"]["initial_velocity"]["validation"]["errors"]
        self.assertIn("missing explicit unit", errors)

    def test_conflicting_values_are_rejected(self):
        result = parameter_contract.extract_text(contract(), "初始速度 8 m/s，随后冲击速度改为 9 m/s")
        self.assertFalse(result["validation"]["valid"])
        self.assertEqual(len(result["conflicts"]), 1)

    def test_out_of_range_value_is_rejected(self):
        result = parameter_contract.extract_text(contract(), "初始速度为 30 m/s")
        self.assertFalse(result["validation"]["valid"])
        self.assertIn("below minimum", " ".join(result["validation"]["errors"]))

    def test_non_whitelisted_injected_parameter_is_rejected(self):
        result = parameter_contract.extract_text(contract(), "初始速度为 8 m/s")
        result["parameters"]["delete_contact"] = {"normalized_value": 1}
        checked = parameter_contract.validate_extraction(contract(), result)
        self.assertFalse(checked["validation"]["valid"])
        self.assertIn("non-whitelisted", " ".join(checked["validation"]["errors"]))

    def test_confirmation_requires_valid_data_and_reviewer(self):
        valid = parameter_contract.extract_text(contract(), "初始速度为 8 m/s")
        confirmed = parameter_contract.confirm_extraction(contract(), valid, "测试用户", "同意提交")
        self.assertEqual(confirmed["state"], "confirmed")
        self.assertEqual(confirmed["review"]["reviewer"], "测试用户")
        self.assertEqual(confirmed["parameters"]["initial_velocity"]["review_status"], "confirmed")

        invalid = parameter_contract.extract_text(contract(), "摩擦系数为 0.2")
        with self.assertRaises(parameter_contract.ContractError):
            parameter_contract.confirm_extraction(contract(), invalid, "测试用户")

    def test_cli_round_trip_writes_utf8_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project.json"
            request = root / "request.txt"
            extracted = root / "extracted.json"
            project.write_text(json.dumps(contract(), ensure_ascii=False), encoding="utf-8")
            request.write_text("装填速度为 28.8 km/h", encoding="utf-8")
            code = parameter_contract.main([
                "extract", str(project), "--text-file", str(request), "--out", str(extracted)
            ])
            self.assertEqual(code, 0)
            data = json.loads(extracted.read_text(encoding="utf-8"))
            self.assertEqual(data["parameters"]["initial_velocity"]["normalized_value"], -8000.0)


if __name__ == "__main__":
    unittest.main()
