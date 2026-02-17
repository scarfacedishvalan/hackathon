import React, { useState, useEffect } from 'react';
import { Table, Column } from '@shared/components/Table';
import type { Asset, Portfolio, PortfolioHolding } from '../types/blMainTypes';
import mockData from '../mock/mockBlMainData.json';
import './AssetSelection.css';

interface AssetSelectionProps {
  assets: Asset[];
}

export const AssetSelection: React.FC<AssetSelectionProps> = ({ assets: initialAssets }) => {
  const [assets, setAssets] = useState<Asset[]>(initialAssets);
  const [portfolios, setPortfolios] = useState<Portfolio[]>(mockData.portfolios || []);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>('');
  const [showModal, setShowModal] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Modal state
  const [portfolioName, setPortfolioName] = useState('');
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [tickerSearch, setTickerSearch] = useState('');

  // Update assets when initial assets change
  useEffect(() => {
    setAssets(initialAssets);
  }, [initialAssets]);

  const loadPortfolio = (portfolioId: string) => {
    const portfolio = portfolios.find(p => p.id === portfolioId);
    if (!portfolio) return;

    setAssets(prevAssets => 
      prevAssets.map(asset => {
        const holding = portfolio.holdings.find(h => h.ticker === asset.ticker);
        return holding 
          ? { ...asset, weight: holding.weight }
          : asset;
      })
    );
    setSelectedPortfolioId(portfolioId);
  };

  const openCreateModal = () => {
    setShowModal(true);
    setPortfolioName('');
    setHoldings([]);
    setTickerSearch('');
  };

  const closeModal = () => {
    setShowModal(false);
  };

  const addHolding = () => {
    const ticker = tickerSearch.trim().toUpperCase();
    if (!ticker) return;
    
    if (holdings.some(h => h.ticker === ticker)) {
      alert('Ticker already added');
      return;
    }

    setHoldings([...holdings, { ticker, weight: 0 }]);
    setTickerSearch('');
  };

  const removeHolding = (ticker: string) => {
    setHoldings(holdings.filter(h => h.ticker !== ticker));
  };

  const updateHoldingWeight = (ticker: string, value: string) => {
    const weight = parseFloat(value) || 0;
    const clampedWeight = Math.max(0, Math.min(100, weight));
    
    setHoldings(holdings.map(h => 
      h.ticker === ticker 
        ? { ...h, weight: clampedWeight / 100 }
        : h
    ));
  };

  const totalWeight = holdings.reduce((sum, h) => sum + h.weight, 0);
  const remaining = 1 - totalWeight;
  const canSave = Math.abs(totalWeight - 1) < 0.0001 && portfolioName.trim() !== '';

  // Calculate summary data for collapsed view
  const selectedAssetsCount = assets.filter(a => a.selected).length;
  const assetsTotalWeight = assets.reduce((sum, a) => sum + (a.selected ? a.weight : 0), 0);
  const selectedPortfolio = portfolios.find(p => p.id === selectedPortfolioId);
  const portfolioDisplayName = selectedPortfolio?.name || 'No Portfolio Selected';

  const autoNormalize = () => {
    if (holdings.length === 0) return;
    
    const normalizedWeight = 1 / holdings.length;
    setHoldings(holdings.map(h => ({ ...h, weight: normalizedWeight })));
  };

  const savePortfolio = () => {
    if (!canSave) return;

    const newPortfolio: Portfolio = {
      id: `portfolio-${Date.now()}`,
      name: portfolioName.trim(),
      holdings: holdings.map(h => ({ ...h })),
    };

    setPortfolios([...portfolios, newPortfolio]);
    loadPortfolio(newPortfolio.id);
    closeModal();
  };

  const columns: Column<Asset>[] = [
    {
      key: 'selected',
      header: 'Select',
      width: '60px',
      render: (asset) => (
        <input
          type="checkbox"
          checked={asset.selected}
          onChange={() => {
            console.log('Toggle asset:', asset.ticker);
          }}
        />
      ),
    },
    {
      key: 'ticker',
      header: 'Ticker',
      width: '100px',
    },
    {
      key: 'name',
      header: 'Name',
    },
    {
      key: 'weight',
      header: 'Weight',
      width: '100px',
      render: (asset) => `${(asset.weight * 100).toFixed(1)}%`,
    },
  ];

  return (
    <>
      <div className="asset-selection-card">
        <div 
          className="asset-card-header collapsible-header" 
          onClick={() => setIsExpanded(prev => !prev)}
        >
          <h3 className="asset-card-title">
            Portfolio Context
            <span className={`chevron ${isExpanded ? 'expanded' : ''}`}>▼</span>
          </h3>
        </div>
        
        {!isExpanded ? (
          <div className="collapsed-summary">
            <div className="summary-info">
              <div className="summary-line">
                <span className="summary-label">Portfolio:</span>
                <span className="summary-value">{portfolioDisplayName}</span>
              </div>
              <div className="summary-line">
                <span className="summary-detail">
                  {selectedAssetsCount} Assets | Total Weight: {(assetsTotalWeight * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <button 
              className="change-btn" 
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(true);
              }}
            >
              Change
            </button>
          </div>
        ) : (
          <>
            <div className="asset-card-controls-row">
              <select 
                className="portfolio-dropdown"
                value={selectedPortfolioId}
                onChange={(e) => loadPortfolio(e.target.value)}
              >
                <option value="">Select Portfolio</option>
                {portfolios.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <button className="create-portfolio-btn" onClick={openCreateModal}>
                + Create Portfolio
              </button>
            </div>
            <div className="asset-card-content">
              <Table data={assets} columns={columns} />
            </div>
          </>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Create Portfolio</h2>
            
            <div className="modal-section">
              <label className="modal-label">Portfolio Name:</label>
              <input
                type="text"
                className="modal-input"
                value={portfolioName}
                onChange={(e) => setPortfolioName(e.target.value)}
                placeholder="Enter portfolio name"
              />
            </div>

            <div className="modal-section">
              <label className="modal-label">Add Security:</label>
              <div className="add-security-row">
                <input
                  type="text"
                  className="modal-input"
                  value={tickerSearch}
                  onChange={(e) => setTickerSearch(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addHolding()}
                  placeholder="Enter ticker (e.g., AAPL)"
                />
                <button className="modal-add-btn" onClick={addHolding}>
                  + Add
                </button>
              </div>
            </div>

            {holdings.length > 0 && (
              <div className="modal-section">
                <table className="holdings-table">
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Weight (%)</th>
                      <th>Remove</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map(h => (
                      <tr key={h.ticker}>
                        <td>{h.ticker}</td>
                        <td>
                          <input
                            type="number"
                            className="weight-input"
                            value={(h.weight * 100).toFixed(2)}
                            onChange={(e) => updateHoldingWeight(h.ticker, e.target.value)}
                            min="0"
                            max="100"
                            step="0.01"
                          />
                        </td>
                        <td>
                          <button 
                            className="remove-holding-btn"
                            onClick={() => removeHolding(h.ticker)}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                <div className={`remaining-allocation ${remaining < 0 ? 'negative' : ''}`}>
                  Remaining Allocation: <strong>{(remaining * 100).toFixed(2)}%</strong>
                  {remaining < 0 && <span className="warning"> (Exceeds 100%)</span>}
                </div>
              </div>
            )}

            <div className="modal-actions">
              {holdings.length > 0 && (
                <button className="modal-btn-secondary" onClick={autoNormalize}>
                  Auto Normalize
                </button>
              )}
              <button className="modal-btn-secondary" onClick={closeModal}>
                Cancel
              </button>
              <button 
                className="modal-btn-primary" 
                onClick={savePortfolio}
                disabled={!canSave}
              >
                Save Portfolio
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
