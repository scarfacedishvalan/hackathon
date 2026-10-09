"""Offline checks of unbound tools, scope, statistics, and prompt compatibility."""

import json
import unittest
from datetime import date
from statistics import fmean, pstdev

from app.services.bl_backtest.agent_utils import prompts as legacy_prompts
from app.services.bl_backtest.agent_utils.research import make_research_tools
from app.services.bl_backtest.agent_utils.research import prompts
from app.services.bl_backtest.data_interface.load import load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context, summarize_evidence_values
from app.services.bl_backtest.schema import ResearchRequest


class ResearchToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_research_data()

    def setUp(self):
        self.context = prepare_context(self.data, ResearchRequest(
            hypothesis="Use EPS revisions", universe=["AAPL", "MSFT", "BND"],
            as_of=date(2021, 9, 30),
        ))
        self.tools = make_research_tools(self.context)

    def test_research_prompt_imports_are_compatible(self):
        self.assertEqual(legacy_prompts.SYSTEM_PROMPT, prompts.SYSTEM_PROMPT)
        self.assertEqual(legacy_prompts.RESEARCH_AGENT, prompts.RESEARCH_AGENT)
        self.assertIs(legacy_prompts.build_user_prompt, prompts.build_user_prompt)
        self.assertEqual(json.loads(prompts.build_user_prompt(self.context)), self.context.model_dump(mode="json"))

    def test_query_returns_only_selected_asset_and_macro_evidence(self):
        result = self.tools["query_evidence"]("AAPL")
        self.assertEqual(result["observation_date"], "2021-09-30")
        self.assertTrue(all(item["asset"] in (None, "AAPL") for item in result["evidence"].values()))
        self.assertTrue(all(item["end"] <= "2021-09-30" for item in result["evidence"].values()))
        json.dumps(result)
        selected = self.tools["query_evidence"]("AAPL", ["eps_change_21"], include_macro=False)
        self.assertEqual(list(selected["evidence"]), ["AAPL.eps_change_21"])
        self.assertEqual(selected["evidence"]["AAPL.eps_change_21"]["source"], "eps_estimates_revisions.csv")

    def test_query_rejects_unknown_universe_and_metrics(self):
        for args in [
            ("JPM",), ("AAPL", ["made_up"]), ("AAPL", []),
            ("AAPL", ["eps_latest", "eps_latest"]), ("AAPL", "eps_latest"),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.tools["query_evidence"](*args)
        with self.assertRaises(ValueError):
            self.tools["query_evidence"]("AAPL", include_macro="yes")

    def test_summaries_reuse_existing_features_and_units(self):
        for signal, reference, unit in [
            ("eps", "AAPL.eps_change_63", "fraction"),
            ("returns", "AAPL.return_63", "fraction"),
            ("rates", "macro.yield_10y_change_63", "basis_points"),
        ]:
            result = self.tools["summarize_signal"]("AAPL", signal)
            self.assertEqual(result["evidence"][reference], self.context.evidence[reference].model_dump(mode="json"))
            self.assertEqual(result["evidence"][reference]["unit"], unit)
        for signal, lookback in [("unknown", 63), ("eps", 42), ("eps", True), ("eps", "63")]:
            with self.subTest(signal=signal, lookback=lookback), self.assertRaises(ValueError):
                self.tools["summarize_signal"]("AAPL", signal, lookback)

    def test_comparison_matches_numerical_statistics_and_preserves_provenance(self):
        result = self.tools["compare_signals"](["AAPL", "MSFT", "BND"], "eps", 21)
        stats = result["statistics"]
        values = [self.context.evidence[f"{asset}.eps_change_21"].value for asset in ("AAPL", "MSFT")]
        self.assertEqual(stats["available_count"], 2)
        self.assertEqual(stats["excluded"], {"BND.eps_change_21": "not_applicable"})
        self.assertAlmostEqual(stats["mean"], fmean(values))
        self.assertAlmostEqual(stats["population_stddev"], pstdev(values))
        self.assertEqual(stats["minimum"], min(values))
        self.assertEqual(stats["maximum"], max(values))
        self.assertEqual(len(result["evidence"]), 3)
        json.dumps(result)

    def test_unavailable_and_single_asset_statistics_are_explicit(self):
        result = self.tools["compare_signals"](["BND"], "eps")
        self.assertEqual(result["statistics"]["available_count"], 0)
        self.assertIsNone(result["statistics"]["mean"])
        self.assertIsNone(result["statistics"]["population_stddev"])
        one = self.tools["compare_signals"](["AAPL"], "returns")
        self.assertEqual(one["statistics"]["population_stddev"], 0)
        early_context = prepare_context(self.data, self.context.request.model_copy(update={"as_of": date(2021, 3, 19)}))
        early = make_research_tools(early_context)["compare_signals"](["AAPL", "MSFT"], "returns")
        self.assertEqual(early["statistics"]["available_count"], 0)
        self.assertEqual(set(early["statistics"]["excluded"].values()), {"insufficient_history"})

    def test_comparison_restrictions(self):
        for assets, signal in [
            ([], "eps"), (["AAPL", "AAPL"], "eps"), (["JPM"], "eps"),
            (["AAPL"], "rates"), ("AAPL", "eps"),
        ]:
            with self.subTest(assets=assets, signal=signal), self.assertRaises(ValueError):
                self.tools["compare_signals"](assets, signal)
        mismatch = {
            "AAPL.eps_change_63": self.context.evidence["AAPL.eps_change_63"],
            "MSFT.return_63": self.context.evidence["MSFT.return_63"],
        }
        with self.assertRaisesRegex(ValueError, "matching metrics"):
            summarize_evidence_values(mismatch)
        with self.assertRaises(ValueError):
            summarize_evidence_values({})

    def test_private_snapshot_and_return_values_cannot_expand_scope(self):
        original_value = self.context.evidence["AAPL.eps_latest"].value
        self.context.evidence["AAPL.eps_latest"].value = 999
        self.context.request.universe.append("JPM")
        result = self.tools["query_evidence"]("AAPL")
        self.assertEqual(result["evidence"]["AAPL.eps_latest"]["value"], original_value)
        result["evidence"]["AAPL.eps_latest"]["value"] = -1
        self.assertEqual(
            self.tools["query_evidence"]("AAPL")["evidence"]["AAPL.eps_latest"]["value"],
            original_value,
        )
        with self.assertRaises(ValueError):
            self.tools["query_evidence"]("JPM")

    def test_future_evidence_and_invalid_identity_are_rejected(self):
        self.context.evidence["AAPL.eps_latest"].end = date(2021, 10, 1)
        with self.assertRaisesRegex(ValueError, "cutoff"):
            make_research_tools(self.context)
        self.context.evidence["AAPL.eps_latest"].end = date(2021, 9, 30)
        self.context.evidence["AAPL.eps_change_63"].asset = "MSFT"
        tools = make_research_tools(self.context)
        with self.assertRaisesRegex(ValueError, "identity"):
            tools["summarize_signal"]("AAPL", "eps")


if __name__ == "__main__":
    unittest.main()
