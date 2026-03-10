import React from 'react';
import { AppLayout } from './AppLayout';
import { Providers } from './providers';
import { BLMainPage, BLMainProvider } from '@features/bl_main';

export const App: React.FC = () => {
  return (
    <Providers>
      <BLMainProvider>
        <AppLayout>
          <BLMainPage />
        </AppLayout>
      </BLMainProvider>
    </Providers>
  );
};
