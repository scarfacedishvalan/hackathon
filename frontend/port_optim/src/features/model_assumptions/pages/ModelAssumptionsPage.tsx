import React from 'react';
import { Card } from '@shared/components';
import { useModelAssumptions } from '../hooks/useModelAssumptions';
import { MarketCapsTable } from '../components/MarketCapsTable';
import { FactorExposuresGrid } from '../components/FactorExposuresGrid';
import './ModelAssumptionsPage.css';

export const ModelAssumptionsPage: React.FC = () => {
  const { data, loading, error, saving, updateMarketCap, updateFactorExposure } = useModelAssumptions();

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

      <Card title="Market Caps">
        <MarketCapsTable data={data} onChange={updateMarketCap} />
      </Card>

      <Card title="Factor Exposures">
        <FactorExposuresGrid data={data} onChange={updateFactorExposure} />
      </Card>
    </div>
  );
};
