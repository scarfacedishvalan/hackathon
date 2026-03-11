import React, { createContext, useContext } from 'react';
import { useBacktest as _useBacktestState } from '../hooks/useBacktest';

type BacktestContextValue = ReturnType<typeof _useBacktestState>;

const BacktestContext = createContext<BacktestContextValue | null>(null);

export const BacktestProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const state = _useBacktestState();
  return <BacktestContext.Provider value={state}>{children}</BacktestContext.Provider>;
};

export const useBacktest = (): BacktestContextValue => {
  const ctx = useContext(BacktestContext);
  if (!ctx) throw new Error('useBacktest must be used within BacktestProvider');
  return ctx;
};
