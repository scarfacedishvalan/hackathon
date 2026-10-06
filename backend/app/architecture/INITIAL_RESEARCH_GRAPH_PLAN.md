# Initial LangGraph Investment Research Workflow

Status: implemented initial research graph and approved rebalance integration.
The subsequent feedback extension in section 11 supersedes the original
one-call/exact-universe-view assumptions below.
The notebook now processes the hypothesis at eligible monthly rebalances using
the existing `bt` engine, deterministic long-only research-strength tilts, and
explicit equal-weight warm-up records. No new backtest engine.

Subsequent approved extension: the single-date
[research walkthrough](../services/bl_backtest/research_walkthrough.ipynb) now
connects `research_views -> generate_weights_bl -> END` using
[research_bl.py](../services/bl_backtest/research_bl.py) and the existing
application BL recipe runner. Annual view targets equal the market-implied prior
plus signed magnitude times an explicit maximum annual alpha (default 0.05).
Confidence uses the runner's existing uncertainty mapping; neutral and
zero-confidence views are omitted. The output includes the application's
market-cap prior/BL allocation comparison. This illustrative calibration is not
an empirically estimated return forecast. Monthly backtest behavior remains
unchanged; the research graph itself still does not execute BL.

## 1. Goal and scope

Build a small, one-shot LangGraph workflow that accepts a natural-language
research hypothesis, a security universe, and selected historical evidence,
then returns validated, evidence-backed investment views.

The graph itself establishes the research pipeline, not portfolio execution.
The approved integration in section 10 translates its views into research
tilts for the existing backtest example. It does not run Black-Litterman (BL)
or replace the existing recipe stress-testing agent.

This plan is the scope reference for the initial research graph. The broader
[agent plan](./agent_plan.md),
[agentic BL backtest architecture](./AGENTIC_BL_BACKTEST_ARCHITECTURE.md), and
[ReAct agent architecture](./AGENT_ARCHITECTURE.md) remain future/background
references; their tools, temporal firewall, backtest, checkpoints, and portfolio
execution are not prerequisites for this work.

## 2. Repository findings

### Actual evidence sources

Use the existing files in [mock_timeseries](../../data/mock_timeseries/) without
regenerating them or introducing a replacement storage model.

| Source | Existing structure | Observed coverage |
|---|---|---|
| [eps_estimates_revisions.csv](../../data/mock_timeseries/eps_estimates_revisions.csv) | Long form: `date`, `ticker`, `eps_applicable`, `eps_estimate_usd`, `revision_usd`, `revision_pct` | 16,302 rows; 1,254 dates per security |
| [rates_10y.csv](../../data/mock_timeseries/rates_10y.csv) | `date`, `yield_10y_pct`, `change_bp` | 1,254 rows |
| [market_prices.csv](../../data/mock_timeseries/market_prices.csv) | Wide form: `date` plus ticker columns | 1,254 rows |
| [market_returns.csv](../../data/mock_timeseries/market_returns.csv) | Wide form: `date` plus ticker columns | 1,253 rows |

EPS, rates, and prices span 2021-03-19 through 2026-03-17. Returns start on
2021-03-22 because the first price observation has no preceding return.

The universe is AAPL, AMZN, BAC, BND, GLD, GOOGL, JNJ, JPM, MSFT, PG, TSLA,
VNQ, and WMT. BND, GLD, and VNQ have `eps_applicable=False` and intentionally
empty EPS fields. The first EPS revisions and first daily rate change are
also intentionally empty.

The [generator notebook](../../data/generate_mock_timeseries.ipynb) establishes:

- EPS and 10Y yields are reproducible synthetic series, not historical
  consensus estimates or observed Treasury yields.
- Prices are exported from the existing SQLite price history; returns are
  calculated from those prices without filling missing values.
- `revision_pct` and market returns are fractional changes, not percentage
  points: `0.01` means 1%.
- `yield_10y_pct` is in percentage points: `1.6` means a 1.6% yield.
- `change_bp` is the daily yield difference multiplied by 100.
- There is no publication/availability timestamp or EPS fiscal-period field.
  Do not claim point-in-time certification or a particular EPS forecast period.

### Reusable code and conventions

- [market_data.json](../../data/market_data.json) is the universe and metadata
  registry. Reuse
  [load_market_data_raw](../orchestrators/market_data_orchestrator.py) rather
  than copying the universe, sectors, or factor metadata.
