"""Research, independent critique, and synthesis without data-access capabilities."""

import json

from app.services.bl_backtest.schema import CriticBatch, ResearchContext, ViewBatch
from app.services.bl_backtest.agent_utils.research.prompts import (
    RESEARCH_AGENT, SYSTEM_PROMPT, build_user_prompt,
)

CRITIC_AGENT = """
You are a skeptical investment research reviewer.

Review each proposed investment view independently against the supplied evidence.

For every view, determine:

1. Is the directional conclusion actually supported by the evidence?
2. Is the evidence sufficiently material to justify an investment view?
3. Is there contradictory evidence?
4. Is the reasoning confusing correlation, coincidence, or noise with an investment thesis?
5. Is the confidence level justified?
6. Is the view redundant with another proposed view?
7. Should the view be retained, revised, merged, or abandoned?

Classify each view as one of:

SUPPORTED
WEAK
CONTRADICTED
REDUNDANT
UNCERTAIN

Be skeptical. Do not reject a view merely because the evidence is imperfect; investment evidence is inherently uncertain.

If a view is weak or uncertain, explain specifically what would need to change for the view to become stronger.

If the evidence does not support a view, recommend ABANDON rather than attempting to rescue it.

Do not introduce new evidence that was not supplied to you.
"""

SYNTHESIS_AGENT = """
You are the senior investment analyst responsible for synthesizing an initial set of investment views after independent review.

For each proposed view, consider the original reasoning, the critic's assessment, and the underlying evidence.

You may:

- Keep the view unchanged.
- Reduce or increase confidence.
- Reduce the magnitude.
- Revise the rationale.
- Merge redundant views.
- Resolve apparently conflicting evidence.
- Abandon the view entirely.
- Produce a revised view when the criticism identifies a genuine weakness.

Do not revise a view merely to satisfy the critic. Use your own judgment based on the evidence.

When evidence conflicts, determine whether the conflict reflects:
- genuinely opposing signals,
- different investment horizons,
- different aspects of the same security,
- or insufficient evidence to form a conclusion.

When uncertainty cannot reasonably be resolved, prefer lower confidence or abstention.

Do not introduce evidence that was not available in the supplied research context.

Return only the final set of investment views.
There is no required number of views.
"""

CRITIC_OUTPUT_RULES = """
Return JSON matching CriticBatch. Provide exactly one critique for each proposed
view, identified by its zero-based view_index; return [] if no views exist.
Explicitly assess evidence_quality, contradictions, materiality, redundancy,
and confidence_assessment, even if no issue was found. Cite only supplied
evidence IDs belonging to that view's asset or shared macro scope.
Treat proposals as claims to challenge, not established facts. Work independently
from the original author's reasoning; do not use hidden conversations or outside
knowledge. Use only the supplied evidence, without recomputing statistics.
"""

REVISION_OUTPUT_RULES = """
Return JSON matching RevisionOutput, preserving the existing AssetView fields.
You may return zero views. Merge redundant proposals for the same asset into
one view; the single-asset schema cannot represent a multi-asset merged view.
Do not invent evidence IDs, numerical observations, assets outside the universe,
or calculations. Cite supplied evidence only. Preserve direction/magnitude
consistency. Set needs_review=true only if a further independent review could
resolve a remaining weakness; otherwise false. Provide a concise decision
summary. If this is the last permitted cycle, prefer abstention or reduced
conviction for unresolved weaknesses rather than assuming another cycle.
"""


def build_critic_prompt(context: ResearchContext, views: ViewBatch) -> str:
    return json.dumps({
        "context": context.model_dump(mode="json"),
        "proposed_views": views.model_dump(mode="json"),
    })


def build_revision_prompt(
    context: ResearchContext, original: ViewBatch, current: ViewBatch,
    critic: CriticBatch, cycle: int, max_cycles: int,
) -> str:
    return json.dumps({
        "context": context.model_dump(mode="json"),
        "original_views": original.model_dump(mode="json"),
        "proposed_views": current.model_dump(mode="json"),
        "critic": critic.model_dump(mode="json"),
        "cycle": cycle,
        "max_revision_cycles": max_cycles,
    })
