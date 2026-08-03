import os
import unittest
from pathlib import Path


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_PATH = Path(os.environ.get("LSDYNA_SKILL_UNDER_TEST", DEFAULT_SKILL_DIR / "SKILL.md"))
RESOURCE_ROOT = Path(os.environ.get("LSDYNA_RESOURCE_ROOT", DEFAULT_SKILL_DIR))


class SkillWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.resources = {}
        for relative in (
            "references/brainstorm-protocol.md",
            "references/existing-deck-repair.md",
            "references/kfile-format.md",
            "references/literature-parameter-routing.md",
            "references/quality-gates.md",
            "knowledge/errors.md",
            "knowledge/materials.json",
        ):
            path = RESOURCE_ROOT / relative
            cls.resources[relative] = path.read_text(encoding="utf-8")

    def test_frontmatter_and_mode_routing_are_preserved(self):
        for required in (
            "name: lsdyna-kfile",
            "已有 deck 模式",
            "新建 deck 模式",
            "跳过 §1 需求头脑风暴",
            "references/existing-deck-repair.md",
            "prepare_existing_deck.py",
            "原 deck 的物理意图",
        ):
            self.assertIn(required, self.skill)

    def test_environment_contract_is_preserved(self):
        for required in (
            "kagent_config.py",
            "C:\\Program Files\\ANSYS Inc\\v242\\ansys\\bin\\winx64",
            "R14.1.1",
            "R15",
            "LSDYNA_BIN",
            "LSDYNA_MPIEXEC",
            "~/.lsdyna-kagent.json",
            "fetch_manuals.py",
        ):
            self.assertIn(required, self.skill)

    def test_new_deck_gates_and_order_are_preserved(self):
        required = (
            "references/brainstorm-protocol.md",
            "最多 5 轮",
            "每轮最多 4 个问题",
            "2-4 个",
            "[默认]",
            'python "SKILL_DIR/scripts/units.py" list',
            "knowledge/errors.md",
            "模板目录存在不等于模板可用",
            "无适用模板时，必须先完成 LS-DYNA",
            "官方资料/官方算例检索和学术文献检索",
            "不得用普通网页搜索、既有经验或相邻模板直接替代该双链路",
            "research/literature-evidence.json",
            "no-similar-case",
            "M0~M3",
            "spec.md",
            "收到用户明确同意前",
            "不得生成、复制、修改或运行任何最终 `.k` 文件",
            "[假设]",
        )
        for item in required:
            self.assertIn(item, self.skill)

        ordered = (
            "references/brainstorm-protocol.md",
            "knowledge/errors.md",
            "模板目录存在不等于模板可用",
            "收到用户明确同意前",
            "## 3.",
            "## 4.",
            "## 5.",
        )
        new_deck_flow = self.skill[self.skill.index("## 2.") :]
        positions = [new_deck_flow.index(item) for item in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_baseline_templates_and_m0_m3_checks_are_preserved(self):
        for required in (
            "templates/drop/",
            "templates/crash/",
            "templates/penetration/",
            "templates/forming/",
            "templates/ale/",
            "templates/sph/",
            "mm-ton-s",
            "cm-g-us",
            "m-kg-s",
            "mm-kg-ms",
            "M0 先过 L0/L1",
            "单单元/简化试件",
            "穿透、初始间隙、反力",
            "每次只增加一类复杂度",
            "敏感性分析",
        ):
            self.assertIn(required, self.skill)

    def test_information_and_construction_contract_is_preserved(self):
        for required in (
            "units.py",
            "不得手抄换算",
            "manual_index.py",
            "pypdf.PdfReader",
            "references/literature-parameter-routing.md",
            "references/kfile-format.md",
            "PID=SECID=MID=n",
            "nid0=eid0=n*100000",
            "sid0=n*10",
            "曲线从 901",
            "part set 从 801",
            "*CONTROL_TERMINATION",
            "HGEN=2 RWEN=2 SLNTEN=2 RYLEN=2",
            "TSSFAC=0.9",
            "ENDTIM/200",
            "ENDTIM/20",
            "plate / box / cylinder / cylshell / sphere / sphbox / sphcyl",
            "--axis x|y|z",
            "gen_mesh.py",
        ):
            self.assertIn(required, self.skill)

    def test_validation_repair_and_final_delivery_chain_is_preserved(self):
        commands = (
            'check_kfile.py" model.k',
            "--endcyc 50 --ncpu 4 --timeout 300",
            'parse_results.py" .',
            '--ncpu 4 --timeout 1800',
            'parse_results.py" . --json report.json',
        )
        for command in commands:
            self.assertIn(command, self.skill)
        positions = [self.skill.index(command) for command in commands]
        self.assertEqual(positions, sorted(positions))

        for required in (
            "0 errors",
            "model_trial.k",
            "references/quality-gates.md",
            "最多 8 轮",
            "从 L0 重跑",
            "WARN",
            "症状/原因/修法/日期",
            "--mode mpp --ncpu 8",
            "--ncpu 2",
            "60 s",
            "sp",
            "--precision dp",
            "final_delivery_report.md",
            "再向用户发送一份同内容或等价摘要",
            "在报告写入并",
            "发送前不得结束任务",
            "report.json",
            "run.log",
            "未获得",
        ):
            self.assertIn(required, self.skill)

    def test_referenced_protocols_retain_delegated_thresholds_and_safety_rules(self):
        effective = "\n".join(self.resources.values())
        for required in (
            "max\\|total/initial − 1\\| ≤ 0.10",
            "峰值沙漏能/峰值内能 ≤ 0.10",
            "质量增加 ≤ 5%",
            "侵彻类可放宽到 0.15",
            "S-ALE 多物质对流可放宽到 0.2",
            "动能/内能 < 5%",
            "search_papers",
            "setup_academic_mcp.py",
            "Never modify the user's original deck directly",
            "Stop after PASS at L1, then run L2",
            "If not repaired within 8 iterations",
            "*DEFINE_CURVE",
            "A(20) O(20)",
            "PART 定义了但网格 include 漏了",
            '"steel_mild"',
            '"water"',
            '"air"',
        ):
            self.assertIn(required, effective)

    def test_install_candidate_has_no_preview_relative_paths(self):
        if SKILL_PATH.parent.name == ".reduced":
            for forbidden in ("../references/", "../knowledge/", "../scripts/", "本压缩预览"):
                self.assertNotIn(forbidden, self.skill)


if __name__ == "__main__":
    unittest.main()
