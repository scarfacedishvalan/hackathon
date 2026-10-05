# Initial LangGraph Investment Research Workflow

Status: implementation plan only. No application code or dependencies are
changed by this document.

## 1. Goal and scope

Build a small, one-shot LangGraph workflow that accepts a natural-language
research hypothesis, a security universe, and selected historical evidence,
then returns validated, evidence-backed investment views.

The first version establishes the research pipeline, not portfolio execution.
It will not run Black-Litterman (BL), produce weights, run a backtest, or replace
the existing recipe stress-testing agent.

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
- The inspected root and backend requirement files do not declare LangGraph
  or LangChain. OpenAI, Pydantic, pandas, and NumPy are already declared.

One integration caveat matters: the existing default OpenAI wrapper accepts
`schema` but does not enforce it, and `chat_and_record` does not forward its
temperature/token-limit arguments to the client's `chat` call. Do not assume
that passing these arguments provides enforced structured output or sampling
settings. Configure the research client explicitly and validate its response
in Python. Avoid a broad refactor of existing callers.

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

Proposed files, created only in the later implementation:

| File | Responsibility |
|---|---|
| `backend/app/orchestrators/research_graph.py` | Request entry point, graph state, nodes, graph construction, result assembly |
| `backend/app/services/research/schema.py` | Request/context boundary models and `AssetView`/`ViewBatch` |
| `backend/app/services/research/evidence.py` | Existing CSV loading, checks, selection, deterministic summaries/provenance |
| `backend/app/services/research/__init__.py` | Package initialization only |
| `backend/test_research_graph.py` | Offline data, graph, validation, and failure tests |

Keep the prompt and small configured LLM adapter local to the orchestrator
initially; extract another module only if the implementation genuinely needs it.
Use the existing injectable `.chat()` boundary and usage recorder. The research
adapter can enforce provider JSON-schema output while explicitly configuring
temperature/token limits; deterministic validation remains authoritative.

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
establish this architecture. Leave existing BL/backtest routes and the mock
weight generator untouched.

## 8. Implementation sequence and acceptance tests

1. **Contracts:** add strict request, evidence, assessment, and view boundaries.
   Test magnitude semantics, missingness, invalid types, and exact asset coverage.
2. **Evidence:** add the read-only CSV preparation helper. Verify actual
   repository shapes/universe and units; test endpoint calculations with small
   hand-checkable fixtures, insufficient history, cutoff resolution,
   non-applicable EPS, duplicate rows, and CSV consistency tolerances.
3. **Graph:** add the four nodes and one-shot LLM integration using the existing
   tracked client boundary. Use an injected fake client for offline tests.
4. **Output/failures:** validate references, return complete provenance, and
   propagate stage-specific failures.
5. **Documentation/demo:** update the backend usage documentation and this plan
   with the implemented entry point and a sample validated result.

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
- No BL calculation, optimizer, live-price fetcher, or backtest is invoked.

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
