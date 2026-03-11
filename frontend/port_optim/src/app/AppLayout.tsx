import React, { useState } from 'react';
import { useBLMain } from '@features/bl_main/context/BLMainContext';
import { Button } from '@shared/components';
import { SaveThesisModal } from './SaveThesisModal';
import './AppLayout.css';

export type AppPage = 'bl_main' | 'backtest' | 'agent' | 'admin';

interface AppLayoutProps {
  children: React.ReactNode;
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
}

const PlayIcon: React.FC = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M3.5 2.5L12.5 8L3.5 13.5V2.5Z"
      fill="currentColor"
    />
  </svg>
);

const SaveIcon: React.FC = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 2h7l3 3v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"
      stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="none"/>
    <path d="M9 2v4H5V2M5 9h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const NAV_TABS: { id: AppPage; label: string }[] = [
  { id: 'bl_main',   label: 'Portfolio Optimizer' },
  { id: 'backtest',  label: 'Backtest' },
  { id: 'agent',     label: 'Agent Analysis' },
  { id: 'admin',     label: 'Admin Console' },
];

export const AppLayout: React.FC<AppLayoutProps> = ({ children, activePage, onNavigate }) => {
  const { refetch, runLoading, saveThesis, saveThesisLoading } = useBLMain();
  const [thesisModalOpen, setThesisModalOpen] = useState(false);

  return (
    <div className="app-container">
      {/* Sticky Header */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">Portfolio Dashboard</h1>
          <div className="header-actions">
            {activePage === 'bl_main' && (
              <>
                <button
                  className="save-thesis-btn"
                  onClick={() => setThesisModalOpen(true)}
                  disabled={saveThesisLoading}
                >
                  <SaveIcon />
                  {saveThesisLoading ? 'Saving…' : 'Save Thesis'}
                </button>
                <Button
                  variant="primary"
                  size="large"
                  icon={runLoading ? undefined : <PlayIcon />}
                  onClick={refetch}
                  disabled={runLoading}
                >
                  {runLoading ? 'Running…' : 'Run Black-Litterman'}
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="app-nav">
          {NAV_TABS.map(tab => (
            <button
              key={tab.id}
              className={`nav-tab${activePage === tab.id ? ' nav-tab--active' : ''}`}
              onClick={() => onNavigate(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {children}
      </main>

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
