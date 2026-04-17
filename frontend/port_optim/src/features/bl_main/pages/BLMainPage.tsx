import React, { useState } from 'react';
import { useBLMain } from '../context/BLMainContext';
import { Button } from '@shared/components';
import { SaveThesisModal } from '../../../app/SaveThesisModal';
import {
  AssetSelection,
  CreateView,
  ActiveViews,
  AnalystSuggestions,
  ModelControls,
  EfficientFrontierChart,
  BLAllocationChart,
  TopDownContribution,
  PortfolioStats,
} from '../components';
import BLCalculationSteps from '../components/BLCalculationSteps';
import './BLMainPage.css';

const ASSET_VIEW_EXAMPLES = [
  'AAPL will outperform MSFT by 3% over the next quarter.',
  'TSLA expected to underperform JPM by 5%.',
];

const FACTOR_VIEW_EXAMPLES = [
  'Growth factor is expected to deliver a +4% annualized excess return (factor premium) over cash',
  'Rising rates will strongly benefit financials and slightly hurt defensives.',
];

interface PastableExamplesProps {
  onCopy: (text: string) => void;
}

const PastableExamples: React.FC<PastableExamplesProps> = ({ onCopy }) => (
  <div className="pastable-examples-card">
    <div className="examples-section">
      <div className="examples-category">
        <h4 className="examples-title">Asset Views</h4>
        {ASSET_VIEW_EXAMPLES.map((ex, i) => (
          <div key={i} className="example-item">
            <p className="example-text">{ex}</p>
            <button className="copy-btn" onClick={() => onCopy(ex)} title="Copy to input">📋</button>
          </div>
        ))}
      </div>
      <div className="examples-category">
        <h4 className="examples-title">Factor Views</h4>
        {FACTOR_VIEW_EXAMPLES.map((ex, i) => (
          <div key={i} className="example-item">
            <p className="example-text">{ex}</p>
            <button className="copy-btn" onClick={() => onCopy(ex)} title="Copy to input">📋</button>
          </div>
        ))}
      </div>
    </div>
  </div>
);

const PlayIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3.5 2.5L12.5 8L3.5 13.5V2.5Z" fill="currentColor" />
  </svg>
);

const SaveIcon: React.FC = () => (
  <svg width="13" height="13" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 2h7l3 3v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"
      stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="none"/>
    <path d="M9 2v4H5V2M5 9h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

export const BLMainPage: React.FC = () => {
  const {
    data, loading,
    bottomUpViews, topDownViews,
    parseView, parseViewLoading,
    deleteBottomUpView, deleteTopDownView,
    loadViews,
    portfolios: _portfolios, portfoliosLoading: _portfoliosLoading,
    createPortfolio: _createPortfolio, deletePortfolio: _deletePortfolio,
    selectedPortfolioId: _selectedPortfolioId, setSelectedPortfolioId: _setSelectedPortfolioId, selectedPortfolio: _selectedPortfolio,
    refetch, runLoading, error,
    saveThesis, saveThesisLoading,
  } = useBLMain();

  const [thesisModalOpen, setThesisModalOpen] = useState(false);
  const [dismissedError, setDismissedError] = useState<Error | null>(null);
  const [viewInput, setViewInput] = useState('');

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

      {/* Action row */}
      <div className="bl-action-row">
        <Button
          variant="secondary"
          icon={<SaveIcon />}
          className="bl-save-thesis-btn"
          onClick={() => setThesisModalOpen(true)}
          disabled={saveThesisLoading}
        >
          {saveThesisLoading ? 'Saving…' : 'Save Thesis'}
        </Button>
        <Button
          variant="secondary"
          icon={runLoading ? undefined : <PlayIcon />}
          className="bl-run-btn"
          onClick={refetch}
          disabled={runLoading}
        >
          {runLoading ? 'Running…' : 'Run Black-Litterman'}
        </Button>
      </div>

      {/* Optimization error banner */}
      {error && error !== dismissedError && (
        <div className="bl-error-banner" role="alert">
          <span className="bl-error-banner__message">{error.message}</span>
          <button
            className="bl-error-banner__dismiss"
            onClick={() => setDismissedError(error)}
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* 1. Asset Universe */}
      <AssetSelection />

      {/* 2. View Engine: Create View + Pastable Examples side by side */}
      <div className="view-editor-row">
        <div className="view-editor-left">
          <CreateView parseView={parseView} parseViewLoading={parseViewLoading} value={viewInput} onChange={setViewInput} />
        </div>
        <div className="view-editor-right">
          <PastableExamples onCopy={setViewInput} />
        </div>
      </div>

      {/* 3. Active Views: Bottom-Up + Top-Down side by side (full width) */}
      <ActiveViews
        bottomUpViews={bottomUpViews}
        topDownViews={topDownViews}
        onDeleteBottomUp={deleteBottomUpView}
        onDeleteTopDown={deleteTopDownView}
      />

      {/* 3. Allocation Chart + Portfolio Stats */}
      {data.portfolioStats ? (
        <div className="allocation-panel">
          <BLAllocationChart data={data.allocation} />
          <PortfolioStats data={data.portfolioStats} />
        </div>
      ) : (
        <BLAllocationChart data={data.allocation} />
      )}

      {/* 4. Efficient Frontier */}
      <EfficientFrontierChart data={data.efficientFrontier} />

      {/* 5. Remaining sections */}
      <TopDownContribution data={data.topDownContribution} />
      <AnalystSuggestions suggestions={data.analystSuggestions} onViewAdded={loadViews} />
      <ModelControls />

      {/* 6. Black-Litterman Calculation Steps */}
      {data.calculationSteps && data.calculationSteps.length > 0 && (
        <BLCalculationSteps steps={data.calculationSteps} />
      )}

      {/* Save Thesis Modal */}
      {thesisModalOpen && (
        <SaveThesisModal
          onSave={saveThesis}
          onClose={() => setThesisModalOpen(false)}
          saving={saveThesisLoading}
        />
      )}

    </div>
  );
};
