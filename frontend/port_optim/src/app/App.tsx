import React, { useState } from 'react';
import { AppLayout, type AppPage } from './AppLayout';
import { Providers } from './providers';
import { BLMainPage, BLMainProvider } from '@features/bl_main';
import { BacktestPage } from '@features/backtest';
import { AgentPage } from '@features/agent';
import { AdminPage } from '@features/admin';

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<AppPage>('bl_main');

  return (
    <Providers>
      <BLMainProvider>
        <AppLayout activePage={activePage} onNavigate={setActivePage}>
          {/* Always keep pages mounted to preserve state across tab switches. */}
          <div style={{ display: activePage === 'bl_main'  ? undefined : 'none' }}><BLMainPage /></div>
          <div style={{ display: activePage === 'backtest' ? undefined : 'none' }}><BacktestPage /></div>
          <div style={{ display: activePage === 'agent'    ? undefined : 'none' }}><AgentPage /></div>
          <div style={{ display: activePage === 'admin'    ? undefined : 'none' }}><AdminPage /></div>
        </AppLayout>
      </BLMainProvider>
    </Providers>
  );
};
