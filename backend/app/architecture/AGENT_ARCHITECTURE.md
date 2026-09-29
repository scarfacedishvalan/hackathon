# BL Agent Orchestrator — Architecture Reference

This document covers the **current ReAct loop implementation** in full detail,
then describes a **LangGraph-based upgrade path** with specific, justified
motivations for the change.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current Implementation — ReAct Loop](#2-current-implementation--react-loop)
   - [Component Map](#21-component-map)
   - [Data & State](#22-data--state)
   - [Control Flow](#23-control-flow)
   - [Tool Catalogue](#24-tool-catalogue)
   - [Goal Constraint Extraction](#25-goal-constraint-extraction)
   - [Audit & Cost Tracking](#26-audit--cost-tracking)
   - [Limitations](#27-limitations)
3. [Proposed Upgrade — LangGraph](#3-proposed-upgrade--langgraph)
   - [Why LangGraph (not just a refactor)](#31-why-langgraph-not-just-a-refactor)
   - [Graph Structure](#32-graph-structure)
   - [State Schema](#33-state-schema)
   - [Node Definitions](#34-node-definitions)
   - [Checkpointing & Resumability](#35-checkpointing--resumability)
   - [Parallel Tool Dispatch](#36-parallel-tool-dispatch)
   - [Streaming to the Frontend](#37-streaming-to-the-frontend)
   - [Human-in-the-Loop Interrupts](#38-human-in-the-loop-interrupts)
   - [Migration Plan](#39-migration-plan)
4. [Benefit Summary](#4-benefit-summary)

---

## 1. System Overview

The BL Agent Orchestrator is an autonomous portfolio analysis system. Given
a Black-Litterman recipe (a JSON description of investor views, model
parameters, and universe constraints) and a natural-language goal, the agent:

1. Parses hard constraints from the goal (e.g. "max 20% per position").
2. Establishes a base BL scenario as a benchmark.
3. Iteratively calls diagnostic and simulation tools to stress-test the recipe.
4. Terminates with a written narrative, risk flags, and a recommended
   portfolio allocation.

The agent is the integration point for the GPT-4o LLM, the BL calculation
engine (`bl_orchestrator.py`), and the tool layer (`bl_agent_tools.py`).

---

## 2. Current Implementation — ReAct Loop

### 2.1 Component Map

```
backend/app/
├── orchestrators/
│   ├── bl_agent_orchestrator.py     ← ReAct loop, public API, audit assembly
│   ├── bl_agent_tools.py            ← Tool schemas (TOOLS), dispatch_tool(), helpers
│   ├── bl_orchestrator.py           ← run_black_litterman() wrapper
│   └── view_orchestrator.py         ← load_recipe() — reads data/bl_recipes/*.json
├── services/
│   ├── llm_client.py                ← chat_with_history(), AgentCostTracker
│   └── price_data/load_data.py      ← load_market_data()
└── data/
    ├── bl_recipes/                  ← Input: recipe JSON files
    ├── agent_audits/                ← Output: full audit JSON per run
    └── agent_costs.db               ← SQLite: per-step token & cost log
```

### 2.2 Data & State

All state in the current implementation is held as **mutable local variables**
inside `run_agent()`. There is no formal state container.

| Variable | Type | Purpose |
|---|---|---|
| `messages` | `list[dict]` | Full OpenAI conversation history (system + user + assistant + tool results) |
| `run_cache` | `dict[str, dict]` | Maps scenario labels to BL result summaries; shared with `dispatch_tool` by reference |
| `steps_log` | `list[dict]` | Ordered record of every tool call, its args, and its result |
| `synthesis` | `dict \| None` | Set when the `synthesise` tool fires; doubles as the termination flag |
| `step_idx` | `int` | Loop counter acting as a step budget guard |
| `goal_mutations` | `dict` | Hard constraints extracted from the goal; injected into every tool dispatch |

**Key coupling**: `run_cache` is passed by reference into `dispatch_tool()`.
This means scenario results written inside the tool layer are immediately
visible to the orchestrator's post-loop summary logic. This is effective but
brittle — there is no locking, and the coupling is implicit.

### 2.3 Control Flow

```
run_agent(thesis_name, goal)
│
├─ load_recipe()
├─ _load_price_data()
├─ _extract_goal_mutations(goal)          ← GPT-4o-mini + regex fallback
├─ run_black_litterman(base recipe)       ← benchmark
│
└─ for step_idx in range(max_steps):      ← ReAct loop
       │
       ├─ chat_with_history(messages, tools=TOOLS)
       │      └─ returns (content, tool_calls)
       │
       ├─ if not tool_calls:
       │      synthesis = {narrative: content}
       │      break                        ← implicit termination
       │
       └─ for tc in tool_calls:           ← SEQUENTIAL dispatch
              │
              ├─ dispatch_tool(tc.name, tc.args, ...)
              ├─ append result to messages
              ├─ append to steps_log
              │
              └─ if tc.name == "synthesise" and result["done"]:
                     synthesis = result
                     break                 ← explicit termination
```

There are **three separate `break` sites** that can end the loop:
- Outer `if synthesis and synthesis.get("done"): break` (after the inner loop)
- Inner `if tool_name == "synthesise" ...` (inside the tool loop)
- The `if not tool_calls` branch (implicit text termination)

Each requires its own guard. Missing or incorrectly ordering any one of them
creates a silent logic error where the agent continues past a valid terminal
state or stops prematurely.

### 2.4 Tool Catalogue

Tools are defined as OpenAI function-calling schemas in `TOOLS` and executed
via `dispatch_tool()`.

**Core Tools**

| Tool | Purpose |
|---|---|
| `get_recipe_summary` | Surfaces recipe structure: universe, views, parameters, constraints |
| `run_bl_scenario` | Runs BL with a named set of mutations; caches result in `run_cache` |
| `run_stress_sweep` | Grid search over one parameter; returns summary table, does **not** cache a named scenario |
| `compare_scenarios` | Diffs two cached scenarios: weight delta + return delta |
| `synthesise` | Terminal tool — accepts narrative, `recommended_weights`, `risk_flags`; sets `done: true` |

**Diagnostic Tools**

| Tool | What it Tests | Implementation |
|---|---|---|
| `view_importance_test` | Each view's contribution — removes views one at a time and measures Sharpe + allocation shift change | Calls `run_black_litterman` N times (once per view) |
| `view_fragility_scan` | How sensitive a view's portfolio impact is to changes in its magnitude | Calls `run_black_litterman` up to 5 times with `_apply_view_override` |
| `factor_shock_scan` | Macro factor sensitivity under varying shock magnitudes | Calls `run_black_litterman` up to 5 times with `_apply_factor_shock_override` |
| `allocation_envelope` | Min/max weight ranges across all cached scenarios | Pure dict computation over `run_cache` |

**Mutation System** (`_apply_mutations`)

All scenario variations go through a single deep-copy + patch function.
Supported mutation keys:

| Key | Effect |
|---|---|
| `drop_views` | Remove named bottom-up views or factor shocks |
| `override_confidence` | Replace view confidence scalars |
| `override_expected_return` | Replace per-asset posterior return targets |
| `set_model_parameters` | Patch `tau`, `risk_aversion`, `risk_free_rate` |
| `scale_factor_shock` | Multiply a factor shock magnitude |
| `weight_bounds` | Set global `[min, max]` per-asset weight limits |

Goal-level constraints (from `_extract_goal_mutations`) are **hard-merged**
into every `run_bl_scenario` call in `dispatch_tool`, meaning the agent cannot
accidentally run a scenario without applying the user's position caps.

### 2.5 Goal Constraint Extraction

The constraint extraction pipeline runs before the ReAct loop:

```
_extract_goal_mutations(goal)
│
├─ GPT-4o-mini call with _CONSTRAINT_EXTRACTION_PROMPT
│   Returns: {"weight_bounds": [0.0, 0.2], "long_only": true}
│
└─ Regex fallback (if LLM fails):
    Matches: "max 20%", "cap of 15%", "no single asset above 25%"
    Returns: {"weight_bounds": [0.0, 0.20]}
```

Parsed constraints are:
1. Injected into the base run (so the benchmark already respects user limits).
2. Injected into the initial user message so the LLM is aware of them.
3. Hard-merged at the `dispatch_tool` level to backstop any LLM compliance failures.

### 2.6 Audit & Cost Tracking

Every run produces two artefacts:

**`data/agent_audits/<audit_id>.json`** — complete record:
```jsonc
{
  "audit_id": "uuid",
  "thesis_name": "...",
  "goal": "...",
  "run_timestamp": "ISO-8601",
  "model": "gpt-4o",
  "base_recipe_snapshot": { /* original recipe */ },
  "base_result_summary": { /* weights, Sharpe, returns */ },
  "steps": [ /* every tool call: name, args, result */ ],
  "mutations_applied": [ /* mutations from run_bl_scenario calls only */ ],
  "scenarios_run": { /* label -> result_summary for non-base scenarios */ },
  "diagnostics": {
    "view_fragility": [...],
    "factor_transmission": [...],
    "view_importance": [...],
    "allocation_envelope": [...]
  },
  "synthesis": { "narrative": "...", "recommended_weights": {}, "risk_flags": [] },
  "final_weights": { /* asset: weight */ },
  "weight_delta_vs_base": { /* asset: delta */ },
  "cost_breakdown": { /* total tokens + USD */ },
  "step_costs": [ /* per-step breakdown */ ]
}
```

**`data/agent_costs.db`** (SQLite) — per-step cost log used by
`AgentCostTracker` for `list_audits()` and `get_audit_cost()` queries.

### 2.7 Limitations

These are the concrete weaknesses of the current implementation, ranked by
operational impact:

#### L1 — No Resumability on Failure *(High Impact)*

A single `run_agent` call makes up to 8 GPT-4o requests plus several
`run_black_litterman` computations. If any step raises an unhandled exception
— network timeout, OpenAI rate limit, or a malformed tool argument — the
entire run is lost. The partial `steps_log` and `run_cache` results are
discarded; the next call starts from step 0. Given GPT-4o costs, a failure at
step 6 wastes roughly 75% of the run's budget.

#### L2 — Sequential Tool Dispatch *(Medium Impact)*

When the LLM returns multiple tool calls in a single response (which it does
for independent diagnostic tools like `view_fragility_scan` and
`factor_shock_scan`), they are dispatched in a `for tc in tool_calls` loop.
Each call to `run_black_litterman` is CPU-bound and takes ~100–500ms. There
is no mechanism here to parallelize them even though they are fully
independent.

#### L3 — No Streaming to the Frontend *(Medium Impact)*

The current API (`run_agent`) is synchronous and blocking. The React frontend
shows a spinner for the entire duration of the run (potentially 30–120
seconds). Diagnostic tool results, which contain valuable intermediate
insights (e.g. "view X is the most important, fragility scan running..."), are
only visible after the full run completes.

#### L4 — Implicit, Fragmented Termination Logic *(Low-Medium Impact)*

As described in §2.3, termination is handled via three separate `break`
conditions plus a sentinel `synthesis` variable. This is an informal state
machine implemented with control flow. Adding a new terminal condition (e.g.
a budget cap, an analyst interrupt) requires finding and updating multiple
locations.

#### L5 — No Human-in-the-Loop *(Low Impact, High Value for Production)*

The agent cannot pause for human input mid-run. For portfolio decisions,
an analyst reviewing the diagnostic results before the synthesis step and
adding context or overriding the agent's direction is a compliance and
quality-of-output concern, not just a feature.

---

## 3. Proposed Upgrade — LangGraph

### 3.1 Why LangGraph (not just a refactor)

A plain refactor of the current code — splitting `run_agent` into smaller
functions, using `asyncio.gather` for tool dispatch — would address L2 and
partially L3 but cannot solve L1, L4, or L5 without reimplementing what
LangGraph already provides:

| Limitation | Plain Refactor Fixes? | LangGraph Fixes? |
|---|---|---|
| L1 — No resumability | No — requires a checkpoint protocol | **Yes** — `SqliteSaver` built in |
| L2 — Sequential dispatch | Yes — `asyncio.gather` | **Yes** — `ToolNode` built in |
| L3 — No streaming | Partial — can add a callback | **Yes** — `.astream_events()` native |
| L4 — Fragmented termination | Partial — can consolidate `if` blocks | **Yes** — edges are the only exit paths |
| L5 — No human interrupt | No — requires external state management | **Yes** — `interrupt_before` built in |

### 3.2 Graph Structure

The current ReAct loop maps directly to a two-node graph:

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │  route = "continue"
  ┌───────────┐  always   ┌────────────┐           │
  │ agent_node │ ────────► │ tools_node │───────────┘
  └───────────┘           └────────────┘
   (LLM call)              (tool dispatch)    route = "end"
                                 │
                                 └──────────────────► END
```

The `route_after_tools` function replaces all three `break` sites:

```python
def route_after_tools(state: AgentState) -> Literal["agent", "__end__"]:
    if state.get("synthesis"):            # synthesise tool was called
        return END
    if state["step_count"] >= state["max_steps"]:  # budget exhausted
        return END
    if not state["messages"][-1].tool_calls:       # LLM produced plain text
        return END
    return "agent"
```

One function. All exits visible in one place. Adding a new exit condition is
adding one `if` branch here.

Full graph construction:

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools=bl_tools))  # parallel dispatch

graph.set_entry_point("agent")
graph.add_edge("agent", "tools")
graph.add_conditional_edges(
    "tools",
    route_after_tools,
    {"agent": "agent", END: END},
)
```

### 3.3 State Schema

The mutable locals from `run_agent()` become a typed, serialisable state
`TypedDict`. This is what gets checkpointed after every node.

```python
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class AgentState(TypedDict):
    # Conversation history — add_messages handles append-only updates
    messages: Annotated[list, add_messages]
    # Shared scenario cache — new entries are merged (not overwritten)
    run_cache: dict[str, dict]
    # Ordered audit trail of tool calls
    steps_log: list[dict]
    # Set by synthesise tool; presence signals termination
    synthesis: dict | None
    # Hard constraints extracted from the goal
    goal_mutations: dict
    # Original recipe (read-only reference)
    base_recipe: dict
    # Iteration counter
    step_count: int
    max_steps: int
    # Run metadata
    audit_id: str
    thesis_name: str
    goal: str
```

**Why this matters**: Because state is a plain dict (not object references),
LangGraph can serialise it to SQLite after each node completes. If the process
dies between the `tools` node and the `agent` node, the state is restored
from the checkpoint and the run continues from exactly that point.

### 3.4 Node Definitions

#### `agent_node`

```python
async def agent_node(state: AgentState) -> dict:
    """Call the LLM with the current conversation history and tools."""
    response = await openai_client.chat.completions.create(
        model=AGENT_MODEL,
        messages=state["messages"],
        tools=TOOLS,
        temperature=0.2,
    )
    # Cost tracking can still write to agent_costs.db here
    return {
        "messages": [response.choices[0].message],
        "step_count": state["step_count"] + 1,
    }
```

The node returns only the **diff** to apply to state — not the full state.
`add_messages` merges the new assistant message into `state["messages"]`.

#### `tools_node` (using `ToolNode`)

LangGraph's built-in `ToolNode` inspects `state["messages"][-1].tool_calls`,
runs all of them (concurrently via `asyncio.gather` if tools are async), and
appends all tool result messages back.

```python
from langgraph.prebuilt import ToolNode

# Each tool is an async Python callable wrapping dispatch_tool
async def run_bl_scenario_tool(label: str, mutations: dict) -> str:
    result = dispatch_tool("run_bl_scenario", {"label": label, "mutations": mutations}, ...)
    return json.dumps(result)

tools_node = ToolNode([
    get_recipe_summary_tool,
    run_bl_scenario_tool,
    run_stress_sweep_tool,
    view_importance_test_tool,
    view_fragility_scan_tool,
    factor_shock_scan_tool,
    allocation_envelope_tool,
    compare_scenarios_tool,
    synthesise_tool,
])
```

The `synthesise_tool` sets `synthesis` in state, which `route_after_tools`
detects and routes to `END`.

### 3.5 Checkpointing & Resumability (fixes L1)

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string(str(AGENT_COSTS_DB)) as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

`AGENT_COSTS_DB` already exists — no new infrastructure. The checkpointer adds
a `checkpoints` table to the existing SQLite file.

**Starting a run:**
```python
config = {"configurable": {"thread_id": audit_id}}
await app.ainvoke(initial_state, config=config)
```

**Resuming after failure:**
```python
# State is restored automatically from the checkpoint
await app.ainvoke(None, config=config)
```

The checkpoint is written after each node completes. A failure mid-`tools_node`
(e.g. during tool 3 of 4) will re-execute only the tools that hadn't completed.
A failure between nodes (network drop between `tools` and `agent`) replays
from the completed checkpoint — the `agent` node runs again without re-running
the tools.

### 3.6 Parallel Tool Dispatch (fixes L2)

The current code:
```python
# Dispatches view_fragility_scan and factor_shock_scan one after the other
for tc in tool_calls:
    tool_result = dispatch_tool(tc.function.name, ...)
```

With `ToolNode` and async tools:
```python
# Both tools run concurrently; total time = max(individual times), not sum
async def view_fragility_scan_tool(...):
    ...  # wraps existing dispatch_tool logic

async def factor_shock_scan_tool(...):
    ...  # wraps existing dispatch_tool logic
```

`run_cache` needs a `threading.Lock` (or `asyncio.Lock`) to guard concurrent
writes, but the `dispatch_tool` logic itself is unchanged. For 5-point scans
that each take ~300ms, this reduces the tool execution phase from ~1.5s to
~0.3s.

### 3.7 Streaming to the Frontend (fixes L3)

LangGraph's `.astream_events()` yields events as they occur:

```python
async for event in app.astream_events(initial_state, config=config, version="v2"):
    match event["event"]:
        case "on_tool_start":
            await websocket.send_json({
                "type": "tool_start",
                "tool": event["name"],
                "step": state["step_count"],
            })
        case "on_tool_end":
            await websocket.send_json({
                "type": "tool_result",
                "tool": event["name"],
                "result": event["data"]["output"],
            })
        case "on_chain_end":
            if event["name"] == "synthesise":
                await websocket.send_json({
                    "type": "synthesis_complete",
                    "data": event["data"]["output"],
                })
```

This means the frontend can display a live timeline of tool calls:
```
[Step 1] get_recipe_summary         ✓  (230ms)
[Step 2] view_importance_test       ✓  (1.2s)  → AAPL most impactful (+0.12 Sharpe)
[Step 3] view_fragility_scan        running...
```

The router endpoint changes from a synchronous POST that blocks for 60s to
a WebSocket that streams incremental updates. The existing audit JSON format
and the `load_audit` / `list_audits` APIs are unchanged.

### 3.8 Human-in-the-Loop Interrupts (fixes L5)

```python
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"],   # pause before each tool execution for review
    # or:
    interrupt_before=["agent"],   # pause after tools, before next LLM call
)
```

A more targeted version: interrupt specifically before synthesis:

```python
def should_interrupt(state: AgentState) -> bool:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls"):
        return any(tc.function.name == "synthesise" for tc in last_msg.tool_calls)
    return False

app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"],
    # Then check should_interrupt in the API layer before calling app.ainvoke again
)
```

The analyst API:
```python
# Run until interrupt
state = await app.ainvoke(initial_state, config=config)

# Analyst reviews state["steps_log"], state["run_cache"]
# Optionally injects additional context into state["messages"]
await app.aupdate_state(config, {"messages": [analyst_message]})

# Resume
final_state = await app.ainvoke(None, config=config)
```

### 3.9 Migration Plan

The migration is designed to leave all tool logic and the BL calculation
engine untouched.

**Phase 1 — State & Graph skeleton** (no behaviour change)
- Define `AgentState` TypedDict mirroring the current local variables.
- Define `agent_node`, `tools_node`, `route_after_tools`.
- Wire up the graph, compile without a checkpointer.
- Verify the existing `run_agent` test suite passes against the new graph.

**Phase 2 — Checkpointing**
- Add `AsyncSqliteSaver` pointing at `AGENT_COSTS_DB`.
- Add a `resume_agent(audit_id)` public function.
- Test failure injection at each step boundary.

**Phase 3 — Parallel dispatch**
- Convert `dispatch_tool` inner functions to `async def`.
- Add `asyncio.Lock` to `run_cache` write sites.
- Verify correctness with concurrent `view_importance_test` + `factor_shock_scan`.

**Phase 4 — Streaming**
- Replace the HTTP POST endpoint with a WebSocket endpoint.
- Wire `.astream_events()` to the WebSocket channel.
- Update the frontend to consume incremental tool events.

**What stays unchanged:**
- `bl_agent_tools.py` — all tool schemas, `dispatch_tool`, `_apply_mutations`
- `bl_orchestrator.py` — BL calculation engine
- `view_orchestrator.py` — recipe loading
- Audit JSON format — `AgentState` maps 1:1 to the same output fields
- `list_audits()` / `load_audit()` — unchanged public API

**New dependencies:**
```
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=0.1.0
```

---

## 4. Benefit Summary

| Concern | Current | With LangGraph | Practical Effect |
|---|---|---|---|
| **Failure recovery** | Full restart from step 0 | Resume from last completed node | Save up to 7 GPT-4o calls on a late-stage failure |
| **Parallel tools** | Sequential `for` loop | `ToolNode` with `asyncio.gather` | Concurrent diagnostic scans; ~5× faster tool phase |
| **Frontend UX** | 60s spinner | Live tool event stream over WebSocket | Analyst sees progress in real time |
| **Termination logic** | 3 separate `break` sites + sentinel flag | Single `route_after_tools` function | One place to add/remove exit conditions |
| **Human review** | Not possible | `interrupt_before` + `aupdate_state` | Analyst can add context or override before synthesis |
| **State visibility** | Mutable local vars, implicit coupling via shared `run_cache` reference | Typed `AgentState` dict, explicit return diffs | Easier to test, snapshot, and debug each node in isolation |
| **New dependencies** | None | `langgraph`, `langgraph-checkpoint-sqlite` | Two packages, both actively maintained by LangChain Inc. |