- [load_data.py](../services/price_data/load_data.py) loads live application
  price history from SQLite. It is not the loader for these mock CSVs; do not
  call it or fetch Yahoo data in the new research workflow.
- [llm_client](../services/llm_client/__init__.py) exposes `chat_and_record`
  and injectable clients with existing usage tracking.
- [model settings](../services/model_settings/chat_and_record_metadata.py)
  centralize model and operation configuration.
- [news view schema](../services/news_api/view_schema.py) uses Pydantic,
  strict extra-field rejection, and deterministic validation. Its article
  source, categorical confidence, and lack of neutral/magnitude support
  make it unsuitable to reuse unchanged.
- [BL parser schema](../services/bl_llm_parser/output_schema.json) uses
  `asset` and numeric confidence, but expects BL return targets and recipe
  structure rather than research evidence.
- `AssetView` and `ViewBatch` in the older backtest architecture are proposed
  documentation, not implemented models. Use their naming as prior art,
  not as an importable dependency.
- OpenAI, Pydantic, pandas, and NumPy were already declared. The root/backend
  manifests now also declare `langgraph>=1.0,<2`; no direct LangChain model
  wrapper dependency was added.

The shared OpenAI wrapper now supports opt-in `structured_output=True`;
`chat_and_record` supports opt-in `forward_parameters=True` for temperature
and token limits. The graph uses both. Existing callers retain their legacy
defaults and three-argument client compatibility. Research responses still
undergo deterministic Python validation.

## 3. Contracts

### Research request

Use a small Pydantic request model with:

| Field | Meaning |
|---|---|
| `hypothesis` | Nonempty natural-language research instruction |
| `universe` | Nonempty, unique list of registry securities; preserve requested order |
| `as_of` | Optional observation-date cutoff, resolved once before selection |

For the initial implementation, use fixed 21- and 63-observation lookbacks,
explicitly described as approximate one- and three-trading-month windows.
Do not add natural-language window parsing or a signal configuration framework.

If `as_of` is omitted, use the latest date shared by the required CSV date
coverage, not the machine's current date. For a non-observation cutoff, select
the latest observed date on or before it and return both dates. Reject a cutoff
outside dataset coverage instead of silently substituting another period.

### Processed research context

Keep existing DataFrames and CSV columns inside deterministic data preparation.
The graph and LLM receive only a compact, JSON-serializable context:

- Request, resolved observation date, and selected security metadata.
- An evidence map with stable IDs.
- Each evidence entry's asset scope or shared macro scope, metric, value,
  unit, source file/columns, actual start/end dates, and observation count.
- Explicit `available`, `not_applicable`, or `insufficient_history` status.
- Data-quality warnings and synthetic-data labels.

These are boundary/provenance structures, not a new underlying market-data
model. Do not create a database, signal registry, generic provider hierarchy,
or alternate dataset.

### Investment view

Use a dedicated, small `AssetView` model and a `ViewBatch` wrapper. Prefer
`asset` over `ticker` to align with existing BL-facing naming.

| Field | Contract |
|---|---|
| `asset` | One requested security |
| `direction` | `positive`, `negative`, or `neutral` |
| `magnitude` | Finite, unsigned research-strength score in `[0, 1]` |
| `confidence` | Finite numeric score in `[0, 1]` for the evidence-supported assessment |
| `rationale` | Nonempty concise explanation, including uncertainty/conflicting evidence |
| `evidence_cited` | Unique evidence IDs supplied for this asset or shared macro context |

Recommended initial magnitude semantics: a dimensionless conviction/strength
score, **not an expected return**, volatility, or portfolio weight. Direction
carries the sign. Neutral must have magnitude zero; positive/negative must
have magnitude greater than zero. Confidence is distinct from magnitude and
is not a calibrated probability.

This choice avoids inventing an EPS-to-return calibration. A future BL adapter
will need an explicit return horizon, reference basis, calibration policy,
and confidence-to-uncertainty mapping before translating research scores.
Do not equate `magnitude` with BL `expected_return`, or interpret neutral as
an absolute zero-return constraint.

Return exactly one view per requested asset in request order. The result
contains the request, resolved context/evidence map, validated `ViewBatch`,
and warnings, allowing consumers to resolve citations without accessing CSVs.

## 4. Graph architecture

```text
START
  |
  v
prepare_research_context        deterministic context checks/assembly
  |
  v
analyze_available_evidence      one LLM invocation for the full universe
  |
  v
generate_investment_views       deterministic projection into candidate views
  |
  v
validate_structured_views       Pydantic + cross-field/provenance validation
  |
  v
END                            validated research result
```

