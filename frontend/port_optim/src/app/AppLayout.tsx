import React from 'react';
import './AppLayout.css';
import logoImage from '../assets/bl_logo.png';

export type AppPage = 'bl_main' | 'backtest' | 'agent' | 'admin';

interface AppLayoutProps {
  children: React.ReactNode;
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
}

const NAV_TABS: { id: AppPage; label: string }[] = [
  { id: 'bl_main',   label: 'Black Litterman' },
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
          <div className="header-branding">
            <img src={logoImage} alt="View Matrix Dashboard" className="app-logo" />
            <h1 className="app-title">ViewMatrix: Express, Build, Optimize!</h1>
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
    </div>
  );
};
