import React from 'react';
import './AppLayout.css';

export type AppPage = 'bl_main' | 'backtest' | 'agent' | 'admin';

interface AppLayoutProps {
  children: React.ReactNode;
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
}

const NAV_TABS: { id: AppPage; label: string }[] = [
  { id: 'bl_main',   label: 'Portfolio Optimizer' },
  { id: 'backtest',  label: 'Backtest' },
  { id: 'agent',     label: 'Agent Analysis' },
  { id: 'admin',     label: 'Admin Console' },
];

export const AppLayout: React.FC<AppLayoutProps> = ({ children, activePage, onNavigate }) => {
  return (
    <div className="app-container">
      {/* Sticky Header */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">Portfolio Dashboard</h1>
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
    </div>
  );
};