Use `StateGraph`, a typed state, explicit linear edges, and compilation without
a checkpointer. No `ToolNode`, message-history reducer, conditional retry
edge, agent loop, or agent framework is needed.

### Data-access boundary

The public orchestration entry point first validates the request and invokes
a deterministic evidence-preparation helper outside the graph. It then passes
the processed context into the graph.

The preparation node checks that supplied evidence matches the request,
normalizes prompt-ready context, and surfaces coverage warnings. Graph nodes
never receive dataset paths, raw DataFrames, database connections, or data
access tools. This keeps the future context-injection interface independent
of the current CSV source.

### Minimal graph state

Store only the request, processed context, parsed evidence assessments,
candidate views, and validated result. Node functions return state updates
rather than mutating shared caches. Keep dependencies in the graph-builder
closure, not in serializable state. Each invocation gets fresh state.

### One-shot reasoning

The analysis node makes **one LLM call total**, across the requested universe.
Its structured response contains concise per-asset evidence assessments and
proposed direction, strength, confidence, rationale, and citations.

The generation node deterministically projects those assessments into
candidate `AssetView` records. It does not make a second call, calculate
financial targets, or invent a view missing from the LLM response.

This deliberately keeps the requested analysis/generation boundaries visible
without introducing a second reasoning pass. The intermediate assessments
are concise decision summaries, not requests for hidden chain-of-thought.

The prompt tells the model to interpret only supplied evidence under the
hypothesis, distinguish mock data from real observations, acknowledge
conflicting/missing signals, and avoid causal or predictive claims unsupported
by the context. Treat hypothesis text as user research input, not permission
to override the output contract or fetch outside information.

## 5. Deterministic evidence preparation

Load the four CSVs read-only with pandas and metadata through the canonical
registry loader. Validate required columns, numeric/boolean types, unique
dates or date/ticker pairs, positive prices, and finite populated numeric
values. Sort dates, select the requested assets, and slice before computing
features.

Initial feature set:

| Evidence | Processing |
|---|---|
| EPS | Latest applicable estimate; 21-/63-observation net fractional estimate changes |
| 10Y rates | Latest yield; 21-/63-observation changes in basis points |
| Prices/returns | Latest price; 21-/63-observation cumulative fractional returns |
| Metadata | Asset class and sector; descriptive context, not observed market signals |

For a window of `N` changes, require `N+1` level observations, using endpoint
ratios for EPS and price returns and endpoint yield differences for rates.
Select corresponding `N` supplied daily returns and check that compounding
agrees with the price-derived return within CSV-rounding tolerance. Document
the tolerance and fail on material inconsistency; do not silently switch sources.

Preserve the supplied daily revision/change fields and verify their definitions
against successive levels within a documented rounding tolerance. Do not sum
fractional EPS revisions to calculate a multi-period change.

No rolling regressions, z-scores, factor modeling, inferred return targets,
annualization, news retrieval, or extra signal families in version one.

Missingness rules:

- Preserve intentional first-observation differences and non-applicable EPS.
  Never replace them with zero.
- Mark a feature unavailable when its full lookback cannot be computed;
  do not shorten a window and label it as a complete 21-/63-observation result.
- Unexpected missing/invalid values in required source data are explicit
  preparation errors, not silently filled, dropped, or imputed observations.
- A fund may still receive a view based on rates and price evidence.
- An EPS-only hypothesis with no applicable EPS should yield a neutral
  assessment with an explicit limitation, not invented EPS evidence.

Observation-date filtering is a basic reproducibility boundary, not a
publication-time firewall. Static metadata may describe today's configuration.
The output must state this limitation; no historical-validity claim is made.

## 6. Validation and failure behavior

Deterministic validation checks:

1. Strict JSON/object shapes and Pydantic models; reject unexpected fields.
2. Exact universe coverage: no missing, duplicate, or unrequested assets.
3. Allowed directions, finite numeric scores, ranges, and neutral/magnitude
   consistency. Reject boolean/string substitutions for numeric scores.
4. Nonempty rationale and valid, unique citations.
5. Citation scope: an asset cannot cite another asset's evidence.
6. Non-neutral views cite at least one available numerical evidence entry.
   Metadata alone or unavailable features cannot support a directional view.
7. Neutral views explain weak/conflicting/unavailable evidence and reference
   the supplied coverage or evidence entries where applicable.
8. Source date ranges do not exceed the resolved observation cutoff.

