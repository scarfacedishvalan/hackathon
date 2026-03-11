import React, { useState } from 'react';
import type { AgentAudit } from '../types/agentTypes';
import StepTimeline from './StepTimeline';
import './AuditDisplay.css';

function pct(n: number | undefined) {
  if (n == null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

function delta(n: number) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(1)}%`;
}

interface Props {
  audit: AgentAudit;
}

const AuditDisplay: React.FC<Props> = ({ audit }) => {
  const [stepsOpen, setStepsOpen] = useState(false);

  const base = audit.base_result_summary;
  const syn = audit.synthesis;
  const cost = audit.cost_breakdown;

  // Derive final sharpe / return / vol from scenarios_run or base
  const scenariosRun = (audit.scenarios_run ?? {}) as Record<string, any>;
  const scenarioKeys = Object.keys(scenariosRun);
  const lastScenario = scenarioKeys.length
    ? scenariosRun[scenarioKeys[scenarioKeys.length - 1]]
    : null;

  const finalSharpe  = lastScenario?.sharpe       ?? base.sharpe;
  const finalReturn  = lastScenario?.portfolio_return ?? base.portfolio_return;
  const finalVol     = lastScenario?.portfolio_vol    ?? base.portfolio_vol;

  const weightDelta = audit.weight_delta_vs_base ?? {};
  const allAssets = Array.from(
    new Set([
      ...Object.keys(base.weights ?? {}),
      ...Object.keys(weightDelta),
    ])
  ).sort();

  const finalWeights = audit.final_weights ?? base.weights ?? {};

  return (
    <div className="audit-display">
      {/* Header */}
      <div className="audit-header">
        <div className="audit-header__left">
          <span className="audit-thesis">{audit.thesis_name}</span>
          <span className="audit-goal">{audit.goal}</span>
        </div>
        <div className="audit-header__right">
          <span className="audit-meta">{audit.model}</span>
          <span className="audit-meta">{new Date(audit.run_timestamp).toLocaleString()}</span>
          <span className="audit-meta audit-meta--cost">${cost?.total_cost_usd?.toFixed(4)} / {cost?.total_tokens?.toLocaleString()} tok</span>
        </div>
      </div>

      {/* Synthesis */}
      <section className="audit-section">
        <div className="audit-narrative">{syn.narrative}</div>
        {syn.risk_flags?.length ? (
          <div className="risk-flags">
            {syn.risk_flags.map((f, i) => (
              <span key={i} className="risk-chip">⚠ {f}</span>
            ))}
          </div>
        ) : null}
      </section>

      {/* Metrics + Allocation side-by-side */}
      <div className="audit-grid">
        {/* Allocation delta table */}
        <section className="audit-section audit-section--allocation">
          <h3 className="audit-section__title">Allocation</h3>
          <table className="alloc-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Base</th>
                <th>Final</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {allAssets.map(asset => {
                const baseW = base.weights?.[asset] ?? 0;
                const finalW = finalWeights[asset] ?? 0;
                const d = weightDelta[asset] ?? (finalW - baseW);
                return (
                  <tr key={asset}>
                    <td className="alloc-asset">{asset}</td>
                    <td>{pct(baseW)}</td>
                    <td className="alloc-final">{pct(finalW)}</td>
                    <td className={`alloc-delta ${d > 0.001 ? 'alloc-delta--up' : d < -0.001 ? 'alloc-delta--down' : ''}`}>
                      {Math.abs(d) > 0.0001 ? delta(d) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        {/* Metrics */}
        <section className="audit-section audit-section--metrics">
          <h3 className="audit-section__title">Metrics</h3>
          <div className="metrics-grid">
            <MetricRow label="Sharpe"  base={base.sharpe}             final={finalSharpe}  fmt={n => n.toFixed(4)} />
            <MetricRow label="Return"  base={base.portfolio_return}   final={finalReturn}  fmt={n => pct(n)} />
            <MetricRow label="Vol"     base={base.portfolio_vol}      final={finalVol}     fmt={n => pct(n)} />
            <div className="metric-row metric-row--plain">
              <span className="metric-label">LLM calls</span>
              <span className="metric-value">{cost?.steps ?? '—'}</span>
            </div>
            <div className="metric-row metric-row--plain">
              <span className="metric-label">Tool calls</span>
              <span className="metric-value">{audit.steps?.length ?? '—'}</span>
            </div>
            <div className="metric-row metric-row--plain">
              <span className="metric-label">Cost</span>
              <span className="metric-value">${cost?.total_cost_usd?.toFixed(4)}</span>
            </div>
          </div>
        </section>
      </div>

      {/* Collapsible step timeline */}
      <section className="audit-section">
        <button className="steps-toggle" onClick={() => setStepsOpen(o => !o)}>
          <span>{stepsOpen ? '▲' : '▼'} Agent steps</span>
          <span className="steps-toggle__count">{audit.steps?.length ?? 0} tool calls, {cost?.steps ?? 0} LLM calls</span>
        </button>
        {stepsOpen && <StepTimeline steps={audit.steps ?? []} />}
      </section>
    </div>
  );
};

interface MetricRowProps {
  label: string;
  base: number;
  final: number;
  fmt: (n: number) => string;
}

const MetricRow: React.FC<MetricRowProps> = ({ label, base, final, fmt }) => {
  const up = final > base + 0.0001;
  const down = final < base - 0.0001;
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-base">{fmt(base)}</span>
      <span className="metric-arrow">{up ? '▲' : down ? '▼' : '—'}</span>
      <span className={`metric-final ${up ? 'metric--up' : down ? 'metric--down' : ''}`}>{fmt(final)}</span>
    </div>
  );
};

export default AuditDisplay;
