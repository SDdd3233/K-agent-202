import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class TemplateAuthoringProtocolTests(unittest.TestCase):
    def setUp(self):
        self.skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.protocol_text = (
            SKILL_DIR / "references" / "template-authoring-protocol.md"
        ).read_text(encoding="utf-8")

    def test_template_requests_have_a_dedicated_route(self):
        route = "**模板制作模式**"
        self.assertIn(route, self.skill_text)
        self.assertIn("references/template-authoring-protocol.md", self.skill_text)
        self.assertIn("--outdir template_build/<模板名称>", self.skill_text)
        self.assertIn("**已有 deck 模式**", self.skill_text)

    def test_protocol_protects_source_and_separates_candidate_validation(self):
        self.assertIn("source/", self.protocol_text)
        self.assertIn("只读", self.protocol_text)
        self.assertIn("working/", self.protocol_text)
        self.assertIn("validation/", self.protocol_text)
        self.assertIn("不得直接编辑上传文件", self.protocol_text)

    def test_protocol_limits_questions_across_the_whole_request(self):
        self.assertIn("整个模板制作请求中不得超过 **5 个**", self.protocol_text)
        self.assertIn("一次集中提出", self.protocol_text)
        self.assertIn("只问影响结果的问题", self.protocol_text)

    def test_protocol_blocks_final_validation_until_answers(self):
        self.assertIn("问题未回答前不得抽象最终模板或进行最终 L2 验证", self.skill_text)
        self.assertIn("暂停模板抽象和最终验证", self.protocol_text)
        self.assertIn("模板候选必须重新验证", self.protocol_text)


class NoTemplateRoutingProtocolTests(unittest.TestCase):
    def test_skill_blocks_writing_when_template_evidence_is_missing(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("模板目录存在不等于模板可用", skill_text)
        self.assertIn("无适用模板时，必须先完成 LS-DYNA 官方资料/官方算例检索和学术文献检索", skill_text)
        self.assertIn("不得用普通网页搜索、既有经验或相邻模板直接替代该双链路", skill_text)
        self.assertIn("research/literature-evidence.json", skill_text)

    def test_brainstorm_protocol_requires_applicability_and_evidence_in_spec(self):
        protocol_text = (SKILL_DIR / "references" / "brainstorm-protocol.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("四项中任一项为“不能支撑”即视为无适用模板", protocol_text)
        self.assertIn("在双链路完成前", protocol_text)
        self.assertIn("模板适用性判定：", protocol_text)
        self.assertIn("`research/literature-evidence.json`：", protocol_text)

    def test_spec_confirmation_blocks_kfile_work_until_explicit_approval(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        protocol_text = (SKILL_DIR / "references" / "brainstorm-protocol.md").read_text(
            encoding="utf-8"
        )

        for text in (skill_text, protocol_text):
            self.assertIn("收到用户明确同意前", text)
            self.assertIn("不得生成、复制、修改或运行任何最终 `.k` 文件", text)

    def test_skill_requires_persisted_final_delivery_report(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("final_delivery_report.md", skill_text)
        self.assertIn("再向用户发送一份同内容或等价摘要的“最终交付报告”", skill_text)
        self.assertIn("在报告写入并", skill_text)
        self.assertIn("发送前不得结束任务", skill_text)

    def test_literature_routing_names_explosive_welding_trigger(self):
        routing_text = (
            SKILL_DIR / "references" / "literature-parameter-routing.md"
        ).read_text(encoding="utf-8")

        self.assertIn("explosive welding", routing_text)
        self.assertIn("interface wave", routing_text)
        self.assertIn("template_applicability", routing_text)
        self.assertIn("official_basis", routing_text)


if __name__ == "__main__":
    unittest.main()