Citation validity proves that references exist and are in scope; it does not
prove the economic correctness of the rationale. Do not describe this as
deterministic verification of LLM reasoning.

Malformed JSON, refusal/empty responses, invalid citations, or a missing view
fail the run explicitly. Do not silently drop records, downgrade invalid
responses to neutral, fabricate defaults, or retry/revise with the LLM.

Reuse existing LLM call tracking for provider failures and token/cost metadata.
Report preparation/parsing/validation errors with their stage and actionable
details to the caller. A provider-success record is not a successful research
run if later validation fails.

## 7. Small implementation footprint

Implemented file ownership:

| File | Responsibility |
|---|---|
| `backend/app/services/bl_backtest/research_graph.py` | Request entry point, graph state, nodes, graph construction, result assembly |
| `backend/app/services/bl_backtest/schema.py` | Request/context boundary models, `AssetView`/`ViewBatch`, deterministic view validation |
| `backend/app/services/bl_backtest/agent_utils/prompts.py` | Research instructions and prompt assembly from processed evidence |
| `backend/app/services/bl_backtest/research_weights.py` | Real rebalance callback, explicit warm-up records, deterministic long-only tilt policy |
| `backend/app/services/llm_client/utils.py` | Reused shared client with opt-in provider schema enforcement and parameter forwarding |
| `backend/app/services/bl_backtest/data_interface/load.py` | Read-only loading of existing CSVs and canonical metadata; source-shape checks |
| `backend/app/services/bl_backtest/data_interface/query.py` | Universe/date selection and cutoff/coverage checks over loaded data |
| `backend/app/services/bl_backtest/data_interface/process.py` | Deterministic features, consistency checks, evidence IDs, provenance, and warnings |
| `backend/app/services/bl_backtest/agent_utils/__init__.py` | Agent utility package initialization only |
| `backend/app/services/bl_backtest/data_interface/__init__.py` | Data interface package initialization only |
| `backend/app/services/bl_backtest/run_example.py` | Default mock, explicit research-only and research-backtest modes |
| `backend/app/services/bl_backtest/run_example.ipynb` | Live hypothesis-driven monthly example and per-rebalance audit tables |
| `backend/test_research_graph.py` | Offline data, graph, validation, and failure tests |

Keep all new workflow code inside the existing
[bl_backtest package](../services/bl_backtest/), rather than introducing a
separate research service or top-level orchestrator. Package placement does
not mean the research graph executes a backtest.

Separate LangChain/LLM agent utilities in `agent_utils/` from dataset access
and processing in `data_interface/`. The graph imports these small functions
and contracts; utility modules do not import or execute the graph. Do not add
generic agent classes or data-provider abstractions.

Reuse the existing injectable `.chat()` boundary and usage recorder directly;
there is no separate research LLM adapter or client module. The shared client
enforces provider JSON-schema output when opted in; deterministic validation
remains authoritative. `agent_utils/` holds prompts and is the home for any
later LangChain-specific helpers, but no additional LangChain wrapper is needed.

Add a `research_agent / analyze_evidence` entry to the existing model metadata.
Reuse the current configured OpenAI model family rather than introducing a new
provider or separate cost database.

Declare `langgraph` in the relevant root/backend dependency manifests during
implementation, preserving their existing formatting/encoding. Resolve a
compatible version against the selected Python and existing package pins then;
do not copy the old architecture's version floor without checking compatibility.
No direct LangChain/OpenAI wrapper package, SQLite checkpointer package, vector
store, queue, or orchestration server is required.

Expose a Python entry point first. No frontend or HTTP route is required to
establish this architecture. Existing BL/backtest API routes are unchanged.
The rebalance hook and mock callback now accept the explicit fourth timestamp
argument described in section 10, preserving default mock behavior.

The updated [run_example.py](../services/bl_backtest/run_example.py)
accepts an explicit `--research-only` mode with hypothesis,
universe, and optional cutoff inputs. With no flag, retain its existing
monthly agentic/equal-weight backtest and statistics output. Research-only
mode calls the new graph once and prints the validated research result; it
must not load the live price database, construct a `bt` strategy, or call
`bt.run`. Keep backtest-only imports/loading inside the backtest execution
path so research-only execution does not require or initialize `bt`.

Do not pass `ViewBatch` into `AgenticViewWeighTarget.weight_fn`: that callback
requires portfolio weights, not research views. The approved
`--research-backtest` mode and notebook inject `make_research_weight_fn`, which
uses deterministic strength tilts instead of BL. Default CLI execution remains
the mock example.

