import React, { useState } from 'react';
import { AppLayout, type AppPage } from './AppLayout';
import { Providers } from './providers';
import { BLMainPage, BLMainProvider } from '@features/bl_main';
import { BacktestPage } from '@features/backtest';
import { AgentPage } from '@features/agent';

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<AppPage>('bl_main');

  return (
    <Providers>
      <BLMainProvider>
        <AppLayout activePage={activePage} onNavigate={setActivePage}>
          {activePage === 'bl_main' && <BLMainPage />}
          {activePage === 'backtest' && <BacktestPage />}
          {activePage === 'agent' && <AgentPage />}
        </AppLayout>
      </BLMainProvider>
    </Providers>
  );
};
