import React, { useState } from 'react';
import { Card } from '@shared/components';
import './ModelControls.css';

export const ModelControls: React.FC = () => {
  const [expanded, setExpanded] = useState(true);
  const [riskAversion, setRiskAversion] = useState(2.5);
  const [confidenceScaling, setConfidenceScaling] = useState<'low' | 'medium' | 'high'>('medium');

  return (
    <Card className="model-controls">
      <div className="controls-header" onClick={() => setExpanded(!expanded)}>
        <h3 className="controls-title">
          Model Controls (λ = Risk Aversion)
        </h3>
        <span className="toggle-icon">{expanded ? '−' : '+'}</span>
      </div>

      {expanded && (
        <div className="controls-content">
          <div className="control-group">
            <label className="control-label">
              Risk Aversion: {riskAversion.toFixed(1)}
            </label>
            <input
              type="range"
              min="0.5"
              max="5"
              step="0.1"
              value={riskAversion}
              onChange={(e) => setRiskAversion(Number(e.target.value))}
              className="slider"
            />
            <div className="slider-labels">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>

          <div className="control-group">
            <label className="control-label">Confidence Scaling</label>
            <div className="radio-group-vertical">
              {(['low', 'medium', 'high'] as const).map((level) => (
                <label key={level} className="radio-option">
                  <input
                    type="radio"
                    value={level}
                    checked={confidenceScaling === level}
                    onChange={(e) =>
                      setConfidenceScaling(e.target.value as 'low' | 'medium' | 'high')
                    }
                  />
                  <span className="radio-text">{level.charAt(0).toUpperCase() + level.slice(1)}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};