### 7.1 Proposed backend code architecture

The tree below shows implementation ownership. `[NEW]` means a
file/package added in this implementation, `[UPDATE]` means a narrow change to an existing file,
and `[REUSE]` means an existing component used without replacing it.

```text
backend/
|
+-- app/
|   |
|   +-- orchestrators/
|   |   +-- market_data_orchestrator.py                [REUSE]
|   |       +-- load_market_data_raw(): universe/metadata
|   |
|   +-- services/
|   |   |
|   |   +-- bl_backtest/                              [EXISTING PACKAGE]
|   |   |   |
|   |   |   +-- __init__.py                            [EXISTING]
|   |   |   +-- agent_weigh_algo.py                    [UPDATE: timestamp/weight checks]
|   |   |   +-- mock_agent.py                          [UPDATE: optional timestamp]
|   |   |   +-- run_example.py                         [UPDATE]
|   |   |   |   +-- Default: existing backtest behavior
|   |   |   |   +-- --research-only: one graph run, no backtest
|   |   |   |   +-- --research-backtest: live research-strength tilts
|   |   |   +-- run_example.ipynb                      [UPDATE: live research + audits]
|   |   |   |
|   |   |   +-- research_graph.py                      [NEW]
|   |   |   |   +-- Public research entry point
|   |   |   |   +-- Typed state, four nodes, graph builder
|   |   |   |   +-- Validated result assembly
|   |   |   |
|   |   |   +-- schema.py                              [NEW]
|   |   |   |   +-- Request and processed-context models
|   |   |   |   +-- Evidence assessment and view models
|   |   |   |   +-- Deterministic view-validation helper
|   |   |   |
|   |   |   +-- research_weights.py                    [NEW]
|   |   |   |   +-- Real callback, warm-up records, tilt policy
|   |   |   |
|   |   |   +-- agent_utils/                           [NEW]
|   |   |   |   +-- __init__.py
|   |   |   |   +-- prompts.py
|   |   |   |       +-- Instructions and processed-context prompts
|   |   |   |
|   |   |   +-- data_interface/                        [NEW]
|   |   |       +-- __init__.py
|   |   |       +-- load.py
|   |   |       |   +-- Read-only CSV and metadata loading
|   |   |       +-- query.py
|   |   |       |   +-- Universe/cutoff selection and coverage
|   |   |       +-- process.py
|   |   |           +-- Features, consistency checks, provenance
|   |   |
|   |   +-- llm_client/                               [REUSE + OPT-IN UPDATE]
|   |   |   +-- Existing injectable chat boundary
|   |   |   +-- Existing usage/cost recording
|   |   |   +-- Opt-in JSON schema and sampling/token parameters
|   |   |
|   |   +-- model_settings/
|   |       +-- chat_and_record_metadata.py            [UPDATE]
|   |           +-- research_agent / analyze_evidence settings
|   |
|   +-- architecture/
|       +-- INITIAL_RESEARCH_GRAPH_PLAN.md             [THIS PLAN]
|
+-- data/
|   +-- market_data.json                              [REUSE]
|   +-- mock_timeseries/                              [REUSE, READ-ONLY]
|       +-- eps_estimates_revisions.csv
|       +-- rates_10y.csv
|       +-- market_prices.csv
|       +-- market_returns.csv
|
+-- test_research_graph.py                            [NEW]
|   +-- Evidence calculations and source validation
|   +-- Graph order, one-call behavior, and state isolation
|   +-- Output contracts, citations, and explicit failures
|
+-- requirements.txt                                 [UPDATE: LangGraph]
+-- README.md                                        [UPDATE: usage]
```

The repository-root requirements manifest also receives the LangGraph
declaration; it is outside the backend tree above.

Module ownership and execution boundaries:

```text
Caller / run_example.py --research-only
  |
  v
research_graph.py: public entry point
  |
  +----> schema.py: validate request
  |
  +----> data_interface/: prepare selected evidence
  |        |
  |        +----> load.py: read CSVs + canonical registry metadata
  |        +----> query.py: select assets and observation window
  |        +----> process.py: features, checks, evidence references
  |        |
  |        +----> Return processed context only
  |
  v
research_graph.py: compiled LangGraph
  |
  +----> prepare_research_context
  |
  +----> analyze_available_evidence
  |        |
  |        +----> agent_utils/prompts.py: assemble bounded context
  |        +----> Existing llm_client: configured/tracked structured output
  |        +----> One LLM call; no dataset access
  |
  +----> generate_investment_views
  |
  +----> validate_structured_views
  |        |
  |        +----> schema.py: strict models and provenance checks
  |
  v
Validated research result
```

