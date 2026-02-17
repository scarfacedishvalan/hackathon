import React from 'react';
import { useBLMain } from '@features/bl_main/hooks/useBLMain';
import { Button } from '@shared/components';
import './AppLayout.css';

interface AppLayoutProps {
  children: React.ReactNode;
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

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { refetch, loading } = useBLMain();

  return (
    <div className="app-container">
      {/* Sticky Header */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">Black-Litterman Portfolio System</h1>
          <Button
            variant="primary"
            size="large"
            icon={<PlayIcon />}
            onClick={refetch}
            disabled={loading}
          >
            Run Black-Litterman
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {children}
      </main>
    </div>
  );
};
