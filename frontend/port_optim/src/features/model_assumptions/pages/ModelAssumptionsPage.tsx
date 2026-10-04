import React from 'react';
import { useModelAssumptions } from '../hooks/useModelAssumptions';
import { CollapsibleSection } from '../components/CollapsibleSection';
import { MarketCapsTable } from '../components/MarketCapsTable';
import { FactorExposuresGrid } from '../components/FactorExposuresGrid';
import { PriceHistoryPanel } from '../components/PriceHistoryPanel';
import { CorrelationsPanel } from '../components/CorrelationsPanel';
import './ModelAssumptionsPage.css';

export const ModelAssumptionsPage: React.FC = () => {
  const { data, loading, error, saving, refreshing, updateFactorExposure, refreshMarketCaps } = useModelAssumptions();

  if (loading) return <div className="model-assumptions-page">Loading…</div>;
  if (error && !data) return <div className="model-assumptions-page model-assumptions-error">Failed to load: {error}</div>;
  if (!data) return null;

  return (
    <div className="model-assumptions-page">
      <p className="model-assumptions-note">
        Edits here read from and write directly to <code>market_data.json</code> — the shared
        registry used by every Black-Litterman calculation.
        {saving && <span className="saving-indicator"> saving…</span>}
      </p>
      {error && <p className="model-assumptions-error">{error}</p>}

      <CollapsibleSection title="Factor Exposures">
        <FactorExposuresGrid data={data} onChange={updateFactorExposure} />
      </CollapsibleSection>

      <CollapsibleSection
        title="Market Caps"
        headerExtra={
          <button
            type="button"
            className="refresh-caps-btn"
            onClick={(e) => { e.stopPropagation(); refreshMarketCaps(); }}
            disabled={refreshing}
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        }
      >
        <MarketCapsTable data={data} />
      </CollapsibleSection>

      <CollapsibleSection title="Price History">
        <PriceHistoryPanel tickers={data.all_assets} />
      </CollapsibleSection>

      <CollapsibleSection title="Correlations">
        <CorrelationsPanel />
      </CollapsibleSection>
    </div>
  );
};
