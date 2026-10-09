"""Static notebook and offline tool-loop tests; no notebook/kernel or API execution."""

import ast
import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.services.bl_backtest.agent_utils.research import make_research_tools
from app.services.bl_backtest.data_interface.load import load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context
from app.services.bl_backtest.schema import AssetView, ResearchRequest, ViewBatch, validate_views

NOTEBOOK = Path(__file__).parent / "app" / "services" / "bl_backtest" / "agent_utils" / "research" / "tool_agent_walkthrough.ipynb"


class FakeModel:
    def __init__(self, responses, batch):
        self.responses = iter(responses)
        self.batch = batch
        self.bindings = []
        self.final_messages = None
        self.tool_messages = None

    def bind_tools(self, tools, **kwargs):
        self.bindings.append(kwargs)
        return self

    def invoke(self, messages):
        self.tool_messages = list(messages)
        return next(self.responses)

    def with_structured_output(self, schema, **kwargs):
        parent = self

        class FinalModel:
            def invoke(self, messages):
                parent.final_messages = messages
                return parent.batch

        return FinalModel()


class ToolNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.context = prepare_context(load_research_data(), ResearchRequest(
            hypothesis="Compare EPS revisions", universe=["AAPL", "MSFT"],
            as_of=date(2026, 3, 17),
        ))
        cls.tools = [
            StructuredTool.from_function(func=func, name=name)
            for name, func in make_research_tools(cls.context).items()
        ]

    def runner(self):
        node = next(
            node for cell in self.notebook["cells"] if cell["cell_type"] == "code"
            for node in ast.parse("".join(cell["source"])).body
            if isinstance(node, ast.FunctionDef) and node.name == "run_tool_research"
        )
        namespace = {
            "json": json, "context": self.context, "request": self.context.request,
            "tools": self.tools, "tools_by_name": {tool.name: tool for tool in self.tools},
            "MAX_TOOL_ROUNDS": 4, "MAX_CALLS_PER_ROUND": 8,
            "TOOL_SYSTEM_PROMPT": "Test", "ViewBatch": ViewBatch,
            "HumanMessage": HumanMessage, "SystemMessage": SystemMessage,
            "ToolMessage": ToolMessage, "validate_views": validate_views,
            "ValidationError": ValidationError,
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(NOTEBOOK), "exec"), namespace)
        return namespace["run_tool_research"]

    def call(self, name="compare_signals", args=None):
        return AIMessage(content="", tool_calls=[{
            "name": name, "args": args or {"assets": ["AAPL", "MSFT"], "signal": "eps", "lookback": 63},
            "id": "call_test", "type": "tool_call",
        }])

    def batch(self, reference="AAPL.eps_change_63"):
        return ViewBatch(views=[AssetView(
            asset="AAPL", direction="positive", magnitude=0.2, confidence=0.3,
            rationale="Illustrative test view", evidence_cited=[reference],
        )])

    def test_notebook_syntax_preserving_user_execution_outputs(self):
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))

    def test_real_chatopenai_binding_and_tool_schemas_without_network(self):
        llm = ChatOpenAI(model="gpt-4.1-mini", api_key="offline-test-not-a-secret")
        bound = llm.bind_tools(self.tools, tool_choice="required")
        self.assertEqual(len(bound.kwargs["tools"]), 3)
        self.assertEqual(bound.kwargs["tool_choice"], "required")
        for tool in self.tools:
            json.dumps(tool.args)
        structured = llm.with_structured_output(ViewBatch, method="json_schema")
        self.assertIsNotNone(structured)

    def test_calls_printed_tool_response_ids_and_final_validation(self):
        model = FakeModel([self.call(), AIMessage(content="Enough evidence")], self.batch())
        with redirect_stdout(io.StringIO()) as output:
            views, trace = self.runner()(model)
        self.assertEqual(views, self.batch())
        self.assertEqual(len(trace), 1)
        self.assertIn("TOOL CALL", output.getvalue())
        self.assertIn("TOOL RESULT", output.getvalue())
        self.assertEqual(model.bindings, [{}, {"tool_choice": "required"}])
        results = [msg for msg in model.tool_messages if isinstance(msg, ToolMessage)]
        self.assertEqual(results[0].tool_call_id, "call_test")
        final_input = json.loads(model.final_messages[-1].content)
        self.assertEqual(final_input["allowed_evidence_ids"], [
            "AAPL.eps_change_63", "MSFT.eps_change_63",
        ])
        self.assertNotIn("evidence_catalog", final_input)
        self.assertNotIn("AAPL.return_63", final_input["retrieved_context"]["evidence"])

    def test_unretrieved_citation_is_rejected(self):
        model = FakeModel([self.call(), AIMessage(content="Done")], self.batch("AAPL.return_63"))
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "unknown evidence"):
            self.runner()(model)

    def test_tool_round_budget_still_validates_final_output(self):
        model = FakeModel([self.call()] * 4, ViewBatch(views=[]))
        with redirect_stdout(io.StringIO()) as output:
            views, trace = self.runner()(model)
        self.assertEqual(len(trace), 4)
        self.assertEqual(views.views, [])
        self.assertIn("limit reached", output.getvalue())

    def test_unknown_tool_and_outside_universe_stop_explicitly(self):
        for call in [
            self.call("unknown"),
            self.call("query_evidence", {"asset": "JPM"}),
            AIMessage(content="No evidence retrieved"),
        ]:
            with self.subTest(call=call), redirect_stdout(io.StringIO()), self.assertRaises((ValueError, RuntimeError)):
                self.runner()(FakeModel([call, AIMessage(content="Done")], ViewBatch(views=[])))

    def test_null_macro_asset_is_reported_then_corrected(self):
        invalid = self.call("query_evidence", {
            "asset": None, "metrics": ["yield_10y_change_21", "yield_10y_change_63"],
        })
        corrected = self.call("query_evidence", {
            "asset": "AAPL", "include_macro": True,
            "metrics": ["yield_10y_change_21", "yield_10y_change_63"],
        })
        corrected.tool_calls[0]["id"] = "call_corrected"
        model = FakeModel(
            [invalid, corrected, AIMessage(content="Reviewed macro evidence")],
            self.batch("macro.yield_10y_change_63"),
        )
        with redirect_stdout(io.StringIO()) as output:
            views, trace = self.runner()(model)
        self.assertEqual(len(views.views), 1)
        self.assertEqual(len(trace), 2)
        self.assertIn("TOOL ERROR", output.getvalue())
        self.assertIn("error", trace[0])
        self.assertEqual(set(trace[1]["result"]["evidence"]), {
            "macro.yield_10y_change_21", "macro.yield_10y_change_63",
        })
        messages = [msg for msg in model.tool_messages if isinstance(msg, ToolMessage)]
        self.assertEqual([msg.status for msg in messages], ["error", "success"])
        self.assertEqual([msg.tool_call_id for msg in messages], ["call_test", "call_corrected"])

    def test_invalid_arguments_exhaust_budget_without_synthesis(self):
        model = FakeModel([self.call("query_evidence", {"asset": None})] * 4, ViewBatch(views=[]))
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "No evidence"):
            self.runner()(model)
        self.assertIsNone(model.final_messages)

    def oversized_batch(self):
        return AIMessage(content="", tool_calls=[
            {
                "name": "query_evidence", "args": {"asset": "AAPL"},
                "id": f"call_overflow_{index}", "type": "tool_call",
            }
            for index in range(9)
        ])

    def test_oversized_batch_is_rejected_then_smaller_batch_succeeds(self):
        model = FakeModel([
            self.oversized_batch(), self.call(), AIMessage(content="Done"),
        ], self.batch())
        with redirect_stdout(io.StringIO()) as output:
            views, trace = self.runner()(model)
        self.assertEqual(views, self.batch())
        self.assertEqual(len(trace), 10)
        self.assertTrue(all("error" in entry for entry in trace[:9]))
        self.assertIn("result", trace[-1])
        self.assertIn("TOOL BUDGET ERROR", output.getvalue())
        messages = [msg for msg in model.tool_messages if isinstance(msg, ToolMessage)]
        self.assertEqual(len(messages), 10)
        self.assertEqual([msg.status for msg in messages], ["error"] * 9 + ["success"])
        self.assertEqual([msg.tool_call_id for msg in messages[:9]], [
            f"call_overflow_{index}" for index in range(9)
        ])

    def test_oversized_batches_exhaust_rounds_without_execution_or_synthesis(self):
        model = FakeModel([self.oversized_batch()] * 4, ViewBatch(views=[]))
        with redirect_stdout(io.StringIO()) as output, self.assertRaisesRegex(RuntimeError, "No evidence"):
            self.runner()(model)
        self.assertNotIn("TOOL RESULT:", output.getvalue())
        self.assertIsNone(model.final_messages)


if __name__ == "__main__":
    unittest.main()
