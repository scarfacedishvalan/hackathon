import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '@shared/components';
import { blMainService } from '../services/blMainService';
import './ModelControls.css';

interface ModelParams {
  tau: number;
  risk_aversion: number;
  risk_free_rate: number;
}

const DEFAULTS: ModelParams = { tau: 0.05, risk_aversion: 3.0, risk_free_rate: 0.02 };
const DEBOUNCE_MS = 500;

export const ModelControls: React.FC = () => {
  const [expanded, setExpanded] = useState(true);
  const [params, setParams] = useState<ModelParams>(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load from current.json on mount
  useEffect(() => {
    blMainService.getModelParameters()
      .then(p => setParams(p))
      .catch(() => {/* keep defaults */});
  }, []);

  // Debounced persist to current.json
  const persist = useCallback((next: ModelParams) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSaving(true);
      try {
        await blMainService.updateModelParameters(next);
      } finally {
        setSaving(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  const update = (key: keyof ModelParams, raw: string) => {
    const value = Number(raw);
    const next = { ...params, [key]: value };
    setParams(next);
    persist(next);
  };

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
              onChange={(e) => update('risk_aversion', e.target.value)}
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
              onChange={(e) => update('tau', e.target.value)}
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
              onChange={(e) => update('risk_free_rate', e.target.value)}
              className="slider"
            />
            <div className="slider-labels"><span>0%</span><span>10%</span></div>
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

