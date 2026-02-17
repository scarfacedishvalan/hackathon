import React from 'react';
import { AppLayout } from './AppLayout';
import { Providers } from './providers';
import { BLMainPage } from '@features/bl_main';

export const App: React.FC = () => {
  return (
    <Providers>
      <AppLayout>
        <BLMainPage />
      </AppLayout>
    </Providers>
  );
};
