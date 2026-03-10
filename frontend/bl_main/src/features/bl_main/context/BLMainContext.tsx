import React, { createContext, useContext } from 'react';
import { useBLMain as _useBLMainState } from '../hooks/useBLMain';

type BLMainContextValue = ReturnType<typeof _useBLMainState>;

const BLMainContext = createContext<BLMainContextValue | null>(null);

/**
 * Provides a single shared useBLMain() state to the entire component tree.
 * Must wrap both AppLayout (Run button) and BLMainPage (charts) so that
 * clicking Run causes the charts to re-render with the new data.
 */
export const BLMainProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const value = _useBLMainState();
  return <BLMainContext.Provider value={value}>{children}</BLMainContext.Provider>;
};

export const useBLMain = (): BLMainContextValue => {
  const ctx = useContext(BLMainContext);
  if (!ctx) throw new Error('useBLMain must be used within BLMainProvider');
  return ctx;
};
