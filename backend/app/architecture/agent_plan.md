# Agentic Black-Litterman Backtest — Research & Implementation Plan

## 1. Main Intent

Build an experimental extension to the existing quantitative-finance agent in which an LLM agent generates investment views for a historical Black-Litterman (BL) backtest.

The research question is:

> Can an agent take structured, point-in-time non-price information, interpret it according to a natural-language research hypothesis, and generate useful, auditable investment views that improve or change a deterministic Black-Litterman portfolio?

The agent should be responsible for **semantic interpretation and heuristic design**, while deterministic tools remain responsible for:

- historical data access;
- statistical calculations;
- temporal integrity;
- BL mathematics;
- portfolio constraints;
- transaction costs;
- backtest accounting;
- performance evaluation.

The first implementation should be deliberately simple and reproducible.

---

## 2. First Experimental Scope

Start with:

- 10–20 liquid US equities;
- monthly rebalancing;
- one simple lateral signal family: **earnings estimate revisions**;
- one-month holding period;
- deterministic BL implementation;
- basic transaction costs;
- simple portfolio constraints;
- comparison against useful baselines.

Do not start with news, analyst-report retrieval, complex macro signals, or unrestricted web search. Those can be added later after the temporal architecture is proven.

### Initial signal

Use changes in consensus EPS estimates over historical horizons, for example:

- 1-month EPS revision;
- 3-month EPS revision;
- optionally 6-month EPS revision.

The simplest deterministic features can include:

- revision magnitude;
- revision direction;
- cross-sectional z-score/percentile;
- persistence;
- acceleration;
- agreement across horizons.

The LLM should not be responsible for calculating these statistics.

---

## 3. Core Experimental Workflow

For every historical rebalance timestamp `T`:

1. Backtest controller establishes immutable `T`.
2. A point-in-time historical snapshot is created.
3. Snapshot exposes only information whose `available_timestamp <= T`.
4. Agent receives:
   - research hypothesis/instructions;
   - security universe;
   - available factor/signal registry;
   - structured statistical evidence retrieved through permitted tools.
5. Agent decides how the supplied evidence should be interpreted.
6. Agent generates candidate investment views and confidence.
7. Candidate views are converted into structured BL inputs.
8. Deterministic validation checks view provenance and validity.
9. Deterministic BL engine produces portfolio weights.
10. Portfolio constraints and transaction costs are applied.
11. Portfolio is held until the next rebalance.
12. Future realized returns are used only by the backtest/evaluation engine.
13. Run produces a complete audit/provenance record.
14. Repeat at the next rebalance timestamp with a fresh agent state.

Conceptually:

    Backtest clock T
          ↓
    Point-in-time snapshot
          ↓
    Historical evidence/tools
          ↓
    Agent interpretation
          ↓
    Investment views
          ↓
    Deterministic BL
          ↓
    Portfolio
          ↓
    Future realized returns
          ↓
    Evaluation

---

## 4. Temporal Integrity Is a Hard System Boundary

Do not rely on an LLM instruction such as "do not use future information."

The temporal firewall must be implemented below the agent.

### Critical rule

For every external information object `x` supplied to the agent:

    available_timestamp(x) <= T

must hold.

`observation_date`, `period_end`, or the economic period described by the data must NOT be used as a substitute for availability time.

Example:

- FY2020 EPS describes an observation period ending in 2020.
- It may only become usable after its publication timestamp in 2021.
- A December 2020 backtest must not see it.

### Point-in-time data should retain at least

- security identifier;
- metric/signal name;
- value;
- observation period;
- available/publication timestamp;
- revision timestamp where applicable;
- source identifier;
- dataset/version identifier;
- content hash where appropriate.

### Historical snapshot

Create the conceptual equivalent of an immutable:

    HistoricalSnapshot(T)

It should define:

- cutoff timestamp;
- permitted datasets;
- dataset versions;
- universe;
- snapshot/run identifier.

The agent should interact with snapshot-scoped data capabilities rather than raw databases.

---

## 5. Agent Responsibilities

The agent should NOT:

- query arbitrary databases;
- decide what the historical cutoff is;
- retrieve future information;
- perform the authoritative BL mathematics;
- calculate future realized returns;
- change backtest accounting;
- silently modify portfolio constraints;
- introduce unavailable factors as factual evidence.

The agent SHOULD be able to:

- interpret a natural-language research hypothesis;
- identify relevant factors from the supplied factor registry;
- select among available evidence;
- request deterministic statistical calculations;
- interpret conflicting or weak evidence;
- decide whether evidence supports a positive, negative, or neutral view;
- determine view strength/magnitude within an explicitly permitted representation;
- assign confidence;
- explain which supplied evidence supports each view;
- remain neutral when evidence is insufficient.

---

## 6. Natural-Language Research Hypothesis

Provide a user-facing text input describing the intended heuristic.

Example:

> Use earnings estimate revisions as the primary signal. Focus on the direction and magnitude of revisions over the past three months. Generate positive views for stocks with materially improving earnings expectations, negative views for materially deteriorating expectations, and remain neutral when the signal is weak or ambiguous. Be more confident when revisions are large and consistent across time. Do not overreact to small one-off revisions.

The agent should translate this into a structured methodology before the backtest is run.

For example:

```json
{
  "signal": "eps_revision",
  "lookbacks": ["1m", "3m"],
  "view_logic": {
    "positive": "materially positive revision",
    "negative": "materially negative revision",
    "neutral": "weak or conflicting evidence"
  },
  "confidence_basis": [
    "magnitude",
    "cross_horizon_consistency",
    "persistence"
  ],
  "confidence_style": "conservative"
}