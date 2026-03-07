import React, { useState } from 'react';
import { Card } from '@shared/components';
import type { Portfolio } from '../types/blMainTypes';
import './ModelControls.css';

interface ModelControlsProps {
  portfolios: Portfolio[];
  portfoliosLoading: boolean;
  createPortfolio: (portfolio: Omit<Portfolio, 'id'> & { id?: string }) => Promise<void>;
  deletePortfolio: (id: string) => Promise<void>;
  selectedPortfolioId: string | null;
  setSelectedPortfolioId: (id: string | null) => void;
  selectedPortfolio: Portfolio | null;
}

export const ModelControls: React.FC<ModelControlsProps> = ({
  portfolios,
  portfoliosLoading,
  createPortfolio,
  deletePortfolio,
  selectedPortfolioId,
  setSelectedPortfolioId,
  selectedPortfolio,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [portfolioExpanded, setPortfolioExpanded] = useState(true);
  const [riskAversion, setRiskAversion] = useState(2.5);
  const [confidenceScaling, setConfidenceScaling] = useState<'low' | 'medium' | 'high'>('medium');

  const [newName, setNewName] = useState('');
  const [newHoldings, setNewHoldings] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreatePortfolio = async () => {
    setCreateError(null);
    const name = newName.trim();
    if (!name) { setCreateError('Name is required'); return; }

    let holdings: { ticker: string; weight: number }[] = [];
    try {
      holdings = JSON.parse(newHoldings);
      if (!Array.isArray(holdings)) throw new Error();
    } catch {
      setCreateError('Holdings must be a JSON array, e.g. [{"ticker":"AAPL","weight":0.6}]');
      return;
    }

    setCreating(true);
    try {
      await createPortfolio({ name, holdings });
      setNewName('');
      setNewHoldings('');
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create portfolio');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Card className="model-controls">
      <div className="controls-header" onClick={() => setExpanded(!expanded)}>
        <h3 className="controls-title">Model Controls (λ = Risk Aversion)</h3>
        <span className="toggle-icon">{expanded ? '−' : '+'}</span>
      </div>

      {expanded && (
        <div className="controls-content">
          <div className="control-group">
            <label className="control-label">
              Risk Aversion: {riskAversion.toFixed(1)}
            </label>
            <input
              type="range" min="0.5" max="5" step="0.1"
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
                    type="radio" value={level}
                    checked={confidenceScaling === level}
                    onChange={(e) => setConfidenceScaling(e.target.value as 'low' | 'medium' | 'high')}
                  />
                  <span className="radio-text">{level.charAt(0).toUpperCase() + level.slice(1)}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="controls-header portfolio-section-header" onClick={() => setPortfolioExpanded(!portfolioExpanded)}>
        <h3 className="controls-title">Portfolio Context</h3>
        <span className="toggle-icon">{portfolioExpanded ? '−' : '+'}</span>
      </div>

      {portfolioExpanded && (
        <div className="controls-content">
          {portfoliosLoading ? (
            <p className="portfolio-loading">Loading portfolios…</p>
          ) : (
            <>
              <div className="control-group">
                <label className="control-label">Select Portfolio</label>
                <select
                  className="portfolio-select"
                  value={selectedPortfolioId ?? ''}
                  onChange={(e) => setSelectedPortfolioId(e.target.value || null)}
                >
                  <option value="">— none —</option>
                  {portfolios.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {selectedPortfolio && (
                <div className="portfolio-holdings-table">
                  <div className="portfolio-holdings-header">
                    <span className="control-label">{selectedPortfolio.name}</span>
                    <button
                      className="portfolio-delete-btn"
                      onClick={() => {
                        deletePortfolio(selectedPortfolio.id);
                        setSelectedPortfolioId(null);
                      }}
                      title="Delete portfolio"
                    >
                      ×
                    </button>
                  </div>
                  <table className="holdings-table">
                    <thead>
                      <tr><th>Ticker</th><th>Weight</th></tr>
                    </thead>
                    <tbody>
                      {selectedPortfolio.holdings.map((h) => (
                        <tr key={h.ticker}>
                          <td>{h.ticker}</td>
                          <td>{(h.weight * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          <div className="portfolio-create">
            <p className="control-label">Add Portfolio</p>
            <input
              className="portfolio-input"
              placeholder="Portfolio name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <textarea
              className="portfolio-input portfolio-textarea"
              placeholder='[{"ticker":"AAPL","weight":0.6},{"ticker":"MSFT","weight":0.4}]'
              rows={3}
              value={newHoldings}
              onChange={(e) => setNewHoldings(e.target.value)}
            />
            {createError && <p className="portfolio-error">{createError}</p>}
            <button
              className="portfolio-add-btn"
              onClick={handleCreatePortfolio}
              disabled={creating}
            >
              {creating ? 'Saving…' : 'Save Portfolio'}
            </button>
          </div>
        </div>
      )}
    </Card>
  );
};

