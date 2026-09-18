import importlib.util
import json
import subprocess
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


parameter_contract = load_module("parameter_contract_workflow", SCRIPTS_DIR / "parameter_contract.py")
case_builder = load_module("case_builder_workflow", SCRIPTS_DIR / "build_parameterized_case.py")
workflow = load_module("parameter_case_workflow", SCRIPTS_DIR / "parameter_case_workflow.py")


def project_data():
    return {
        "schema_version": 1,
        "project_id": "workflow-test",
        "unit_system": "mm-ton-s",
        "baseline": {"root": "baseline", "main_deck": "model.k"},
        "parameters": [{
            "parameter_id": "end_time", "name": "终止时间", "aliases": ["计算时间"],
            "type": "number", "dimension": "time", "accepted_units": ["s"],
            "allowed_range": {"min": 0.001, "max": 1}, "required": True,
            "requires_confirmation": True,
        }],
        "keyword_mappings": [{
            "parameter_id": "end_time", "target_file": "model.k",
            "keyword": "CONTROL_TERMINATION", "occurrence": 1,
            "data_line": 1, "field": 1, "format": "csv", "expected": 0.01,
            "value_format": ".9g",
        }],
    }


class ParameterCaseWorkflowTests(unittest.TestCase):
    def make_case(self, root):
        baseline = root / "baseline"
        baseline.mkdir()
        (baseline / "model.k").write_text(
            "*KEYWORD\n*CONTROL_TERMINATION\n0.01,0,0,0,0,0,0,0\n*END\n",
            encoding="ascii",
        )
        project = root / "project.json"
        project.write_text(json.dumps(project_data(), ensure_ascii=False), encoding="utf-8")
        extracted = parameter_contract.extract_text(project_data(), "计算时间为 0.02 s")
        confirmed = parameter_contract.confirm_extraction(project_data(), extracted, "user")
        confirmed_path = root / "confirmed.json"
        confirmed_path.write_text(json.dumps(confirmed, ensure_ascii=False), encoding="utf-8")
        result = case_builder.build_case(project, confirmed_path, root / "case", "case-test")
        return Path(result["case_dir"])

    def test_review_markdown_contains_values_and_evidence(self):
        extracted = parameter_contract.extract_text(project_data(), "计算时间为 0.02 s")
        review = parameter_contract.review_markdown(extracted)
        self.assertIn("参数抽取审查单", review)
        self.assertIn("0.02", review)
        self.assertIn("原文证据", review)
        self.assertIn("等待用户确认", review)

    def test_real_l0_gate_passes_minimal_case(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = self.make_case(Path(temp_dir))
            result = workflow.run_l0(case_dir)
            self.assertTrue(result["passed"])
            self.assertEqual(result["state"], "l0_passed")
            manifest = json.loads((case_dir / "case-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["l0"]["verdict"], "PASS")

    def test_integrity_check_blocks_modified_deck(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = self.make_case(Path(temp_dir))
            (case_dir / "deck" / "model.k").write_text("tampered\n", encoding="ascii")
            with self.assertRaises(workflow.ContractError):
                workflow.run_l0(case_dir)

    def test_submit_is_blocked_before_l0(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = self.make_case(Path(temp_dir))
            with self.assertRaises(workflow.ContractError):
                workflow.submit_case(case_dir)

    def test_submit_records_solver_result_after_l0(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = self.make_case(Path(temp_dir))
            workflow.run_l0(case_dir)

            def fake_runner(command, **kwargs):
                output = 'solver output\n{"status":"normal","elapsed_s":1.2,"log":"run.log"}\n'
                return subprocess.CompletedProcess(command, 0, output, "")

            result = workflow.submit_case(case_dir, ncpu=2, runner=fake_runner)
            self.assertEqual(result["state"], "solver_normal")
            manifest = json.loads((case_dir / "case-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["submission"]["result"]["status"], "normal")
            self.assertTrue((case_dir / "run" / "workflow-launcher.log").is_file())

    def test_submit_rejects_changed_l0_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = self.make_case(Path(temp_dir))
            workflow.run_l0(case_dir)
            (case_dir / "validation" / "l0-report.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(workflow.ContractError, "L0 evidence"):
                workflow.submit_case(case_dir)


if __name__ == "__main__":
    unittest.main()
