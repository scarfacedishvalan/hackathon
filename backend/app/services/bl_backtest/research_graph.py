"""Research graph with bounded independent critique and revision."""

from pathlib import Path
from typing import TypeVar, TypedDict

from pydantic import BaseModel

from langgraph.graph import END, START, StateGraph

from app.services.bl_backtest.agent_utils.prompts import (
    CRITIC_AGENT, CRITIC_OUTPUT_RULES, REVISION_OUTPUT_RULES,
    SYNTHESIS_AGENT, build_critic_prompt, build_revision_prompt,
)
from app.services.bl_backtest.agent_utils.research.prompts import (
    RESEARCH_AGENT, SYSTEM_PROMPT, build_user_prompt,
)
from app.services.bl_backtest.schema import (
    CriticBatch, FeedbackCycle, ResearchContext, ResearchResult, RevisionOutput,
    ViewBatch, validate_views,
)
from app.services.llm_client import OpenAIClientWrapper, chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA

STAGES = [
    "prepare_research_context", "analyze_available_evidence",
    "generate_investment_views", "critic_agent", "revision_agent", "validate_structured_views",
]
ONE_SHOT_STAGES = [name for name in STAGES if name not in ("critic_agent", "revision_agent")]
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class ResearchState(TypedDict, total=False):
    context: ResearchContext
    assessments: ViewBatch
    candidates: ViewBatch
    result: ResearchResult
    stages: list[str]
    original_views: ViewBatch
    critic: CriticBatch
    feedback: list[FeedbackCycle]
    revision_cycles: int
    needs_review: bool