Keep graph orchestration in `bl_backtest/research_graph.py`, agent utilities
in `bl_backtest/agent_utils/`, data loading/querying/processing in
`bl_backtest/data_interface/`, and contracts/validation in
`bl_backtest/schema.py`. The existing example owns mode selection, not graph
or data-processing logic. Do not create separate agent classes or one file
per graph node. No new code belongs in the existing BL engine, API routers,
or frontend for this phase.

## 8. Implementation sequence and acceptance tests

1. **Contracts:** add strict request, evidence, assessment, and view boundaries.
   Test magnitude semantics, missingness, invalid types, and exact asset coverage.
2. **Evidence:** add the read-only load/query/process utilities. Verify actual
   repository shapes/universe and units; test endpoint calculations with small
   hand-checkable fixtures, insufficient history, cutoff resolution,
   non-applicable EPS, duplicate rows, and CSV consistency tolerances.
3. **Graph and agent utilities:** add the four nodes under `bl_backtest` and
   separate prompt/client utilities using the existing tracked client boundary.
   Use an injected fake client for offline tests.
4. **Output/failures:** validate references, return complete provenance, and
   propagate stage-specific failures.
5. **Example and documentation:** add `--research-only` and explicitly selected
   `--research-backtest`, preserving default mock behavior. The notebook uses
   the real callback, processed CSV evidence, editable hypothesis/date settings,
   and per-rebalance audit tables. Verify all notebook cells with a fake client.

Acceptance criteria:

- Actual LangGraph compilation/invocation executes the four nodes in order.
- A successful run makes exactly one reasoning call.
- The fake model sees only selected evidence/context, not raw datasets or
  observations after the cutoff.
- All requested assets appear exactly once, in requested order.
- Direction, strength, confidence, rationale, and references satisfy the contract.
- Intentional EPS missingness for BND/GLD/VNQ survives preparation.
- A valid neutral response is accepted; malformed output is never disguised
  as a valid neutral response.
- Fabricated/out-of-scope citations, non-finite scores, truncation, refusal,
  and provider errors fail explicitly.
- Concurrent or repeated invocations do not share mutable state.
- Tests require no API key, network access, source-data writes, or production
  usage-database writes; inject the client and use temporary tracking storage.
- The research graph and `--research-only` example invoke no BL calculation,
  optimizer, live-price loader/fetcher, or backtest.
- The default example preserves its existing strategy, mock weight callback,
  rebalance cadence, backtest execution, and statistics output. Test dispatch
  with mocked backtest dependencies; do not run a full backtest for this phase.
- Agent utilities cannot access datasets directly; data-interface utilities
  contain no LLM calls. Only processed context crosses into the graph.

Use the repository's available test runner; standard-library `unittest` is
sufficient if no configured runner is present. Run focused tests and Python
analysis/import validation for changed modules during implementation. A live
LLM smoke run is optional and separate from deterministic acceptance tests.

## 9. Expansion seams, not implemented extensions

- Additional research branches can later consume the same processed context.
- Additional signals can add evidence entries without changing view consumers.
- A later synthesis node can compare candidate batches before validation.
- Tools can later sit behind the deterministic evidence boundary.
- A BL adapter can consume validated research views only after return semantics
  and calibration are explicitly defined.
- Portfolio diagnostics and revision edges can be added after that adapter.

Do not create interfaces, placeholder modules, graph branches, or persistence
for these extensions now. The typed boundaries and explicit node stages are
the initial extensibility mechanism.

## 10. Rebalance integration: the `weight_fn` contract

This section specifies the approved integration for the hypothesis-driven
example. Weight generation is outside the research graph. It reuses the existing
backtest engine; no BL execution or new backtest engine is implemented.

### 10.1 Existing hook and proposed signature

[AgenticViewWeighTarget](../services/bl_backtest/agent_weigh_algo.py) already
accepts an injectable `weight_fn`. Its original three-argument callback received
a price window, selected universe, and hypothesis; the default
[mock callback](../services/bl_backtest/mock_agent.py) ignores the hypothesis.

Keep the existing `__call__` rebalance hook and inject the real callback.
The callback contract now includes an explicit
rebalance timestamp rather than inferring it from the last price observation.
All four arguments are positional, matching a precisely typed `Callable`:

