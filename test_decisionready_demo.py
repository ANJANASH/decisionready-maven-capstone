import unittest

from decisionready_demo import (
    PROPOSAL_E_XLSX,
    STATUS_TARGETS,
    analyze_proposal_e_workbook,
    assess_benchmark,
    benchmark_proposals,
    custom_preview,
    smoke_regression,
)


class DecisionReadyDemoTests(unittest.TestCase):
    def test_benchmark_texts_are_available(self):
        proposals = benchmark_proposals()
        self.assertEqual(set(proposals), set(STATUS_TARGETS))
        self.assertTrue(all(len(text) > 100 for text in proposals.values()))

    def test_frozen_statuses(self):
        for name, expected in STATUS_TARGETS.items():
            with self.subTest(name=name):
                self.assertEqual(assess_benchmark(name)["readiness_status"], expected)

    def test_proposal_e_local_workbook(self):
        analysis = analyze_proposal_e_workbook(PROPOSAL_E_XLSX)
        self.assertTrue(analysis["is_canonical"])
        self.assertEqual(
            analysis["sheet_names"],
            ["01_Assumptions", "02_Base_Case", "03_Sensitivity"],
        )
        self.assertGreater(analysis["formula_count"], 0)
        self.assertEqual(len(analysis["findings"]), 7)

    def test_custom_input_fails_closed_without_external_call(self):
        result = custom_preview("Approve a short pilot.")
        self.assertEqual(result["readiness_status"], "NOT_ASSESSED")
        self.assertEqual(result["tool_trace"]["selected_tool"], "none")
        self.assertEqual(result["tool_trace"]["calls_used"], 0)

    def test_complete_smoke_regression(self):
        summary = smoke_regression()
        self.assertEqual(summary["statuses"], STATUS_TARGETS)
        self.assertEqual(
            summary["tools_reachable"],
            ["external_search", "internal_retrieval", "none", "spreadsheet_analysis"],
        )


if __name__ == "__main__":
    unittest.main()
