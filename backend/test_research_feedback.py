"""Offline verification of bounded critique/revision; no notebook execution."""

import ast
import contextlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from app.services.bl_backtest.data_interface.load import load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context
from app.services.bl_backtest.research_bl import generate_bl_allocation
from app.services.bl_backtest.research_graph import ONE_SHOT_STAGES, STAGES, build_research_graph
from app.services.bl_backtest.research_weights import views_to_weights
from app.services.bl_backtest.schema import ResearchContext, ResearchRequest, ResearchResult


def proposal(asset="AAPL", confidence=0.8):
    return {
        "asset": asset, "direction": "positive", "magnitude": 0.7,
        "confidence": confidence, "rationale": "Improving supplied EPS evidence.",
        "evidence_cited": [f"{asset}.eps_change_63"],
    }


def critique(index=0, reference="AAPL.eps_change_63"):
    return {
        "view_index": index, "classification": "WEAK", "recommendation": "REVISE",
        "evidence_quality": "Synthetic estimates are limited evidence.",
        "contradictions": "Shorter-horizon EPS revisions may disagree.",
        "materiality": "Check whether the signal is meaningful.",
        "redundancy": "Avoid duplicate same-asset proposals.",
        "confidence_assessment": "Confidence should reflect limitations.",
        "evidence_cited": [reference],
    }


class ScriptedClient:
    model = "gpt-4.1-mini"
    last_prompt_tokens = 10
    last_completion_tokens = 20

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def chat(self, *, system_prompt, user_prompt, schema, temperature, max_tokens):
        self.calls.append((system_prompt, json.loads(user_prompt), schema))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response)


class FeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_research_data()
        cls.context = prepare_context(cls.data, ResearchRequest(
            hypothesis="Use EPS revisions", universe=["AAPL", "MSFT", "JPM", "BND"],
            as_of=date(2021, 9, 30),
        ))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "usage.db"

    def invoke(self, responses, **kwargs):
        client = ScriptedClient(responses)
        graph = build_research_graph(llm_client=client, db_path=self.db, **kwargs)
        return graph.invoke({"context": self.context})["result"], client

    def test_sparse_views_independent_review_and_reduced_confidence(self):
        revised = proposal(confidence=0.3)
        result, client = self.invoke([
            {"views": [proposal()]},
            {"critiques": [critique()]},
            {"views": [revised], "needs_review": False, "summary": "Reduced confidence."},
        ])
        self.assertEqual(result.stages, STAGES)
        self.assertEqual(result.revision_cycles, 1)
        self.assertEqual(len(result.views.views), 1)
        self.assertEqual(result.views.views[0].confidence, 0.3)
        self.assertEqual(result.original_views.views[0].confidence, 0.8)
        self.assertEqual(len(client.calls), 3)
        reviewer = client.calls[1]
        self.assertIn("skeptical", reviewer[0])
        self.assertNotIn("critic", reviewer[1])
        self.assertNotIn("messages", reviewer[1])
        revision_payload = client.calls[2][1]
        self.assertEqual(revision_payload["original_views"]["views"], [proposal()])
        self.assertEqual(revision_payload["critic"]["critiques"], [critique()])
        self.assertEqual(revision_payload["context"], self.context.model_dump(mode="json"))

    def test_two_cycles_then_validation_and_explicit_limit_warning(self):
        result, client = self.invoke([
            {"views": [proposal()]},
            {"critiques": [critique()]},
            {"views": [proposal(confidence=0.5)], "needs_review": True, "summary": "Review changes."},
            {"critiques": [critique()]},
            {"views": [proposal(confidence=0.2)], "needs_review": True, "summary": "Still uncertain."},
        ])
        self.assertEqual(len(client.calls), 5)
        self.assertEqual(result.revision_cycles, 2)
        self.assertTrue(result.revision_limit_reached)
        self.assertTrue(result.warnings)
        self.assertEqual(result.stages, [*STAGES[:5], "critic_agent", "revision_agent", STAGES[-1]])
        self.assertEqual(result.feedback[1].proposed_views.views[0].confidence, 0.5)
        self.assertEqual(client.calls[4][1]["original_views"]["views"], [proposal()])
        self.assertEqual(client.calls[4][1]["cycle"], 2)

    def test_one_cycle_limit_and_config_guard(self):
        result, client = self.invoke([
            {"views": [proposal()]}, {"critiques": [critique()]},
            {"views": [proposal()], "needs_review": True, "summary": "Unresolved."},
        ], max_revision_cycles=1)
        self.assertEqual(len(client.calls), 3)
        self.assertTrue(result.revision_limit_reached)
        for limit in [0, 3, True, 1.5]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                build_research_graph(llm_client=client, max_revision_cycles=limit)

    def test_abandon_all_and_empty_initial_set_are_valid(self):
        for original in [[], [proposal()]]:
            result, client = self.invoke([
                {"views": original},
                {"critiques": [] if not original else [critique()]},
                {"views": [], "needs_review": False, "summary": "Insufficient support; abstain."},
            ])
            self.assertEqual(result.views.views, [])
            self.assertEqual(len(client.calls), 3)
            self.assertEqual(views_to_weights(result.views, universe=["AAPL", "MSFT"]), {"AAPL": 0.5, "MSFT": 0.5})
            with contextlib.redirect_stdout(io.StringIO()):
                allocation = generate_bl_allocation(
                    pd.DataFrame(), result.context, self.data, max_annual_alpha=0.05,
                )
            self.assertEqual(allocation["n_bottom_up_views"], 0)
            self.assertTrue(all(row["priorWeight"] == row["blWeight"] for row in allocation["allocation"]))

    def test_duplicate_proposals_can_be_merged_but_not_left_as_final(self):
        responses = [
            {"views": [proposal(), proposal(confidence=0.6)]},
            {"critiques": [critique(0), critique(1)]},
            {"views": [proposal(confidence=0.5)], "needs_review": False, "summary": "Merged same thesis."},
        ]
        result, _ = self.invoke(responses)
        self.assertEqual(len(result.original_views.views), 2)
        self.assertEqual(len(result.views.views), 1)
        responses[-1]["views"] = [proposal(), proposal()]
        with self.assertRaisesRegex(ValueError, "validate_structured_views"):
            self.invoke(responses)

    def test_fabricated_final_evidence_and_unknown_assets_are_rejected(self):
        for changed in [
            {**proposal(), "evidence_cited": ["invented"]},
            {**proposal(), "evidence_cited": ["MSFT.eps_change_63"]},
            {**proposal(), "asset": "UNKNOWN"},
        ]:
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "validate_structured_views"):
                self.invoke([
                    {"views": [proposal()]}, {"critiques": [critique()]},
                    {"views": [changed], "needs_review": False, "summary": "Revised."},
                ])

    def test_critic_coverage_and_evidence_are_enforced(self):
        for reviews in [[], [critique(0), critique(0)], [critique(1)], [critique(reference="invented")]]:
            with self.subTest(reviews=reviews), self.assertRaisesRegex(ValueError, "critic_agent"):
                self.invoke([{"views": [proposal()]}, {"critiques": reviews}])

    def test_revision_errors_stop_before_portfolio_construction(self):
        for output in [RuntimeError("revision provider failed"), {"views": [proposal()]}]:
            with self.subTest(output=output), self.assertRaises((RuntimeError, ValueError)):
                self.invoke([{"views": [proposal()]}, {"critiques": [critique()]}, output])

    def test_feedback_can_be_disabled_without_another_architecture(self):
        result, client = self.invoke([{"views": [proposal()]}], feedback_enabled=False)
        self.assertEqual(result.stages, ONE_SHOT_STAGES)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result.feedback, [])
        self.assertEqual(result.revision_cycles, 0)

    def test_independently_injected_role_clients_and_repeat_state(self):
        analyst = ScriptedClient([{"views": [proposal()]}, {"views": []}])
        reviewer = ScriptedClient([{"critiques": [critique()]}, {"critiques": []}])
        reviser = ScriptedClient([
            {"views": [proposal(confidence=0.5)], "needs_review": False, "summary": "Keep."},
            {"views": [], "needs_review": False, "summary": "Abstain."},
        ])
        graph = build_research_graph(
            llm_client=analyst, critic_client=reviewer, revision_client=reviser, db_path=self.db,
        )
        for _ in range(2):
            result = graph.invoke({"context": self.context})["result"]
            self.assertEqual(len(result.feedback), 1)
            self.assertEqual(result.revision_cycles, 1)
        self.assertEqual(len(analyst.calls), 2)
        self.assertEqual(len(reviewer.calls), 2)
        self.assertEqual(len(reviser.calls), 2)

    def test_validation_precedes_unchanged_bl_in_composite_graph(self):
        class PortfolioState(TypedDict, total=False):
            context: ResearchContext
            result: ResearchResult
            stages: list[str]
            bl: dict

        client = ScriptedClient([
            {"views": [proposal()]}, {"critiques": [critique()]},
            {"views": [proposal(confidence=0.4)], "needs_review": False, "summary": "Revise."},
        ])
        research = build_research_graph(llm_client=client, db_path=self.db)
        builder = StateGraph(PortfolioState)
        builder.add_node("research_views", research)

        def portfolio(state):
            self.assertEqual(state["result"].stages[-1], "validate_structured_views")
            return {"bl": generate_bl_allocation(
                pd.DataFrame([v.model_dump() for v in state["result"].views.views]),
                state["result"].context, self.data, max_annual_alpha=0.05,
            )}

        builder.add_node("generate_weights_bl", portfolio)
        builder.add_edge(START, "research_views")
        builder.add_edge("research_views", "generate_weights_bl")
        builder.add_edge("generate_weights_bl", END)
        graph = builder.compile()
        diagram = graph.get_graph(xray=True)
        self.assertTrue(any(
            edge.conditional and edge.source.endswith("revision_agent") and edge.target.endswith("critic_agent")
            for edge in diagram.edges
        ))
        with contextlib.redirect_stdout(io.StringIO()):
            state = graph.invoke({"context": self.context})
        self.assertEqual(state["bl"]["n_bottom_up_views"], 1)

    def test_copied_notebook_is_unexecuted_and_syntactically_valid(self):
        path = Path(__file__).parent / "app" / "services" / "bl_backtest" / "research_feedback_walkthrough.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                ast.parse("".join(cell["source"]))
        graph_cell = next(c for c in notebook["cells"] if c["id"] == "build-graph")
        source = "".join(graph_cell["source"])
        self.assertIn("feedback_enabled=True", source)
        self.assertIn("builder.add_edge('research_views', 'generate_weights_bl')", source)


if __name__ == "__main__":
    unittest.main()