```python
WeightFn = Callable[
    [pd.DataFrame, list[str], str, pd.Timestamp],
    dict[str, float],
]

def generate_research_weights(
    price_window: pd.DataFrame,
    universe: list[str],
    hypothesis: str,
    as_of: pd.Timestamp,
) -> dict[str, float]:
    ...
```

The signature above is implemented by the closure returned from
`make_research_weight_fn` in
[research_weights.py](../services/bl_backtest/research_weights.py). The
call site inside `AgenticViewWeighTarget.__call__` is:

```python
weights = self.weight_fn(
    price_window,
    selected,
    self.hypothesis,
    pd.Timestamp(target.now),
)
```

### 10.2 Inputs and ownership

| Input | Supplied by | Contract |
|---|---|---|
| `price_window` | Existing rebalance hook | Historical prices sliced to the configured lookback through `target.now`, with a sorted, unique datetime index and the selected asset columns. No later observations; treat the input as read-only. |
| `universe` | `target.temp["selected"]` | Nonempty, unique registry securities selected for this rebalance, in deterministic order. |
| `hypothesis` | `AgenticViewWeighTarget.hypothesis` | Nonempty research instruction passed unchanged into the research graph on each eligible rebalance. |
| `as_of` | `pd.Timestamp(target.now)` | Actual rebalance timestamp, independent of the latest observation in `price_window`. Controls selection of every evidence source. |

The data interface selects EPS/rate evidence through `as_of` and processes
the supplied price window for price evidence. It must not substitute a
full-history CSV price window for the caller's selected window. The latest
available observation may precede the rebalance date; return that distinction
in provenance rather than changing the rebalance timestamp.

For the current daily datasets, define timestamp-to-observation-date conversion
explicitly and consistently across sources. Reject incompatible timezone or
index conventions instead of silently shifting the cutoff.

Model configuration, the injected LLM client, read-only evidence access, the
chosen view-to-weight policy, and an optional per-rebalance record sink are
dependencies configured once when constructing the callback. They are not
additional positional arguments, mutable global state, or resources created
anew for every rebalance. The callback is synchronous because the existing
`bt` algo invokes it synchronously.

### 10.3 Per-rebalance execution

```text
Existing monthly scheduler
  |
  v
AgenticViewWeighTarget.__call__(target)
  |
  +----> Slice historical price_window through target.now
  |
  v
Injected weight_fn(price_window, universe, hypothesis, as_of)
  |
  +----> data_interface/: select and process evidence through as_of
  |
  +----> research_graph: one hypothesis/evidence reasoning call
  |
  +----> Validate investment views and evidence references
  |
  +----> Agreed deterministic view-to-weight policy
  |
  +----> Validate weights and record date/evidence/views/weights
  |
  v
dict[str, float]
  |
  v
Existing normalization -> target.temp["weights"] -> bt Rebalance()
```

Raw data remains outside the graph and LLM. Each eligible rebalance has fresh
research state and its own selected evidence. Do not reuse a previous date's
views as though the hypothesis were processed again.

### 10.4 Output and selected portfolio policy

Return a mapping containing exactly the selected assets, with finite,
nonnegative weights for the initial long-only example and a strictly positive
total. Explicit zero allocations are permitted. Reject missing/extra assets,
NaN/infinity, negative weights, and an all-zero allocation before the existing
normalization step.

The callback should return normalized weights; retain the algo's existing
normalization defensively. Any portfolio constraints must also hold after
normalization. Do not return `ViewBatch` in place of a weight mapping.

The selected conversion is a deterministic long-only research-strength tilt,
explicitly labeled **non-BL**:

```text
score_i = 1 + 0.5 * direction_sign_i * magnitude_i * confidence_i
weight_i = score_i / sum(scores)
```

This bounds pre-normalization scores to `[0.5, 1.5]`, leaves neutral scores at
1, and never shorts. It does not impose a separate per-position cap or claim
that magnitude represents expected return. BL calibration remains deferred.

The selected warm-up policy is equal weighting whenever any applicable
63-observation-change feature lacks its required 64 level observations.
Record `warmup_equal_weight`, the actual date, hypothesis, weights, and warnings;
make no LLM call. Successful records use `research` and retain the complete
research result. A warm-up baseline is not an LLM-generated result.
Provider or validation failures must remain explicit failures, never silently
fall back to mock weights.

### 10.5 Compatibility and verification

