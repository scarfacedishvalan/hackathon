import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '@shared/components';
import { blMainService } from '../services/blMainService';
import './ModelControls.css';

interface ModelParams {
  tau: number;
  risk_aversion: number;
  risk_free_rate: number;
}

interface Constraints {
  long_only: boolean;
  weight_bounds: [number, number];
}

const PARAM_DEFAULTS: ModelParams = { tau: 0.05, risk_aversion: 3.0, risk_free_rate: 0.02 };
const CONSTRAINT_DEFAULTS: Constraints = { long_only: true, weight_bounds: [0.0, 1.0] };
const DEBOUNCE_MS = 500;

export const ModelControls: React.FC = () => {
  const [expanded, setExpanded] = useState(true);
  const [params, setParams] = useState<ModelParams>(PARAM_DEFAULTS);
  const [constraints, setConstraints] = useState<Constraints>(CONSTRAINT_DEFAULTS);
  const [saving, setSaving] = useState(false);
  const paramDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const constraintDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load from current.json on mount
  useEffect(() => {
    blMainService.getModelParameters()
      .then(p => setParams(p))
      .catch(() => {/* keep defaults */});
    blMainService.getConstraints()
      .then(c => setConstraints(c))
      .catch(() => {/* keep defaults */});
  }, []);

  // Debounced persist — model params
  const persistParams = useCallback((next: ModelParams) => {
    if (paramDebounce.current) clearTimeout(paramDebounce.current);
    paramDebounce.current = setTimeout(async () => {
      setSaving(true);
      try { await blMainService.updateModelParameters(next); }
      finally { setSaving(false); }
    }, DEBOUNCE_MS);
  }, []);

  // Debounced persist — constraints
  const persistConstraints = useCallback((next: Constraints) => {
    if (constraintDebounce.current) clearTimeout(constraintDebounce.current);
    constraintDebounce.current = setTimeout(async () => {
      setSaving(true);
      try { await blMainService.updateConstraints(next); }
      finally { setSaving(false); }
    }, DEBOUNCE_MS);
  }, []);

  const updateParam = (key: keyof ModelParams, raw: string) => {
    const next = { ...params, [key]: Number(raw) };
    setParams(next);
    persistParams(next);
  };

  const updateLower = (raw: string) => {
    const lower = Number(raw);
    const upper = Math.max(lower + 0.01, constraints.weight_bounds[1]);
    const next: Constraints = { ...constraints, weight_bounds: [lower, upper] };
    setConstraints(next);
    persistConstraints(next);
  };

  const updateUpper = (raw: string) => {
    const upper = Number(raw);
    const lower = Math.min(constraints.weight_bounds[0], upper - 0.01);
    const next: Constraints = { ...constraints, weight_bounds: [lower, upper] };
    setConstraints(next);
    persistConstraints(next);
  };

  const toggleLongOnly = () => {
    const next: Constraints = { ...constraints, long_only: !constraints.long_only };
    setConstraints(next);
    persistConstraints(next);
  };

  const [lower, upper] = constraints.weight_bounds;

  return (
    <Card className="model-controls">
      <div className="controls-header" onClick={() => setExpanded(!expanded)}>
        <h3 className="controls-title">
          Model Parameters {saving && <span className="saving-indicator">saving…</span>}
        </h3>
        <span className="toggle-icon">{expanded ? '−' : '+'}</span>
      </div>

      {expanded && (
        <div className="controls-content">

          {/* Risk Aversion */}
          <div className="control-group">
            <label className="control-label">
              Risk Aversion (δ): <strong>{params.risk_aversion.toFixed(1)}</strong>
            </label>
            <input
              type="range" min="0.5" max="10" step="0.5"
              value={params.risk_aversion}
              onChange={(e) => updateParam('risk_aversion', e.target.value)}
              className="slider"
            />
            <div className="slider-labels"><span>0.5 — risk-seeking</span><span>10 — risk-averse</span></div>
          </div>

          {/* Tau */}
          <div className="control-group">
            <label className="control-label">
              Prior Uncertainty (τ): <strong>{params.tau.toFixed(2)}</strong>
            </label>
            <input
              type="range" min="0.01" max="0.20" step="0.01"
              value={params.tau}
              onChange={(e) => updateParam('tau', e.target.value)}
              className="slider"
            />
            <div className="slider-labels"><span>0.01 — trust prior</span><span>0.20 — trust views</span></div>
          </div>

          {/* Risk-free Rate */}
          <div className="control-group">
            <label className="control-label">
              Risk-free Rate (r_f): <strong>{(params.risk_free_rate * 100).toFixed(2)}%</strong>
            </label>
            <input
              type="range" min="0" max="0.10" step="0.005"
              value={params.risk_free_rate}
              onChange={(e) => updateParam('risk_free_rate', e.target.value)}
              className="slider"
            />
            <div className="slider-labels"><span>0%</span><span>10%</span></div>
          </div>

          {/* Divider */}
          <div className="controls-divider" />

          {/* Weight Bounds */}
          <div className="control-group">
            <label className="control-label">Weight Bounds (per asset)</label>
            <div className="bounds-row">
              <div className="bound-control">
                <span className="bound-label">Lower: <strong>{(lower * 100).toFixed(1)}%</strong></span>
                <input
                  type="range" min="0" max="0.5" step="0.01"
                  value={lower}
                  onChange={(e) => updateLower(e.target.value)}
                  className="slider"
                />
                <div className="slider-labels"><span>0%</span><span>50%</span></div>
              </div>
              <div className="bound-control">
                <span className="bound-label">Upper: <strong>{(upper * 100).toFixed(1)}%</strong></span>
                <input
                  type="range" min="0.1" max="1" step="0.01"
                  value={upper}
                  onChange={(e) => updateUpper(e.target.value)}
                  className="slider"
                />
                <div className="slider-labels"><span>10%</span><span>100%</span></div>
              </div>
            </div>
          </div>

          {/* Long-only toggle */}
          <div className="control-group">
            <label className="control-label">Portfolio Constraints</label>
            <button
              className={`long-only-toggle ${constraints.long_only ? 'active' : ''}`}
              onClick={toggleLongOnly}
              type="button"
            >
              <span className="toggle-dot" />
              Long-only {constraints.long_only ? 'enabled' : 'disabled'}
            </button>
            <p className="constraint-hint">
              {constraints.long_only
                ? 'No short positions — all weights ≥ lower bound.'
                : 'Short positions allowed (lower bound may be negative).'}
            </p>
          </div>

        </div>
      )}

      <style>{`
        .saving-indicator {
          font-size: 11px;
          font-weight: 400;
          color: #6b7280;
          margin-left: 8px;
        }
      `}</style>
    </Card>
  );
};

