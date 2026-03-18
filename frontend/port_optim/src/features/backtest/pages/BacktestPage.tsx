import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { RecipeDisplay } from '../components/RecipeDisplay';
import type { BacktestMetrics, BacktestTrade, BacktestRecipe, PortfolioRunResult, PortfolioRunRequest } from '../types/backtestTypes';
import { backtestService } from '../services/backtestService';
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

// -- Example inputs -----------------------------------------------------------

const EXAMPLES = [
  'Run SmaCross with fast=10 and slow=30 from 2021-01-01 to 2023-12-31 with $50,000 cash.',
  'BuyAndHold from 2020-01-01 to 2024-01-01 with $25,000 cash.',
  'Test RsiReversion with period 14, lower 30, upper 70, from 2022-01-01 to 2024-01-01 with $15,000 cash.',
  'EmaCross fast=12 slow=26 from 2021-01-01 to 2023-12-31 with $30,000 and 0.1% commission.',
];

// -- Portfolio constants ------------------------------------------------------

const ASSET_COLOURS = ['#60a5fa','#34d399','#f59e0b','#f87171','#a78bfa','#38bdf8','#fb923c','#4ade80'];

const PortfolioResultsPanel: React.FC<{ result: PortfolioRunResult; onReset: () => void }> = ({ result, onReset }) => {
  const assets = Object.keys(result.weights);
  const [assetFilter, setAssetFilter] = useState<string | null>(null);
  const [chartMode, setChartMode] = useState<'portfolio' | 'assets'>('portfolio');

  const colourMap = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    assets.forEach((a, i) => { m[a] = ASSET_COLOURS[i % ASSET_COLOURS.length]; });
    return m;
  }, [assets]);

  const allTrades = useMemo(() => {
    const rows: Array<BacktestTrade & { asset: string }> = [];
    for (const [asset, trades] of Object.entries(result.trades)) {
      trades.forEach(t => rows.push({ ...t, asset }));
    }
    return rows.sort((a, b) => a.entryTime.localeCompare(b.entryTime));
  }, [result.trades]);

  const filteredTrades = assetFilter ? allTrades.filter(t => t.asset === assetFilter) : allTrades;

  return (
    <div className="backtest-results-step">
      {/* Header */}
      <div className="bt-card" style={{ padding: '16px 24px' }}>
        <div className="results-header-row">
          <div className="results-strategy-badge">
            <span style={{ fontSize: 16, fontWeight: 700, color: '#e0e6ed' }}>{result.recipe.strategy_name}</span>
            <span className="badge">{result.recipe.thesis_name}</span>
            <span className="results-period">{assets.length} assets · equal weight</span>
          </div>
          <button className="bt-btn bt-btn--secondary" style={{ padding: '8px 16px', fontSize: 13 }} onClick={onReset}>New Run</button>
        </div>
      </div>

      {/* Weight bar */}
      <div className="pf-weight-bar">
        {assets.map(a => (
          <div key={a} className="pf-weight-segment" style={{ flex: result.weights[a], background: colourMap[a] }} title={`${a}: ${(result.weights[a] * 100).toFixed(1)}%`}>
            {assets.length <= 8 ? a : ''}
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="equity-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <h2>Equity Curve</h2>
          <div className="bt-mode-toggle" style={{ marginBottom: 0 }}>
            <button className={`bt-mode-btn${chartMode === 'portfolio' ? ' active' : ''}`} onClick={() => setChartMode('portfolio')}>Portfolio</button>
            <button className={`bt-mode-btn${chartMode === 'assets' ? ' active' : ''}`} onClick={() => setChartMode('assets')}>Per Asset</button>
          </div>
        </div>
        <p className="chart-subtitle">Initial cash ${result.recipe.cash.toLocaleString()}</p>
        <div className="equity-chart-inner">
          {chartMode === 'portfolio' ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={result.equityCurve} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="pfGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#60a5fa" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={d => d.slice(0, 7)} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="#60a5fa" strokeWidth={2} fill="url(#pfGrad)" dot={false} name="Portfolio" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="date" type="category" allowDuplicatedCategory={false} tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={d => d.slice(0, 7)} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: '#242b33', border: '1px solid #334155', borderRadius: 8, fontSize: 13 }} />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                {assets.map(a => (
                  <Line key={a} data={result.assetCurves[a] ?? []} type="monotone" dataKey="equity" name={a} stroke={colourMap[a]} strokeWidth={1.5} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className="bt-card">
        <h2>Performance Metrics</h2>
        <div className="metrics-grid" style={{ marginTop: 16 }}>
          {buildMetrics(result.metrics).map(m => (
            <MetricCard key={m.label} label={m.label} value={m.value} cls={m.cls} />
          ))}
        </div>
      </div>

      {/* Trades */}
      {allTrades.length > 0 && (
        <div className="trades-table-card">
          <h2>Trade Log</h2>
          <div className="pf-asset-pills">
            <button className={`pf-pill${assetFilter === null ? ' active' : ''}`} onClick={() => setAssetFilter(null)}>All</button>
            {assets.map(a => (
              <button
                key={a}
                className={`pf-pill${assetFilter === a ? ' active' : ''}`}
                style={{ borderColor: colourMap[a], ...(assetFilter === a ? { background: colourMap[a], color: '#fff' } : { color: colourMap[a] }) }}
                onClick={() => setAssetFilter(assetFilter === a ? null : a)}
              >{a}</button>
            ))}
          </div>
          <table className="trades-table">
            <thead>
              <tr>
                <th>Asset</th><th>Entry</th><th>Exit</th>
                <th>Entry $</th><th>Exit $</th><th>PnL</th><th>Return %</th><th>Size</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((t, i) => (
                <tr key={i}>
                  <td><span className="pf-ticker-badge" style={{ background: colourMap[t.asset] + '33', color: colourMap[t.asset] }}>{t.asset}</span></td>
                  <td>{t.entryTime.slice(0, 10)}</td>
                  <td>{t.exitTime.slice(0, 10)}</td>
                  <td>{t.entryPrice != null ? `$${t.entryPrice.toFixed(2)}` : 'N/A'}</td>
                  <td>{t.exitPrice  != null ? `$${t.exitPrice.toFixed(2)}`  : 'N/A'}</td>
                  <td className={t.pnl != null && t.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>{t.pnl != null ? `$${t.pnl.toFixed(2)}` : 'N/A'}</td>
                  <td className={t.returnPct != null && t.returnPct >= 0 ? 'pnl-positive' : 'pnl-negative'}>{t.returnPct != null ? `${t.returnPct.toFixed(2)}%` : 'N/A'}</td>
                  <td>{t.size ?? 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// -- Main Page ----------------------------------------------------------------

const BacktestTabPanel: React.FC = () => {
  const [step, setStep]                 = useState<'input' | 'review' | 'results'>('input');
  const [theses, setTheses]             = useState<string[]>([]);
  const [pfThesis, setPfThesis]         = useState('');
  const [nlInput, setNlInput]           = useState('');
  const [parsedRecipe, setParsedRecipe] = useState<BacktestRecipe | null>(null);
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError]     = useState<string | null>(null);
  const [pfResult, setPfResult]         = useState<PortfolioRunResult | null>(null);
  const [pfLoading, setPfLoading]       = useState(false);
  const [pfError, setPfError]           = useState<string | null>(null);

  useEffect(() => {
    backtestService.listTheses().then(setTheses).catch(() => {});
  }, []);

  const parseStrategy = useCallback(async () => {
    setParseLoading(true); setParseError(null);
    try {
      const recipe = await backtestService.parseStrategy(nlInput);
      setParsedRecipe(recipe);
      setStep('review');
    } catch (e: unknown) {
      setParseError(e instanceof Error ? e.message : 'Parse failed');
    } finally {
      setParseLoading(false);
    }
  }, [nlInput]);

  const runPortfolio = useCallback(async () => {
    if (!parsedRecipe) return;
    setPfLoading(true); setPfError(null);
    try {
      const data = parsedRecipe.data ?? ({} as BacktestRecipe['data']);
      const bt   = parsedRecipe.backtest ?? ({} as BacktestRecipe['backtest']);
      const req: PortfolioRunRequest = {
        thesis_name:     pfThesis,
        strategy_name:   parsedRecipe.strategy_name ?? 'SmaCross',
        strategy_params: parsedRecipe.strategy_params ?? null,
        start:           data.start    ?? null,
        end:             data.end      ?? null,
        cash:            bt.cash       ?? 10_000,
        commission:      bt.commission ?? null,
      };
      const result = await backtestService.runPortfolio(req);
      setPfResult(result);
      setStep('results');
    } catch (e: unknown) {
      setPfError(e instanceof Error ? e.message : 'Run failed');
    } finally {
      setPfLoading(false);
    }
  }, [parsedRecipe, pfThesis]);

  const reset = useCallback(() => {
    setStep('input'); setParsedRecipe(null); setPfResult(null);
    setParseError(null); setPfError(null);
  }, []);

  return (
    <div className="backtest-page">
      <Stepper active={step} />

      {/* Step 1: Input */}
      {step === 'input' && (
        <div className="backtest-input-step">
          <div className="bt-card">
            <h2>Portfolio Strategy</h2>
            <p className="bt-card-subtitle">
              Select a saved thesis and describe the strategy in natural language.
              The AI will parse it into a recipe, then run across all assets in
              the thesis universe with equal weights.
            </p>

            <label className="pf-label">Thesis</label>
            <select
              className="pf-select"
              value={pfThesis}
              onChange={e => setPfThesis(e.target.value)}
              style={{ marginBottom: 16 }}
            >
              <option value="">— select thesis —</option>
              {theses.map(t => <option key={t} value={t}>{t}</option>)}
            </select>

            <label className="pf-label" style={{ marginTop: 8 }}>Strategy Description</label>
            <textarea
              className="bt-textarea"
              placeholder="e.g. Run SmaCross with fast=10 and slow=30 from 2021-01-01 to 2023-12-31 with $50,000 cash."
              value={nlInput}
              onChange={e => setNlInput(e.target.value)}
              rows={5}
              style={{ marginTop: 6 }}
            />
            <div className="example-chips-label" style={{ marginTop: 12 }}>Quick examples:</div>
            <div className="example-chips">
              {EXAMPLES.map(ex => (
                <button key={ex} className="example-chip" onClick={() => setNlInput(ex)}>{ex}</button>
              ))}
            </div>
          </div>

          <div className="bt-action-row">
            {parseError && <span className="bt-error">{parseError}</span>}
            <button
              className="bt-btn bt-btn--primary"
              onClick={parseStrategy}
              disabled={parseLoading || !pfThesis || !nlInput.trim()}
            >
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
              <h2>Ready to Run</h2>
              <p className="bt-card-subtitle">
                Thesis: <strong style={{ color: '#60a5fa' }}>{pfThesis}</strong>
              </p>
              <p style={{ fontSize: 14, color: '#94a3b8', fontStyle: 'italic', margin: 0 }}>"{nlInput}"</p>
            </div>
            <div className="bt-action-row" style={{ justifyContent: 'flex-start', gap: 10 }}>
              <button className="bt-btn bt-btn--secondary" onClick={() => setStep('input')}>Back</button>
              <button className="bt-btn bt-btn--run" onClick={runPortfolio} disabled={pfLoading}>
                {pfLoading ? <><span className="btn-spinner" /> Running...</> : 'Run Portfolio'}
              </button>
            </div>
            {pfError && <p className="bt-error" style={{ marginTop: 10 }}>{pfError}</p>}
          </div>
          <div className="bt-card">
            <h2>Parsed Recipe</h2>
            <p className="bt-card-subtitle">Review the parsed strategy settings before running</p>
            <RecipeDisplay recipe={parsedRecipe} />
          </div>
        </div>
      )}

      {/* Step 3: Results */}
      {step === 'results' && pfResult && (
        <PortfolioResultsPanel result={pfResult} onReset={reset} />
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

      {tabs.map(tab => (
        <div key={tab.id} style={{ display: tab.id === activeId ? 'block' : 'none' }}>
          <BacktestTabPanel />
        </div>
      ))}
    </div>
  );
};