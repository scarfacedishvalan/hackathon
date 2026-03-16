import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';
import { useState, useCallback } from 'react';
import { useBacktest, BacktestProvider } from '../context/BacktestContext';
import { RecipeDisplay } from '../components/RecipeDisplay';
import type { BacktestMetrics, BacktestTrade } from '../types/backtestTypes';
import './BacktestPage.css';

// -- Stepper ------------------------------------------------------------------

const STEPS = [
  { key: 'input',   label: 'Describe Strategy' },
  { key: 'review',  label: 'Review Recipe' },
  { key: 'results', label: 'Results' },
] as const;

type StepKey = typeof STEPS[number]['key'];

const Stepper: React.FC<{ active: StepKey }> = ({ active }) => {
  const activeIdx = STEPS.findIndex(s => s.key === active);
  return (
    <div className="backtest-stepper">
      {STEPS.map((s, i) => {
        const done    = i < activeIdx;
        const current = i === activeIdx;
        return (
          <React.Fragment key={s.key}>
            {i > 0 && (
              <div className={`step-connector${done ? ' step-connector--done' : ''}`} />
            )}
            <div className="step-item">
              <div className={`step-circle${done ? ' step-circle--done' : current ? ' step-circle--active' : ''}`}>
                {done ? <span>&#10003;</span> : i + 1}
              </div>
              <span className={`step-label${done ? ' step-label--done' : current ? ' step-label--active' : ''}`}>
                {s.label}
              </span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

// -- Metric helpers -----------------------------------------------------------

const fmtPct  = (v: number | null) => v == null ? 'N/A' : `${v.toFixed(2)}%`;
const fmtRat  = (v: number | null) => v == null ? 'N/A' : v.toFixed(2);
const fmtCash = (v: number | null) => v == null ? 'N/A' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

function metricSign(v: number | null, invertPositive = false) {
  if (v == null) return '';
  const positive = invertPositive ? v < 0 : v > 0;
  return positive ? 'metric-value--positive' : v < 0 ? 'metric-value--negative' : '';
}

const MetricCard: React.FC<{ label: string; value: string; cls?: string }> = ({ label, value, cls = '' }) => (
  <div className="metric-card">
    <span className="metric-label">{label}</span>
    <span className={`metric-value ${cls}`}>{value}</span>
  </div>
);

function buildMetrics(m: BacktestMetrics) {
  return [
    { label: 'Total Return',    value: fmtPct(m.returnPct),          cls: metricSign(m.returnPct) },
    { label: 'Ann. Return',     value: fmtPct(m.annualReturnPct),     cls: metricSign(m.annualReturnPct) },
    { label: 'Volatility',      value: fmtPct(m.annualVolatilityPct), cls: '' },
    { label: 'Sharpe Ratio',    value: fmtRat(m.sharpeRatio),         cls: metricSign(m.sharpeRatio) },
    { label: 'Sortino Ratio',   value: fmtRat(m.sortinoRatio),        cls: metricSign(m.sortinoRatio) },
    { label: 'Max Drawdown',    value: fmtPct(m.maxDrawdownPct),      cls: metricSign(m.maxDrawdownPct, true) },
    { label: 'Win Rate',        value: fmtPct(m.winRatePct),          cls: metricSign(m.winRatePct) },
    { label: 'Profit Factor',   value: fmtRat(m.profitFactor),        cls: metricSign(m.profitFactor) },
    { label: 'Equity Final',    value: fmtCash(m.equityFinal),        cls: '' },
    { label: 'Equity Peak',     value: fmtCash(m.equityPeak),         cls: '' },
    { label: 'B&H Return',      value: fmtPct(m.buyHoldReturnPct),    cls: '' },
    { label: '# Trades',        value: m.numTrades != null ? String(m.numTrades) : 'N/A', cls: '' },
  ];
}

// -- Tooltip ------------------------------------------------------------------

interface TPEntry { name: string; value: number; color: string; }
const ChartTooltip: React.FC<{ active?: boolean; label?: string; payload?: TPEntry[] }> = ({ active, label, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#242b33', border: '1px solid #334155', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
      <p style={{ margin: '0 0 4px', fontWeight: 700, color: '#e0e6ed' }}>{label}</p>
      {payload.map(e => (
        <p key={e.name} style={{ margin: '2px 0', color: e.color }}>
          Equity: <strong>${e.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
        </p>
      ))}
    </div>
  );
};

// -- TradesTable --------------------------------------------------------------

const TradesTable: React.FC<{ trades: BacktestTrade[] }> = ({ trades }) => {
  if (!trades.length) return null;
  return (
    <div className="trades-table-card">
      <h2>Trade Log</h2>
      <table className="trades-table">
        <thead>
          <tr>
            <th>Entry</th><th>Exit</th>
            <th>Entry $</th><th>Exit $</th>
            <th>PnL</th><th>Return %</th><th>Size</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => (
            <tr key={i}>
              <td>{t.entryTime.slice(0, 10)}</td>
              <td>{t.exitTime.slice(0, 10)}</td>
              <td>{t.entryPrice != null ? `$${t.entryPrice.toFixed(2)}` : 'N/A'}</td>
              <td>{t.exitPrice  != null ? `$${t.exitPrice.toFixed(2)}`  : 'N/A'}</td>
              <td className={t.pnl != null && t.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                {t.pnl != null ? `$${t.pnl.toFixed(2)}` : 'N/A'}
              </td>
              <td className={t.returnPct != null && t.returnPct >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                {t.returnPct != null ? `${t.returnPct.toFixed(2)}%` : 'N/A'}
              </td>
              <td>{t.size ?? 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// -- Example inputs -----------------------------------------------------------

const EXAMPLES = [
  'Backtest SmaCross on AAPL daily from 2021-01-01 to 2022-12-31 with $10,000 cash.',
  'Run BuyAndHold on SPY daily from 2020-01-01 to 2023-12-31 with $25,000 cash.',
  'Test RsiReversion on MSFT with period 14, lower 30, upper 70, cash $15,000 from 2022-01-01 to 2024-01-01.',
  'SmaCross on GOOG 2019-2023 with $25,000, commission 0.1%, optimize fast=[5,10,15] slow=[20,30,50], maximize Sharpe ratio.',
];

// -- Main Page ----------------------------------------------------------------

const BacktestTabPanel: React.FC = () => {
  const {
    step, nlInput, setNlInput,
    parseLoading, parseError, parseStrategy,
    parsedRecipe,
    runLoading, runError, runRecipe,
    runResult,
    goBack, reset,
  } = useBacktest();

  return (
    <div className="backtest-page">
      <Stepper active={step} />

      {/* Step 1: Input */}
      {step === 'input' && (
        <div className="backtest-input-step">
          <div className="bt-card">
            <h2>Describe Your Strategy</h2>
            <p className="bt-card-subtitle">
              Enter a natural-language description. The AI will parse it into a backtesting recipe.
            </p>
            <textarea
              className="bt-textarea"
              placeholder="e.g. Backtest SmaCross on AAPL daily from 2021-01-01 to 2022-12-31 with $10,000 cash and 0.1% commission."
              value={nlInput}
              onChange={e => setNlInput(e.target.value)}
              rows={5}
            />
            <div className="example-chips-label" style={{ marginTop: 12 }}>Quick examples:</div>
            <div className="example-chips">
              {EXAMPLES.map(ex => (
                <button key={ex} className="example-chip" onClick={() => setNlInput(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <div className="bt-action-row">
            {parseError && <span className="bt-error">{parseError}</span>}
            <button className="bt-btn bt-btn--primary" onClick={parseStrategy} disabled={parseLoading}>
              {parseLoading ? <><span className="btn-spinner" /> Parsing...</> : 'Parse Strategy'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Review */}
      {step === 'review' && parsedRecipe && (
        <div className="backtest-review-step">
          <div>
            <div className="bt-card" style={{ marginBottom: 16 }}>
              <h2>Parsed Input</h2>
              <p className="bt-card-subtitle">Your original description</p>
              <p style={{ fontSize: 14, color: '#94a3b8', fontStyle: 'italic', margin: 0 }}>"{ nlInput}"</p>
            </div>
            <div className="bt-action-row" style={{ justifyContent: 'flex-start', gap: 10 }}>
              <button className="bt-btn bt-btn--secondary" onClick={goBack}>Back</button>
              <button className="bt-btn bt-btn--run" onClick={runRecipe} disabled={runLoading}>
                {runLoading ? <><span className="btn-spinner" /> Running...</> : 'Run Backtest'}
              </button>
            </div>
            {runError && <p className="bt-error" style={{ marginTop: 10 }}>{runError}</p>}
          </div>

          <div className="bt-card">
            <h2>Recipe</h2>
            <p className="bt-card-subtitle">Review the parsed settings before running</p>
            <RecipeDisplay recipe={parsedRecipe} />
          </div>
        </div>
      )}

      {/* Step 3: Results */}
      {step === 'results' && runResult && (
        <div className="backtest-results-step">
          {/* header row */}
          <div className="bt-card" style={{ padding: '16px 24px' }}>
            <div className="results-header-row">
              <div className="results-strategy-badge">
                <span style={{ fontSize: 16, fontWeight: 700, color: '#e0e6ed' }}>
                  {runResult.recipe.strategy_name}
                </span>
                <span className="badge">{runResult.recipe.data?.symbol ?? 'sample'}</span>
                <span className="results-period">
                  {runResult.metrics.start} to {runResult.metrics.end}
                  {runResult.metrics.duration ? ` (${runResult.metrics.duration})` : ''}
                </span>
              </div>
              <button className="bt-btn bt-btn--secondary" style={{ padding: '8px 16px', fontSize: 13 }} onClick={reset}>
                Run Again
              </button>
            </div>
          </div>

          {/* equity curve */}
          <div className="equity-chart-card">
            <h2>Equity Curve</h2>
            <p className="chart-subtitle">Portfolio value over time - initial cash ${runResult.recipe.backtest?.cash?.toLocaleString() ?? 'N/A'}</p>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={runResult.equityCurve} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="btGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#2563eb" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={d => d.slice(0, 7)} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="#2563eb" strokeWidth={2}
                  fill="url(#btGrad)" dot={false} name="Equity" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* metrics grid */}
          <div className="bt-card">
            <h2>Performance Metrics</h2>
            <div className="metrics-grid" style={{ marginTop: 16 }}>
              {buildMetrics(runResult.metrics).map(m => (
                <MetricCard key={m.label} label={m.label} value={m.value} cls={m.cls} />
              ))}
            </div>
          </div>

          {/* trades */}
          {runResult.trades.length > 0 && <TradesTable trades={runResult.trades} />}
        </div>
      )}
    </div>
  );
};

// -- Tab management ----------------------------------------------------------

interface BacktestTab {
  id: string;
  label: string;
}

let tabCounter = 1;

export const BacktestPage: React.FC = () => {
  const [tabs, setTabs] = useState<BacktestTab[]>(() => [
    { id: 'tab-1', label: 'Backtest 1' },
  ]);
  const [activeId, setActiveId] = useState('tab-1');

  const addTab = useCallback(() => {
    tabCounter += 1;
    const id = `tab-${tabCounter}`;
    const label = `Backtest ${tabCounter}`;
    setTabs(prev => [...prev, { id, label }]);
    setActiveId(id);
  }, []);

  const closeTab = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setTabs(prev => {
      if (prev.length === 1) return prev; // keep at least one
      const next = prev.filter(t => t.id !== id);
      if (activeId === id) {
        // activate the neighbour
        const idx = prev.findIndex(t => t.id === id);
        setActiveId(next[Math.max(0, idx - 1)].id);
      }
      return next;
    });
  }, [activeId]);

  return (
    <div className="backtest-tabs-root">
      {/* subtab strip */}
      <div className="bt-subtabs">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`bt-subtab${tab.id === activeId ? ' bt-subtab--active' : ''}`}
            onClick={() => setActiveId(tab.id)}
          >
            <span className="bt-subtab-label">{tab.label}</span>
            {tabs.length > 1 && (
              <button
                className="bt-subtab-close"
                onClick={e => closeTab(tab.id, e)}
                title="Close tab"
              >
                &#10005;
              </button>
            )}
          </div>
        ))}
        <button className="bt-subtab-add" onClick={addTab} title="New backtest">
          &#43;
        </button>
      </div>

      {/* one provider+panel per tab; key ensures isolated state */}
      {tabs.map(tab => (
        <div key={tab.id} style={{ display: tab.id === activeId ? 'block' : 'none' }}>
          <BacktestProvider>
            <BacktestTabPanel />
          </BacktestProvider>
        </div>
      ))}
    </div>
  );
};