The `WeightFn` alias, call site, default mock callback signature, and injected
callback/tests now use the fourth timestamp argument.
For external three-argument callbacks, document the interface change or provide
an explicit compatibility wrapper; do not catch `TypeError` and retry with
another signature.

Inject the real callback through
[build_agentic_strategy](../services/bl_backtest/run_example.py), rather than
overriding `__call__` or replacing the default mock globally. Retain the existing
mock example and research-only mode. Any live hypothesis-driven backtest mode
must be explicitly selected.

Verify with a fake client and short historical fixture that:

- Each eligible rebalance passes its actual timestamp and unchanged hypothesis.
- Every evidence observation is at or before that rebalance cutoff.
- Exactly one reasoning call occurs per eligible rebalance.
- Resulting weights cover the selected universe and satisfy the chosen policy.
- Warm-up and failure behavior are distinguishable from successful research.
- Existing mock/default example behavior remains intact.

No new backtest engine is necessary: this integration plugs into the existing
monthly scheduling and `bt` rebalance machinery.

### 10.6 Verified execution

The offline suite in [test_research_graph.py](../../test_research_graph.py)
executes the actual compiled graph, monthly `bt` rebalances, and every notebook
code cell with a fake LLM and a temporary usage database. For the default
2021-03-19 through 2021-09-30 range it verifies seven rebalance records: four
warm-up allocations and three research calls. This verifies integration and
output contracts, not live model quality. Live execution requires the configured
model credentials and incurs API usage.

## 11. Bounded independent critique and revision

The shared [research_graph.py](../services/bl_backtest/research_graph.py) now
defaults to the feedback flow below; it is not a separate architecture:

```text
prepare_research_context
  |
analyze_available_evidence
  |
generate_investment_views
  |
critic_agent <---------------------+
  |                               |
revision_agent -------------------+  needs_review and cycles < maximum
  |
validate_structured_views
  |
generate_weights_bl                 existing notebook BL node, unchanged
```

The analyst uses the existing research prompt utilities and emits only
supported proposals. `ViewBatch.views` may be empty or a subset of the requested
universe. Individual `AssetView` fields, finite score bounds, direction rules,
and citation checks are unchanged. The final validator rejects duplicate or
out-of-universe assets but no longer requires a view for every security.
Multiple initial proposals for one security may be synthesized into one final
view; the existing schema cannot encode a multi-asset merged thesis.

The critic is a separate LLM node with an independent skeptical prompt, no
shared conversation history, and the same selected evidence. Structured
`CriticBatch` feedback covers every indexed proposal exactly once and explicitly
assesses evidence quality, contradictions, materiality, redundancy, and
confidence. Critic references are also checked against supplied evidence.

Revision receives immutable original proposals, current candidates, context,
critic feedback, and its cycle budget. It returns existing-schema views,
`needs_review`, and a decision summary. It can keep, modify, merge, lower
confidence, or abandon views, but cannot introduce evidence. Deterministic
final validation catches fabricated/out-of-scope references; it does not
certify the economic truth of prose reasoning.

`max_revision_cycles` is 1 or 2, default 2. One cycle uses three model calls;
two use at most five. Revision can request another critic/revision pass while
the limit permits it. No additional pass occurs after abandoning all views.
If the limit is reached with unresolved review concerns, the result flags
`revision_limit_reached` and warnings before deterministic validation.
Malformed model output or final validation failures still fail explicitly.

`ResearchResult` retains its context/views/stages interface and adds original
views, feedback-cycle records, cycle count, and warning metadata. Existing
client injection and usage recording are reused; critic/revision operations
are configured in the existing model settings. Optional independently injected
role clients are supported. `feedback_enabled=False` retains the original
one-pass path within this same graph builder.

Portfolio construction is unchanged. The BL engine sees only final validated
views, with the existing annual calibration/uncertainty/constraints; an empty
set follows its existing market-equilibrium path. The non-BL callback preserves
its existing baseline score for unviewed securities instead of manufacturing
neutral view records, retaining the full portfolio universe.

The unexecuted
[research_feedback_walkthrough.ipynb](../services/bl_backtest/research_feedback_walkthrough.ipynb)
copies the original single-date walkthrough and adds a printed expanded graph,
explicit cycle limit, and per-cycle review inspection. The source walkthrough
and its saved user outputs are left untouched. Offline tests in
[test_research_feedback.py](../../test_research_feedback.py) verify sparse/empty
views, merging, critic coverage, invented-reference rejection, early termination,
hard cycle limits, state isolation, and validation before unchanged BL execution.
