import React from 'react';
import { useBLMain } from '../hooks/useBLMain';
import {
  AssetSelection,
  CreateView,
  ActiveViews,
  AnalystSuggestions,
  ModelControls,
  EfficientFrontierChart,
  BLAllocationChart,
  TopDownContribution,
} from '../components';
import './BLMainPage.css';

export const BLMainPage: React.FC = () => {
  const { data, loading, activeViews, parseView, parseViewLoading, deleteView, portfolios, portfoliosLoading, createPortfolio, deletePortfolio, selectedPortfolioId, setSelectedPortfolioId, selectedPortfolio } = useBLMain();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading Black-Litterman data...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="error-container">
        <p>Failed to load data. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="bl-main-page">
      {/* Left Column */}
      <div className="left-column">
        <AssetSelection assets={data.assets} />
        <CreateView parseView={parseView} parseViewLoading={parseViewLoading} />
        <ActiveViews views={activeViews} onDelete={deleteView} />
        <AnalystSuggestions suggestions={data.analystSuggestions} />
        <ModelControls
          portfolios={portfolios}
          portfoliosLoading={portfoliosLoading}
          createPortfolio={createPortfolio}
          deletePortfolio={deletePortfolio}
          selectedPortfolioId={selectedPortfolioId}
          setSelectedPortfolioId={setSelectedPortfolioId}
          selectedPortfolio={selectedPortfolio}
        />
      </div>

      {/* Right Column */}
      <div className="right-column">
        <EfficientFrontierChart data={data.efficientFrontier} />
        <BLAllocationChart data={data.allocation} />
        <TopDownContribution data={data.topDownContribution} />
      </div>
    </div>
  );
};
