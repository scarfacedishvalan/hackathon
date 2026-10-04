import React, { useEffect, useMemo, useState } from 'react';
import type { MarketAssumptions } from '../types/modelAssumptionsTypes';
import './FactorExposuresGrid.css';

const DEFAULT_STEP = 0.01;

// Diverging red (negative) -> white (0) -> green (positive) scale, normalized
// to the largest magnitude currently present in the matrix.
function colorForExposure(value: number, maxAbs: number): string {
  if (maxAbs <= 0) return 'hsl(0, 0%, 94%)';
  const v = Math.max(-1, Math.min(1, value / maxAbs));
  const hue = v >= 0 ? 142 : 0;
  const lightness = 94 - Math.abs(v) * 45;
  return `hsl(${hue}, 65%, ${lightness}%)`;
}

interface ExposureCellProps {
  value: number;
  background: string;
  onChange: (value: number) => void;
}

const ExposureCell: React.FC<ExposureCellProps> = ({ value, background, onChange }) => {
  const [editValue, setEditValue] = useState(value.toFixed(2));

  // Stay in sync if the value changes externally (e.g. after a save round-trip).
  useEffect(() => {
    setEditValue(value.toFixed(2));
  }, [value]);

  const commit = (next: number) => {
    const rounded = Math.round(next * 100) / 100;
    setEditValue(rounded.toFixed(2));
    onChange(rounded);
  };

  const handleStep = (dir: 1 | -1) => commit(value + dir * DEFAULT_STEP);

  const handleBlur = () => {
    const parsed = parseFloat(editValue);
    if (!isNaN(parsed)) commit(parsed);
    else setEditValue(value.toFixed(2));
  };

  return (
    <td className="exposure-cell" style={{ background }}>
      <div className="exposure-cell-inner">
        <input
          type="text"
          inputMode="decimal"
          className="exposure-input"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
          aria-label="factor exposure"
        />
        <span className="exposure-steppers">
          <button type="button" className="exposure-step-btn exposure-step-btn--up" onClick={() => handleStep(1)} tabIndex={-1} aria-label="increase">
            <svg width="7" height="5" viewBox="0 0 7 5" fill="none"><path d="M3.5 0.5L6.5 4.5H0.5L3.5 0.5Z" fill="currentColor" /></svg>
          </button>
          <button type="button" className="exposure-step-btn exposure-step-btn--down" onClick={() => handleStep(-1)} tabIndex={-1} aria-label="decrease">
            <svg width="7" height="5" viewBox="0 0 7 5" fill="none"><path d="M3.5 4.5L0.5 0.5H6.5L3.5 4.5Z" fill="currentColor" /></svg>
          </button>
        </span>
      </div>
    </td>
  );
};

interface FactorExposuresGridProps {
  data: MarketAssumptions;
  onChange: (asset: string, factorIndex: number, value: number) => void;
}

export const FactorExposuresGrid: React.FC<FactorExposuresGridProps> = ({ data, onChange }) => {
  const maxAbs = useMemo(() => {
    let max = 0;
    for (const asset of data.all_assets) {
      const row = data.factor_exposures[asset] ?? [];
      for (const v of row) max = Math.max(max, Math.abs(v));
    }
    return max;
  }, [data.all_assets, data.factor_exposures]);

  return (
    <div className="factor-exposures-grid-wrap">
      <table className="factor-exposures-grid">
        <thead>
          <tr>
            <th>Asset</th>
            {data.factor_names.map((name) => (
              <th key={name}>{name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.all_assets.map((asset) => {
            const row = data.factor_exposures[asset] ?? data.factor_names.map(() => 0);
            return (
              <tr key={asset}>
                <th>{asset}</th>
                {row.map((value, factorIndex) => (
                  <ExposureCell
                    key={factorIndex}
                    value={value}
                    background={colorForExposure(value, maxAbs)}
                    onChange={(next) => onChange(asset, factorIndex, next)}
                  />
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

