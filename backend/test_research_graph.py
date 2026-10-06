"""Offline contracts, monthly integration, and notebook execution tests."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bt
import numpy as np
import pandas as pd
from pydantic import ValidationError

from app.services.bl_backtest.data_interface.load import DATA_DIR, load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context
from app.services.bl_backtest.data_interface.query import rebalance_date
from app.services.bl_backtest.research_graph import STAGES, build_research_graph, run_research
from app.services.bl_backtest.research_weights import make_research_weight_fn, views_to_weights
from app.services.bl_backtest.run_example import HYPOTHESIS, build_agentic_strategy, build_equal_weight_strategy
from app.services.bl_backtest.schema import AssetView, ResearchContext, ResearchRequest, ViewBatch, validate_views
from app.services.llm_client import OpenAIClientWrapper, chat_and_record


class FakeResearchClient:
    model = "gpt-4.1-mini"
    last_prompt_tokens = 10
    last_completion_tokens = 20

    def __init__(self):
        self.calls = []
        self.response = None
        self.failure = None
        self.feedback_calls = []

    def chat(self, *, system_prompt, user_prompt, schema, temperature, max_tokens):
        if "context" in json.loads(user_prompt):
            payload = json.loads(user_prompt)
            self.feedback_calls.append(payload)
            if "critic" in payload:
                return json.dumps({
                    "views": payload["proposed_views"]["views"],
                    "needs_review": False, "summary": "Keep supported views.",
                })
            return json.dumps({"critiques": [
                {
                    "view_index": i, "classification": "SUPPORTED", "recommendation": "KEEP",
                    "evidence_quality": "Available evidence.", "contradictions": "None.",
                    "materiality": "Meaningful.", "redundancy": "Distinct asset.",
                    "confidence_assessment": "Proportional.",
                    "evidence_cited": view["evidence_cited"],
                }
                for i, view in enumerate(payload["proposed_views"]["views"])
            ]})
        context = ResearchContext.model_validate_json(user_prompt)
        self.calls.append(context)
        if self.failure:
            raise self.failure
        if self.response is not None:
            return self.response
        views = []
        for asset in context.request.universe:
            evidence = context.evidence[f"{asset}.eps_change_63"]
            direction = "neutral"
            if evidence.status == "available":
                direction = "positive" if evidence.value >= 0 else "negative"
                if "reverse" in context.request.hypothesis:
                    direction = "negative" if direction == "positive" else "positive"
            views.append({
                "asset": asset, "direction": direction,
                "magnitude": 0.0 if direction == "neutral" else 0.6,
                "confidence": 0.8, "rationale": "Assessment of supplied EPS evidence.",
                "evidence_cited": [f"{asset}.eps_change_63"],
            })
        return json.dumps({"views": views})


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_research_data()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Path(self.temporary.name) / "usage.db"
        self.client = FakeResearchClient()
        self.request = ResearchRequest(
            hypothesis=HYPOTHESIS, universe=["AAPL", "MSFT", "BND"], as_of=date(2021, 9, 30),
        )
        self.context = prepare_context(self.data, self.request)

    def test_actual_dataset_shapes_and_units(self):
        self.assertEqual(len(self.data.eps), 16302)
        self.assertEqual(len(self.data.prices), 1254)
        self.assertEqual(len(self.data.returns), 1253)
        self.assertEqual(len(self.data.metadata["all_assets"]), 13)
        self.assertEqual(self.context.evidence["BND.eps_latest"].status, "not_applicable")
        self.assertIsNone(self.context.evidence["BND.eps_latest"].value)
        self.assertEqual(self.context.evidence["macro.yield_10y_latest"].unit, "percent")
        self.assertEqual(self.context.evidence["macro.yield_10y_change_63"].unit, "basis_points")

    def test_endpoint_calculations_and_cutoff(self):
        context = prepare_context(self.data, self.request.model_copy(update={"as_of": date(2021, 9, 26)}))
        self.assertEqual(context.observation_date, date(2021, 9, 24))
        for entry in context.evidence.values():
            self.assertLessEqual(entry.end, context.observation_date)
        levels = self.data.eps.query("ticker == 'AAPL'").set_index("date").loc[:"2021-09-24", "eps_estimate_usd"]
        self.assertAlmostEqual(context.evidence["AAPL.eps_change_63"].value, levels.iloc[-1] / levels.iloc[-64] - 1)
        yields = self.data.rates.set_index("date").loc[:"2021-09-24", "yield_10y_pct"]
        self.assertAlmostEqual(context.evidence["macro.yield_10y_change_21"].value, (yields.iloc[-1] - yields.iloc[-22]) * 100)
        prices = self.data.prices.loc[:"2021-09-24", "AAPL"]
        self.assertAlmostEqual(context.evidence["AAPL.return_63"].value, prices.iloc[-1] / prices.iloc[-64] - 1)

    def test_first_observation_and_short_history_are_not_zero(self):
        request = self.request.model_copy(update={"as_of": date(2021, 3, 19)})
        context = prepare_context(self.data, request)
        self.assertEqual(context.evidence["AAPL.eps_change_63"].status, "insufficient_history")
        self.assertIsNone(context.evidence["AAPL.eps_change_63"].value)
        self.assertTrue(self.data.rates.iloc[0]["change_bp"] != self.data.rates.iloc[0]["change_bp"])

    def test_invalid_requests_dates_and_price_windows(self):
        for payload in [
            {"hypothesis": " ", "universe": ["AAPL"]},
            {"hypothesis": "research", "universe": ["AAPL", "AAPL"]},
            {"hypothesis": "research", "universe": []},
        ]:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ResearchRequest(**payload)
        for request in [
            self.request.model_copy(update={"universe": ["UNKNOWN"]}),
            self.request.model_copy(update={"as_of": date(2030, 1, 1)}),
        ]:
            with self.assertRaises(ValueError):
                prepare_context(self.data, request)
        with self.assertRaises(ValueError):
            rebalance_date(pd.Timestamp("2021-09-30", tz="UTC"))
        future = self.data.prices.loc[:"2021-10-01", self.request.universe]
        with self.assertRaisesRegex(ValueError, "after as_of"):
            prepare_context(self.data, self.request, future)
        window = self.data.prices.loc[:"2021-09-30", self.request.universe].iloc[-20:]
        context = prepare_context(self.data, self.request, window)
        self.assertEqual(context.evidence["AAPL.return_63"].observations, 20)
        self.assertEqual(context.evidence["AAPL.return_63"].status, "insufficient_history")
        with self.assertRaisesRegex(ValueError, "contiguous"):
            prepare_context(self.data, self.request, window.iloc[::2])

    def test_source_errors_are_not_filled(self):
        path = Path(self.temporary.name) / "sources"
        path.mkdir()
        for name in ["market_prices.csv", "market_returns.csv", "rates_10y.csv", "eps_estimates_revisions.csv"]:
            (path / name).write_bytes((DATA_DIR / name).read_bytes())
        prices = pd.read_csv(path / "market_prices.csv")
        prices.loc[3, "AAPL"] = np.nan
        prices.to_csv(path / "market_prices.csv", index=False)
        with self.assertRaisesRegex(ValueError, "finite"):
            load_research_data(path)
        (path / "market_prices.csv").write_bytes((DATA_DIR / "market_prices.csv").read_bytes())
        rates = pd.read_csv(path / "rates_10y.csv")
        rates.loc[2, "change_bp"] += 10
        rates.to_csv(path / "rates_10y.csv", index=False)
        with self.assertRaisesRegex(ValueError, "rate changes"):
            load_research_data(path)
        rates = pd.read_csv(DATA_DIR / "rates_10y.csv")
        pd.concat([rates, rates.iloc[[0]]]).to_csv(path / "rates_10y.csv", index=False)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_research_data(path)

    def test_graph_has_feedback_stages_and_fresh_state(self):
        graph = build_research_graph(llm_client=self.client, db_path=self.db)
        for _ in range(2):
            result = graph.invoke({"context": self.context})["result"]
            self.assertEqual(result.stages, STAGES)
            self.assertEqual([v.asset for v in result.views.views], self.request.universe)
            self.assertEqual(result.views.views[-1].direction, "neutral")
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(len(self.client.feedback_calls), 4)
        self.assertEqual(self.client.calls[0].request.hypothesis, HYPOTHESIS)

    def test_invalid_responses_and_provider_errors_fail(self):
        for response in ["not JSON", "", '{"views": [], "unexpected": 1}']:
            self.client.response = response
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, "analyze_available_evidence"):
                run_research(self.context, llm_client=self.client, db_path=self.db)
        self.client.response = None
        self.client.failure = RuntimeError("provider unavailable")
        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            run_research(self.context, llm_client=self.client, db_path=self.db)

    def test_strict_view_validation(self):
        base = {
            "asset": "AAPL", "direction": "positive", "magnitude": 0.5, "confidence": 0.7,
            "rationale": "Evidence", "evidence_cited": ["AAPL.eps_change_63"],
        }
        for patch_values in [
            {"magnitude": True}, {"confidence": "0.5"}, {"confidence": float("nan")},
            {"magnitude": float("inf")}, {"magnitude": -0.1},
            {"direction": "neutral"}, {"rationale": " "},
            {"evidence_cited": ["x", "x"]}, {"extra": 1},
        ]:
            with self.subTest(patch_values=patch_values), self.assertRaises(ValidationError):
                AssetView(**{**base, **patch_values})
        result = run_research(self.context, llm_client=self.client, db_path=self.db)
        for reference in ["fabricated", "MSFT.eps_change_63"]:
            invalid = result.views.model_copy(deep=True)
            invalid.views[0].evidence_cited = [reference]
            with self.assertRaises(ValueError):
                validate_views(invalid, self.context)
        invalid = result.views.model_copy(deep=True)
        invalid.views[-1].direction = "positive"
        invalid.views[-1].magnitude = 0.4
        with self.assertRaisesRegex(ValueError, "available numerical"):
            validate_views(invalid, self.context)
        self.assertEqual(len(validate_views(ViewBatch(views=[result.views.views[0]]), self.context).views), 1)
        self.assertEqual(validate_views(ViewBatch(views=[]), self.context).views, [])
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_views(ViewBatch(views=[result.views.views[0], result.views.views[0]]), self.context)
        reversed_batch = ViewBatch(views=list(reversed(result.views.views)))
        self.assertEqual([v.asset for v in validate_views(reversed_batch, self.context).views], self.request.universe)

    def test_weight_formula_and_hypothesis_reaches_each_call(self):
        records = []
        callback = make_research_weight_fn(data=self.data, llm_client=self.client, db_path=self.db, records=records)
        window = self.data.prices.loc[:"2021-09-30", self.request.universe]
        forward = callback(window, self.request.universe, HYPOTHESIS, pd.Timestamp("2021-09-30"))
        reverse = callback(window, self.request.universe, "reverse the EPS hypothesis", pd.Timestamp("2021-09-30"))
        self.assertNotEqual(forward, reverse)
        for record in records:
            self.assertAlmostEqual(sum(record.weights.values()), 1)
            self.assertTrue(all(value > 0 for value in record.weights.values()))
            self.assertEqual(record.status, "research")
        self.assertEqual(len(self.client.calls), 2)
        batch = ViewBatch(views=[
            AssetView(asset="AAPL", direction="positive", magnitude=1.0, confidence=1.0, rationale="a", evidence_cited=["a"]),
            AssetView(asset="MSFT", direction="negative", magnitude=1.0, confidence=1.0, rationale="b", evidence_cited=["b"]),
        ])
        self.assertEqual(views_to_weights(batch), {"AAPL": 0.75, "MSFT": 0.25})

    def test_warmup_is_explicit_and_never_calls_model(self):
        records = []
        callback = make_research_weight_fn(data=self.data, llm_client=self.client, db_path=self.db, records=records)
        window = self.data.prices.loc[:"2021-04-01", self.request.universe]
        weights = callback(window, self.request.universe, HYPOTHESIS, pd.Timestamp("2021-04-01"))
        self.assertEqual(weights, {a: 1 / 3 for a in self.request.universe})
        self.assertEqual(records[0].status, "warmup_equal_weight")
        self.assertIsNone(records[0].research)
        self.assertEqual(self.client.calls, [])

    def test_real_bt_monthly_rebalance_hook(self):
        records = []
        callback = make_research_weight_fn(data=self.data, llm_client=self.client, db_path=self.db, records=records)
        assets = ["AAPL", "MSFT"]
        prices = self.data.prices.loc["2021-03-19":"2021-09-30", assets]
        strategy = build_agentic_strategy(assets, HYPOTHESIS, weight_fn=callback, name="AgenticResearch")
        with contextlib.redirect_stdout(io.StringIO()):
            result = bt.run(bt.Backtest(strategy, prices), bt.Backtest(build_equal_weight_strategy(assets), prices))
        self.assertIn("AgenticResearch", result.stats)
        self.assertEqual([r.as_of for r in records], [
            date(2021, 3, 19), date(2021, 4, 1), date(2021, 5, 3), date(2021, 6, 1),
            date(2021, 7, 1), date(2021, 8, 2), date(2021, 9, 1),
        ])
        research_records = [r for r in records if r.status == "research"]
        self.assertEqual(len(self.client.calls), len(research_records))
        self.assertEqual(len(research_records), 3)
        for record, context in zip(research_records, self.client.calls):
            self.assertEqual(record.as_of, context.request.as_of)
            self.assertEqual(context.request.hypothesis, HYPOTHESIS)
            self.assertTrue(all(entry.end <= record.as_of for entry in context.evidence.values()))

    def test_invalid_weight_callback_stops_rebalance(self):
        from app.services.bl_backtest.agent_weigh_algo import AgenticViewWeighTarget
        assets = ["AAPL", "MSFT"]
        target = SimpleNamespace(
            temp={"selected": assets}, now=pd.Timestamp("2021-09-30"),
            universe=self.data.prices.loc[:, assets],
        )
        for weights in [
            {"AAPL": 1}, {"AAPL": 0, "MSFT": 0}, {"AAPL": -1, "MSFT": 2},
            {"AAPL": float("nan"), "MSFT": 1}, {"AAPL": "bad", "MSFT": 1},
        ]:
            callback = lambda *args, weights=weights: weights
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                AgenticViewWeighTarget(HYPOTHESIS, weight_fn=callback)(target)

    def test_failed_research_never_falls_back_to_mock(self):
        records = []
        callback = make_research_weight_fn(
            data=self.data, llm_client=self.client, db_path=self.db, records=records,
        )
        self.client.failure = RuntimeError("model failed")
        with self.assertRaisesRegex(RuntimeError, "model failed"):
            callback(
                self.data.prices.loc[:"2021-09-30", self.request.universe],
                self.request.universe, HYPOTHESIS, pd.Timestamp("2021-09-30"),
            )
        self.assertEqual(records, [])

    def test_default_mock_callback_compatibility(self):
        from app.services.bl_backtest.agent_weigh_algo import AgenticViewWeighTarget
        from app.services.bl_backtest.mock_agent import mock_generate_agent_weights

        assets = ["AAPL", "MSFT"]
        window = self.data.prices.loc[:"2021-09-30", assets]
        legacy = mock_generate_agent_weights(window, assets, HYPOTHESIS)
        explicit = mock_generate_agent_weights(window, assets, HYPOTHESIS, pd.Timestamp("2021-09-30"))
        self.assertEqual(legacy, explicit)
        strategy = build_agentic_strategy(assets, HYPOTHESIS)
        self.assertEqual(strategy.name, "AgenticBL")
        target = SimpleNamespace(temp={"selected": assets}, now=window.index[-1], universe=window)
        AgenticViewWeighTarget(HYPOTHESIS)(target)
        self.assertAlmostEqual(sum(target.temp["weights"].values()), 1)

    def test_research_only_cli_uses_processed_context_and_no_bt_run(self):
        from app.services.bl_backtest.run_example import main

        def fake_run(context):
            return run_research(context, llm_client=self.client, db_path=self.db)

        argv = [
            "run_example", "--research-only", "--as-of", "2021-09-30",
            "--universe", "AAPL", "MSFT", "--hypothesis", "Use EPS changes",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch("app.services.bl_backtest.research_graph.run_research", side_effect=fake_run),
            patch("bt.run") as backtest_run,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            main()
        result = json.loads(output.getvalue())
        self.assertEqual(result["context"]["request"]["hypothesis"], "Use EPS changes")
        self.assertEqual(result["stages"], STAGES)
        backtest_run.assert_not_called()

    def test_research_backtest_cli_injects_real_callback(self):
        from app.services.bl_backtest.run_example import main

        original_factory = make_research_weight_fn

        def fake_factory(**kwargs):
            return original_factory(**kwargs, llm_client=self.client, db_path=self.db)

        argv = [
            "run_example", "--research-backtest", "--start-date", "2021-03-19",
            "--end-date", "2021-09-30", "--universe", "AAPL", "MSFT",
            "--hypothesis", "Use EPS changes",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch("app.services.bl_backtest.research_weights.make_research_weight_fn", side_effect=fake_factory),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            main()
        self.assertEqual(len(self.client.calls), 3)
        self.assertTrue(all(c.request.hypothesis == "Use EPS changes" for c in self.client.calls))

    def test_notebook_all_code_cells_execute_offline(self):
        notebook_path = Path(__file__).parent / "app" / "services" / "bl_backtest" / "run_example.ipynb"
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        namespace = {"display": lambda *args: None}
        with patch("plotly.graph_objects.Figure.show"), contextlib.redirect_stdout(io.StringIO()):
            first = True
            for cell in notebook["cells"]:
                if cell["cell_type"] != "code":
                    continue
                exec(compile("".join(cell["source"]), str(notebook_path), "exec"), namespace)
                if first:
                    namespace["LLM_CLIENT"] = self.client
                    namespace["USAGE_DB_PATH"] = self.db
                    first = False
        self.assertGreater(len(namespace["view_rows"]), 0)
        self.assertEqual(len(self.client.calls), 3)


class SharedClientTests(unittest.TestCase):
    def test_opted_in_sampling_parameters_are_forwarded(self):
        client = SimpleNamespace(model="gpt-4.1-mini")
        with patch.object(client, "chat", create=True, return_value="JSON") as chat:
            with tempfile.TemporaryDirectory() as directory:
                chat_and_record(
                    "system", "user", "test", "sampling", llm_client=client,
                    temperature=0.1, max_tokens=456, forward_parameters=True,
                    db_path=Path(directory) / "usage.db",
                )
        self.assertEqual(chat.call_args.kwargs["temperature"], 0.1)
        self.assertEqual(chat.call_args.kwargs["max_tokens"], 456)

    def test_optional_parameter_forwarding_preserves_legacy_clients(self):
        class LegacyClient:
            model = "gpt-4.1-mini"

            def chat(self, system_prompt, user_prompt, schema):
                return "legacy"

        with tempfile.TemporaryDirectory() as directory:
            response = chat_and_record(
                "system", "user", "test", "legacy", llm_client=LegacyClient(),
                db_path=Path(directory) / "usage.db",
            )
        self.assertEqual(response, "legacy")

    def test_schema_parameters_refusal_and_truncation(self):
        with patch("app.services.llm_client.utils.OpenAI") as factory:
            wrapper = OpenAIClientWrapper(api_key="test-key", structured_output=True)
            create = factory.return_value.chat.completions.create
            message = SimpleNamespace(content='{"views":[]}', refusal=None)
            create.return_value = SimpleNamespace(
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=6),
                choices=[SimpleNamespace(message=message, finish_reason="stop")],
            )
            wrapper.chat("system", "user", ViewBatch.model_json_schema(), temperature=0, max_tokens=8000)
            self.assertEqual(create.call_args.kwargs["temperature"], 0)
            self.assertEqual(create.call_args.kwargs["max_tokens"], 8000)
            self.assertTrue(create.call_args.kwargs["response_format"]["json_schema"]["strict"])
            message.refusal = "declined"
            with self.assertRaisesRegex(ValueError, "refused"):
                wrapper.chat("system", "user", ViewBatch.model_json_schema())
            message.refusal = None
            create.return_value.choices[0].finish_reason = "length"
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                wrapper.chat("system", "user", ViewBatch.model_json_schema())


if __name__ == "__main__":
    unittest.main()
