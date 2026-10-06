"""Offline tests for research DataFrame translation into the existing BL engine."""

import contextlib
import io
import unittest
from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

from app.services.bl_backtest.data_interface.load import load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context
from app.services.bl_backtest.research_bl import generate_bl_allocation
from app.services.bl_backtest.schema import ResearchRequest
from app.services.bl_engine.bl_standalone import market_implied_prior_returns, sample_cov


class ResearchBLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_research_data()
        cls.context = prepare_context(cls.data, ResearchRequest(
            hypothesis="Use EPS revisions", universe=["AAPL", "MSFT", "JPM", "BND"],
            as_of=date(2021, 9, 30),
        ))

    def setUp(self):
        self.views = pd.DataFrame([
            {
                "asset": asset, "direction": direction, "magnitude": magnitude,
                "confidence": confidence, "rationale": "Supplied evidence assessment",
                "evidence_cited": [f"{asset}.eps_change_63"],
            }
            for asset, direction, magnitude, confidence in [
                ("AAPL", "positive", 0.8, 0.7), ("MSFT", "negative", 0.3, 0.6),
                ("JPM", "positive", 0.5, 0.0), ("BND", "neutral", 0.0, 0.8),
            ]
        ])

    def test_real_engine_prior_targets_omega_and_allocation(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = generate_bl_allocation(self.views, self.context, self.data, max_annual_alpha=0.05)
        assets = self.context.request.universe
        prices = self.data.prices.loc[:"2021-09-30", assets]
        cov = sample_cov(prices)
        caps = {a: self.data.metadata["market_caps"][a] for a in assets}
        params = self.data.metadata["model_defaults"]
        prior = market_implied_prior_returns(caps, cov, params["risk_aversion"])
        targets = result["recipe"]["bottom_up_views"]
        self.assertEqual([v["asset"] for v in targets], ["AAPL", "MSFT"])
        self.assertAlmostEqual(targets[0]["expected_return"], prior["AAPL"] + 0.8 * 0.05)
        self.assertAlmostEqual(targets[1]["expected_return"], prior["MSFT"] - 0.3 * 0.05)
        self.assertAlmostEqual(result["Omega"][0, 0], params["tau"] * cov.loc["AAPL", "AAPL"] / 0.7)
        self.assertEqual(result["calibration"]["omitted_assets"], ["JPM", "BND"])
        self.assertEqual(set(result["weights"]), set(assets))
        self.assertAlmostEqual(sum(result["weights"].values()), 1, places=4)
        self.assertTrue(all(0 <= w <= 1 for w in result["weights"].values()))
        self.assertEqual([row["ticker"] for row in result["allocation"]], assets)
        for row in result["allocation"]:
            self.assertAlmostEqual(row["priorWeight"], caps[row["ticker"]] / sum(caps.values()), places=6)
            self.assertAlmostEqual(row["blWeight"], result["weights"][row["ticker"]], places=6)

    def test_all_neutral_returns_existing_equilibrium(self):
        self.views["direction"] = "neutral"
        self.views["magnitude"] = 0.0
        with contextlib.redirect_stdout(io.StringIO()):
            result = generate_bl_allocation(self.views, self.context, self.data, max_annual_alpha=0.05)
        self.assertEqual(result["n_bottom_up_views"], 0)
        for row in result["allocation"]:
            self.assertEqual(row["priorWeight"], row["blWeight"])

    def test_invalid_calibration_and_references_fail(self):
        for alpha in [0, -0.1, float("nan"), float("inf"), True]:
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                generate_bl_allocation(self.views, self.context, self.data, max_annual_alpha=alpha)
        self.views.at[0, "evidence_cited"] = ["fabricated"]
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            generate_bl_allocation(self.views, self.context, self.data, max_annual_alpha=0.05)

    def test_estimation_prices_never_exceed_observation_cutoff(self):
        from app.services.bl_backtest import research_bl

        runner = research_bl.run_bl_recipe
        with patch.object(research_bl, "run_bl_recipe", wraps=runner) as spy:
            with contextlib.redirect_stdout(io.StringIO()):
                generate_bl_allocation(self.views, self.context, self.data, max_annual_alpha=0.05)
        prices = spy.call_args.args[1]
        self.assertLessEqual(prices.index.max().date(), self.context.observation_date)
        self.assertTrue(np.isfinite(prices.to_numpy()).all())


if __name__ == "__main__":
    unittest.main()
