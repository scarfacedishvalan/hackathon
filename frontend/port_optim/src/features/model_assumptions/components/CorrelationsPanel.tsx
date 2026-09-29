import React, { useEffect, useState } from 'react';
import { modelAssumptionsService } from '../services/modelAssumptionsService';
import type { CorrelationMatrix } from '../types/modelAssumptionsTypes';
import './CorrelationsPanel.css';

const FREQUENCY_OPTIONS = [
  { value: 252, label: 'Daily (252)' },
  { value: 52, label: 'Weekly (52)' },
  { value: 12, label: 'Monthly (12)' },
];

// Diverging red (-1) -> white (0) -> green (+1) scale; fixed hue, lightness carries magnitude.
function colorForCorrelation(value: number): string {
  const v = Math.max(-1, Math.min(1, value));
  const hue = v >= 0 ? 142 : 0;
  const lightness = 94 - Math.abs(v) * 45;
  return `hsl(${hue}, 65%, ${lightness}%)`;
}

export const CorrelationsPanel: React.FC = () => {
  const [frequency, setFrequency] = useState(252);
  const [data, setData] = useState<CorrelationMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    modelAssumptionsService
      .getCorrelations(frequency)
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [frequency]);

  return (
    <div className="correlations-panel">
      <div className="correlations-header">
        <span className="correlations-title">Asset Correlations</span>
        <label className="frequency-select-label">
          Annualization frequency:
          <select
            className="frequency-select"
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
          >
            {FREQUENCY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="correlations-note">
        Correlation values are unaffected by the annualization frequency (it cancels out
        mathematically) — the frequency selector instead controls the annualized volatility
        figures below.
      </p>

      {loading && <div className="correlations-loading">Loading price data…</div>}
      {error && <div className="correlations-error">Failed to load: {error}</div>}

      {!loading && data && (
        <>
          <div className="correlations-grid-wrap">
            <table className="correlations-grid">
              <thead>
                <tr>
                  <th></th>
                  {data.assets.map((asset) => (
                    <th key={asset}>{asset}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.assets.map((rowAsset, i) => (
                  <tr key={rowAsset}>
                    <th>{rowAsset}</th>
                    {data.assets.map((colAsset, j) => {
                      const value = data.correlation[i][j];
                      return (
                        <td key={colAsset} style={{ background: colorForCorrelation(value) }}>
                          {value.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="volatility-section">
            <span className="volatility-title">Annualized Volatility ({frequency}x)</span>
            <div className="volatility-list">
              {data.assets.map((asset) => (
                <span key={asset} className="volatility-badge">
                  {asset}: {(data.annualized_volatility[asset] * 100).toFixed(1)}%
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
