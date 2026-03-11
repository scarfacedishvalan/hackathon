import React, { useState } from 'react';
import type { AgentAudit } from '../types/agentTypes';
import StepTimeline from './StepTimeline';
import './AuditDisplay.css';

/** Render a string that may contain **bold**, *italic*, and `- bullet` lines as JSX. */
function renderMd(text: string): React.ReactNode {
  // Split into paragraphs / bullet lines
  const lines = text.split(/\n+/);
  return (
    <>
      {lines.map((line, li) => {
        const isBullet = /^\s*[-*]\s/.test(line);
        const content = parseBoldItalic(isBullet ? line.replace(/^\s*[-*]\s/, '') : line);
        if (isBullet) {
          return <li key={li} style={{ marginLeft: 20, marginBottom: 4 }}>{content}</li>;
        }
        return line.trim() ? <p key={li} style={{ margin: '0 0 8px' }}>{content}</p> : null;
      })}
    </>
  );
}

/** Split a line on **bold** and *italic* markers into React nodes. */
function parseBoldItalic(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Pattern: **bold** or *italic*
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[0].startsWith('**')) {
      parts.push(<strong key={key++}>{m[2]}</strong>);
    } else {
      parts.push(<em key={key++}>{m[3]}</em>);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function pct(n: number | undefined) {
  if (n == null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

function deltaPct(n: number) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(1)}%`;
}

function deltaFixed(n: number, places = 3) {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(places)}`;
}

interface Props { audit: AgentAudit }

const AuditDisplay: React.FC<Props> = ({ audit }) => {
  const [stepsOpen, setStepsOpen] = useState(false);

  const base = audit.base_result_summary;
  const syn  = audit.synthesis;

  // Derive final metrics from last scenario or fall back to base
  const scenariosRun  = ((audit as any).scenarios_run ?? {}) as Record<string, any>;
  const scenarioKeys  = Object.keys(scenariosRun);
  const lastScenario  = scenarioKeys.length
    ? scenariosRun[scenarioKeys[scenarioKeys.length - 1]]
    : null;

  const finalSharpe = lastScenario?.sharpe            ?? base.sharpe;
  const finalReturn = lastScenario?.portfolio_return  ?? base.portfolio_return;
  const finalVol    = lastScenario?.portfolio_vol     ?? base.portfolio_vol;

  const weightDelta  = audit.weight_delta_vs_base ?? {};
  const finalWeights = audit.final_weights ?? base.weights ?? {};
  const allAssets    = Array.from(
    new Set([...Object.keys(base.weights ?? {}), ...Object.keys(weightDelta)])
  ).sort();

  const stepCount = audit.steps?.length ?? 0;

  return (
    <div className="audit-display">

      {/* ── Header ── */}
      <div className="audit-header">
        <div className="audit-header__main">
          <span className="audit-thesis-badge">{audit.thesis_name}</span>
          <p className="audit-goal">{audit.goal}</p>
        </div>
        <div className="audit-header__meta">
          <span className="meta-chip">{audit.model}</span>
          <span className="meta-chip">{new Date(audit.run_timestamp).toLocaleString()}</span>
        </div>
      </div>

      {/* ── Narrative + Insight Chips ── */}
      <section className="audit-section">
        <div className="narrative-block">{renderMd(syn.narrative)}</div>
        {syn.risk_flags?.length ? (
          <div className="insights-row">
            {syn.risk_flags.map((f, i) => (
              <div key={i} className="insight-card insight-card--warning">
                <span className="insight-icon">⚠</span>
                <div className="insight-body">
                  <span className="insight-title">{parseBoldItalic(f)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {/* ── Allocation Table ── */}
      <section className="audit-section">
        <h3 className="section-title">Allocation</h3>
        <div className="alloc-table-wrap">
          <table className="alloc-table">
            <colgroup>
              <col className="col-asset" />
              <col className="col-num" />
              <col className="col-num" />
              <col className="col-num" />
            </colgroup>
            <thead>
              <tr>
                <th className="th-asset">Asset</th>
                <th className="th-num">Base</th>
                <th className="th-num">Final</th>
                <th className="th-num">Delta</th>
              </tr>
            </thead>
            <tbody>
              {allAssets.map(asset => {
                const baseW  = base.weights?.[asset] ?? 0;
                const finalW = finalWeights[asset]   ?? 0;
                const d      = weightDelta[asset]    ?? (finalW - baseW);
                const upCls  = d >  0.001 ? 'val--positive' : '';
                const dnCls  = d < -0.001 ? 'val--negative' : '';
                return (
                  <tr key={asset}>
                    <td className="alloc-asset">{asset}</td>
                    <td className="alloc-num">{pct(baseW)}</td>
                    <td className="alloc-num">{pct(finalW)}</td>
                    <td className={`alloc-num alloc-delta ${upCls || dnCls || 'delta-neutral'}`}>
                      {Math.abs(d) > 0.0001 ? deltaPct(d) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Metric Stat Cards ── */}
      <section className="audit-section">
        <h3 className="section-title">Metrics</h3>
        <div className="metrics-row">
          <MetricCard
            label="Sharpe"
            base={base.sharpe}
            final={finalSharpe}
            fmt={n => n.toFixed(3)}
            deltaFmt={n => deltaFixed(n, 3)}
            invertGood={false}
          />
          <MetricCard
            label="Return"
            base={base.portfolio_return}
            final={finalReturn}
            fmt={n => pct(n)}
            deltaFmt={n => deltaPct(n)}
            invertGood={false}
          />
          <MetricCard
            label="Volatility"
            base={base.portfolio_vol}
            final={finalVol}
            fmt={n => pct(n)}
            deltaFmt={n => deltaPct(n)}
            invertGood={true}
          />
        </div>
      </section>

      {/* ── Agent Steps Collapsible ── */}
      <section className="audit-section">
        <button className="timeline-toggle" onClick={() => setStepsOpen(o => !o)}>
          <span className="timeline-toggle__arrow">{stepsOpen ? '▲' : '▼'}</span>
          <span className="timeline-toggle__label">Agent Reasoning</span>
          <span className="timeline-toggle__count">{stepCount} steps</span>
        </button>
        {stepsOpen && <StepTimeline steps={audit.steps ?? []} />}
      </section>

    </div>
  );
};

/* ── Metric stat card ── */
interface MetricCardProps {
  label: string;
  base: number;
  final: number;
  fmt: (n: number) => string;
  deltaFmt: (n: number) => string;
  invertGood: boolean;   // true = lower is better (volatility)
}

const MetricCard: React.FC<MetricCardProps> = ({ label, base, final, fmt, deltaFmt, invertGood }) => {
  const diff = final - base;
  const improved = invertGood ? diff < -0.0001 : diff > 0.0001;
  const worsened = invertGood ? diff > 0.0001  : diff < -0.0001;

  const arrowCls  = improved ? 'arrow--pos' : worsened ? 'arrow--neg' : '';
  const deltaCls  = improved ? 'val--positive' : worsened ? 'val--negative' : '';
  const arrowChar = diff > 0.0001 ? '▲' : diff < -0.0001 ? '▼' : '—';

  return (
    <div className="metric-card">
      <span className="metric-card__label">{label}</span>
      <div className="metric-card__compare">
        <div className="metric-card__base-wrap">
          <span className="metric-card__base-label">Base</span>
          <span className="metric-card__base-val">{fmt(base)}</span>
        </div>
        <span className={`metric-card__arrow ${arrowCls}`}>{arrowChar}</span>
        <div className="metric-card__final-wrap">
          <span className="metric-card__final-label">Final</span>
          <span className="metric-card__final-val">{fmt(final)}</span>
        </div>
      </div>
      <span className={`metric-card__delta ${deltaCls}`}>{deltaFmt(diff)}</span>
    </div>
  );
};

export default AuditDisplay;
