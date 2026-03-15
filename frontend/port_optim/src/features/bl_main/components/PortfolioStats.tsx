import React from 'react';
import type { PortfolioStats as PortfolioStatsType } from '../types/blMainTypes';
import './PortfolioStats.css';

interface Props {
  data: PortfolioStatsType;
}

type MetricKey = 'ret' | 'vol' | 'sharpe' | 'var95';

const METRICS: { key: MetricKey; label: string; pct: boolean }[] = [
  { key: 'ret',    label: 'Expected Return', pct: true  },
  { key: 'vol',    label: 'Volatility',      pct: true  },
  { key: 'sharpe', label: 'Sharpe Ratio',    pct: false },
  { key: 'var95',  label: 'VaR 95%',         pct: true  },
];

function fmtVal(v: number, pct: boolean): string {
  return pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(3);
}

export const PortfolioStats: React.FC<Props> = ({ data }) => (
  <div className="pstats-card">
    <div className="pstats-title">Portfolio Statistics</div>
    <div className="pstats-grid">
      {METRICS.map(({ key, label, pct }) => {
        const prior = data.prior[key];
        const post  = data.posterior[key];

        return (
          <div key={key} className="pstats-metric-box">
            <div className="pstats-metric-label">{label}</div>
            <div className="pstats-values">
              <div className="pstats-value-row">
                <span className="pstats-tag pstats-tag--prior">Prior</span>
                <span className="pstats-value pstats-value--prior">
                  {fmtVal(prior, pct)}
                </span>
              </div>
              <div className="pstats-value-row">
                <span className="pstats-tag pstats-tag--bl">BL</span>
                <span className="pstats-value pstats-value--bl">
                  {fmtVal(post, pct)}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);
