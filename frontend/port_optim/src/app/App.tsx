import React, { useState } from 'react';
import { AppLayout, type AppPage } from './AppLayout';
import { Providers } from './providers';
import { BLMainPage, BLMainProvider } from '@features/bl_main';
import { BacktestPage, BacktestProvider } from '@features/backtest';

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<AppPage>('bl_main');

  return (
    <Providers>
      <BLMainProvider>
        <BacktestProvider>
          <AppLayout activePage={activePage} onNavigate={setActivePage}>
            {activePage === 'bl_main' ? <BLMainPage /> : <BacktestPage />}
          </AppLayout>
        </BacktestProvider>
      </BLMainProvider>
    </Providers>
  );
};