def build_research_graph(
    *, llm_client=None, db_path: Path | None = None, feedback_enabled: bool = True,
    max_revision_cycles: int = 2, critic_client=None, revision_client=None,
):
    if type(max_revision_cycles) is not int or not 1 <= max_revision_cycles <= 2:
        raise ValueError("max_revision_cycles must be 1 or 2")
    metadata = CHAT_AND_RECORD_METADATA["research_agent"]

    def configured_client(client, operation: str):
        return client if client is not None else OpenAIClientWrapper(
            model=metadata[operation]["model"], structured_output=True,
        )

    client = configured_client(llm_client, "analyze_evidence")
    reviewer = configured_client(
        critic_client if critic_client is not None else llm_client, "critic",
    ) if feedback_enabled else None
    reviser = configured_client(
        revision_client if revision_client is not None else llm_client, "revise_views",
    ) if feedback_enabled else None

    def call_model(
        stage: str, operation: str, system_prompt: str, user_prompt: str,
        response_model: type[ResponseModel], model_client,
    ) -> ResponseModel:
        response = chat_and_record(
            system_prompt=system_prompt, user_prompt=user_prompt,
            schema=response_model.model_json_schema(), llm_client=model_client,
            db_path=db_path, max_tokens=8000, forward_parameters=True, **metadata[operation],
        )
        try:
            return response_model.model_validate_json(response)
        except ValueError as exc:
            raise ValueError(f"{stage}: invalid structured response: {exc}") from exc

    def prepare_research_context(state: ResearchState):
        context = state["context"]
        if context.observation_date > (context.request.as_of or context.observation_date):
            raise ValueError("prepare_research_context: observation date exceeds cutoff")
        if set(context.metadata) != set(context.request.universe):
            raise ValueError("prepare_research_context: metadata does not match universe")
        for entry in context.evidence.values():
            if entry.end > context.observation_date or entry.start > entry.end:
                raise ValueError("prepare_research_context: invalid evidence date range")
            if entry.asset is not None and entry.asset not in context.request.universe:
                raise ValueError("prepare_research_context: evidence outside universe")
        return {"stages": [STAGES[0]], "revision_cycles": 0, "feedback": [], "needs_review": False}

    def analyze_available_evidence(state: ResearchState):
        assessments = call_model(
            "analyze_available_evidence", "analyze_evidence",
            SYSTEM_PROMPT + "\n" + RESEARCH_AGENT,
            build_user_prompt(state["context"]), ViewBatch, client,
        )
        return {"assessments": assessments, "stages": [*state["stages"], STAGES[1]]}

    def generate_investment_views(state: ResearchState):
        return {
            "candidates": state["assessments"].model_copy(deep=True),
            "original_views": state["assessments"].model_copy(deep=True),
            "stages": [*state["stages"], STAGES[2]],
        }

    def critic_agent(state: ResearchState):
        proposed = state["candidates"]
        critic = call_model(
            "critic_agent", "critic", CRITIC_AGENT + CRITIC_OUTPUT_RULES,
            build_critic_prompt(state["context"], proposed), CriticBatch, reviewer,
        )
        indices = [item.view_index for item in critic.critiques]
        if sorted(indices) != list(range(len(proposed.views))):
            raise ValueError("critic_agent: must review each proposed view exactly once")
        for item in critic.critiques:
            asset = proposed.views[item.view_index].asset
            for reference in item.evidence_cited:
                evidence = state["context"].evidence.get(reference)
                if evidence is None or evidence.asset not in (None, asset):
                    raise ValueError("critic_agent: unknown or out-of-scope evidence reference")
        return {"critic": critic, "stages": [*state["stages"], "critic_agent"]}

    def revision_agent(state: ResearchState):
        cycle = state["revision_cycles"] + 1
        revision = call_model(
            "revision_agent", "revise_views", SYNTHESIS_AGENT + REVISION_OUTPUT_RULES,
            build_revision_prompt(
                state["context"], state["original_views"], state["candidates"],
                state["critic"], cycle, max_revision_cycles,
            ),
            RevisionOutput, reviser,
        )
        record = FeedbackCycle(
            cycle=cycle, proposed_views=state["candidates"].model_copy(deep=True),
            critic=state["critic"], revision=revision,
        )
        return {
            "candidates": ViewBatch(views=revision.views),
            "revision_cycles": cycle, "needs_review": revision.needs_review,
            "feedback": [*state["feedback"], record],
            "stages": [*state["stages"], "revision_agent"],
        }

    def route_after_revision(state: ResearchState):
        if state["needs_review"] and state["candidates"].views and state["revision_cycles"] < max_revision_cycles:
            return "critic_agent"
        return "validate_structured_views"

    def validate_structured_views(state: ResearchState):
        try:
            views = validate_views(state["candidates"], state["context"])
        except ValueError as exc:
            raise ValueError(f"validate_structured_views: {exc}") from exc
        stages = [*state["stages"], "validate_structured_views"]
        limit_reached = state["needs_review"] and state["revision_cycles"] >= max_revision_cycles
        warnings = ["Revision cycle limit reached with unresolved review concerns."] if limit_reached else []
        return {
            "result": ResearchResult(
                context=state["context"], views=views, stages=stages,
                original_views=state["original_views"], feedback=state["feedback"],
                revision_cycles=state["revision_cycles"], revision_limit_reached=limit_reached,
                warnings=warnings,
            ),
            "stages": stages,
        }

    graph = StateGraph(ResearchState)
    for name, node in zip(STAGES, [
        prepare_research_context, analyze_available_evidence,
        generate_investment_views, critic_agent, revision_agent, validate_structured_views,
    ]):
        if feedback_enabled or name not in ("critic_agent", "revision_agent"):
            graph.add_node(name, node)
    for before, after in zip([START, *STAGES[:2]], STAGES[:3]):
        graph.add_edge(before, after)
    if feedback_enabled:
        graph.add_edge("generate_investment_views", "critic_agent")
        graph.add_edge("critic_agent", "revision_agent")
        graph.add_conditional_edges(
            "revision_agent", route_after_revision,
            {"critic_agent": "critic_agent", "validate_structured_views": "validate_structured_views"},
        )
    else:
        graph.add_edge("generate_investment_views", "validate_structured_views")
    graph.add_edge("validate_structured_views", END)
    return graph.compile()


def run_research(
    context: ResearchContext, *, llm_client=None, db_path: Path | None = None,
    feedback_enabled: bool = True, max_revision_cycles: int = 2,
) -> ResearchResult:
    graph = build_research_graph(
        llm_client=llm_client, db_path=db_path,
        feedback_enabled=feedback_enabled, max_revision_cycles=max_revision_cycles,
    )
    return graph.invoke({"context": context})["result"]
