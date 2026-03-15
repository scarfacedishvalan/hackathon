import React from 'react';
import type { PortfolioStats as PortfolioStatsType } from '../types/blMainTypes';
import './PortfolioStats.css';

interface Props {
  data: PortfolioStatsType;
}

type MetricKey = 'ret' | 'vol' | 'sharpe';

const METRICS: { key: MetricKey; label: string; pct: boolean; higherBetter: boolean }[] = [
  { key: 'ret',    label: 'Expected Return', pct: true,  higherBetter: true  },
  { key: 'vol',    label: 'Volatility',      pct: true,  higherBetter: false },
  { key: 'sharpe', label: 'Sharpe Ratio',    pct: false, higherBetter: true  },
];

function fmtVal(v: number, pct: boolean): string {
  return pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(3);
}

function fmtDelta(delta: number, pct: boolean): string {
  const sign = delta >= 0 ? '+' : '';
  return pct
    ? `${sign}${(delta * 100).toFixed(2)}%`
    : `${sign}${delta.toFixed(3)}`;
}

export const PortfolioStats: React.FC<Props> = ({ data }) => (
  <div className="pstats-card">
    <div className="pstats-title">Portfolio Statistics</div>
    <div className="pstats-metrics">
      {METRICS.map(({ key, label, pct, higherBetter }) => {
        const prior = data.prior[key];
        const post  = data.posterior[key];
        const delta = post - prior;
        const improved = higherBetter ? delta > 0 : delta < 0;
        const neutral  = Math.abs(delta) < 1e-6;

        return (
          <div key={key} className="pstats-metric">
            <div className="pstats-metric-label">{label}</div>

            <div className="pstats-row">
              <span className="pstats-row-tag pstats-row-tag--prior">Prior</span>
              <span className="pstats-row-value pstats-row-value--prior">
                {fmtVal(prior, pct)}
              </span>
            </div>

            <div className="pstats-row">
              <span className="pstats-row-tag pstats-row-tag--bl">BL</span>
              <span className="pstats-row-value pstats-row-value--bl">
                {fmtVal(post, pct)}
              </span>
            </div>

            {!neutral && (
              <div className={`pstats-delta ${improved ? 'pstats-delta--good' : 'pstats-delta--bad'}`}>
                {improved ? '▲' : '▼'} {fmtDelta(delta, pct)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  </div>
);
