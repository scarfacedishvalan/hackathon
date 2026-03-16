import React, { useState, useEffect, useCallback } from 'react';
import { universeService } from '../services/blMainService';
import './AssetSelection.css';

/** Full asset universe sourced from backend/data/market_data.json */
const FULL_UNIVERSE = [
  { ticker: 'AAPL',  name: 'Apple Inc.' },
  { ticker: 'AMZN',  name: 'Amazon.com Inc.' },
  { ticker: 'BAC',   name: 'Bank of America' },
  { ticker: 'BND',   name: 'Vanguard Total Bond' },
  { ticker: 'GLD',   name: 'SPDR Gold Shares' },
  { ticker: 'GOOG',  name: 'Alphabet Inc.' },
  { ticker: 'GOOGL', name: 'Alphabet Inc.' },
  { ticker: 'JNJ',   name: 'Johnson & Johnson' },
  { ticker: 'JPM',   name: 'JPMorgan Chase' },
  { ticker: 'MSFT',  name: 'Microsoft Corp.' },
  { ticker: 'PG',    name: 'Procter & Gamble' },
  { ticker: 'TSLA',  name: 'Tesla Inc.' },
  { ticker: 'VNQ',   name: 'Vanguard Real Estate' },
  { ticker: 'WMT',   name: 'Walmart Inc.' },
];

const COL_SIZE = 7;
const col1 = FULL_UNIVERSE.slice(0, COL_SIZE);
const col2 = FULL_UNIVERSE.slice(COL_SIZE);

export const AssetSelection: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeUniverse, setActiveUniverse] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  const loadUniverse = useCallback(async () => {
    const tickers = await universeService.getUniverse();
    setActiveUniverse(
      new Set(tickers.length > 0 ? tickers : FULL_UNIVERSE.map(a => a.ticker))
    );
  }, []);

  useEffect(() => { loadUniverse(); }, [loadUniverse]);

  const handleToggle = async (ticker: string) => {
    const next = new Set(activeUniverse);
    if (next.has(ticker)) next.delete(ticker);
    else next.add(ticker);
    setActiveUniverse(next);
    setSaving(true);
    try {
      await universeService.setUniverse([...next]);
    } finally {
      setSaving(false);
    }
  };

  const selected = FULL_UNIVERSE.filter(a => activeUniverse.has(a.ticker));

  const renderSummary = () => {
    if (selected.length === 0) {
      return <span className="asset-badge">No assets selected</span>;
    }
    return (
      <>
        {selected.map(a => (
          <span key={a.ticker} className="asset-badge">{a.ticker}</span>
        ))}
        <span className="asset-count">({selected.length})</span>
      </>
    );
  };

  const renderColumn = (items: typeof FULL_UNIVERSE) => (
    <div className="universe-column">
      {items.map(asset => (
        <label key={asset.ticker} className="universe-row">
          <input
            type="checkbox"
            className="universe-checkbox"
            checked={activeUniverse.has(asset.ticker)}
            onChange={() => handleToggle(asset.ticker)}
          />
          <span className="universe-ticker">{asset.ticker}</span>
          <span className="universe-name">{asset.name}</span>
        </label>
      ))}
    </div>
  );

  return (
    <div className="asset-selection-card">
      <div
        className="asset-card-header collapsible-header"
        onClick={() => setIsExpanded(p => !p)}
      >
        <h3 className="asset-card-title">
          Asset Universe
          {saving && <span className="universe-saving">saving…</span>}
          <span className={`chevron ${isExpanded ? 'expanded' : ''}`}>▼</span>
        </h3>
      </div>

      {!isExpanded ? (
        <div className="universe-collapsed">
          <div className="universe-summary">{renderSummary()}</div>
          <button
            className="change-btn"
            onClick={e => { e.stopPropagation(); setIsExpanded(true); }}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="universe-grid">
          {renderColumn(col1)}
          {renderColumn(col2)}
        </div>
      )}
    </div>
  );
};
