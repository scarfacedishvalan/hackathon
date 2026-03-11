import React, { createContext, useContext, useState, useCallback } from 'react';
import { useBLMain as _useBLMainState } from '../hooks/useBLMain';
import { blMainService } from '../services/blMainService';

type BLMainContextValue = ReturnType<typeof _useBLMainState> & {
  saveThesis: (name: string) => Promise<string>;
  saveThesisLoading: boolean;
};

const BLMainContext = createContext<BLMainContextValue | null>(null);

/**
 * Provides a single shared useBLMain() state to the entire component tree.
 * Must wrap both AppLayout (Run button) and BLMainPage (charts) so that
 * clicking Run causes the charts to re-render with the new data.
 */
export const BLMainProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const state = _useBLMainState();
  const [saveThesisLoading, setSaveThesisLoading] = useState(false);

  const saveThesis = useCallback(async (name: string): Promise<string> => {
    setSaveThesisLoading(true);
    try {
      return await blMainService.saveThesis(name);
    } finally {
      setSaveThesisLoading(false);
    }
  }, []);

  const value: BLMainContextValue = { ...state, saveThesis, saveThesisLoading };
  return <BLMainContext.Provider value={value}>{children}</BLMainContext.Provider>;
};

export const useBLMain = (): BLMainContextValue => {
  const ctx = useContext(BLMainContext);
  if (!ctx) throw new Error('useBLMain must be used within BLMainProvider');
  return ctx;
};
