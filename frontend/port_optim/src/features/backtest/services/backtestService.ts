import type { BacktestRecipe, BacktestRunResult, PortfolioRunResult, PortfolioRunRequest } from '../types/backtestTypes';
import { apiClient } from '../../../services/apiClient';
import mockData from '../mock/mockBacktestData.json';

// ---------------------------------------------------------------------------
// Mock fallbacks
// ---------------------------------------------------------------------------

const MOCK_RECIPE = mockData.parsedRecipe as unknown as BacktestRecipe;
const MOCK_RESULT = mockData.runResult    as unknown as BacktestRunResult;

const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const backtestService = {
  /**
   * Step 1 — Parse natural-language text into a recipe.
   * Falls back to mock when the backend is unreachable.
   */
  parseStrategy: async (text: string): Promise<BacktestRecipe> => {
    try {
      return await apiClient.post<BacktestRecipe>('/backtest/parse', { text });
    } catch {
      await delay(600);
      return MOCK_RECIPE;
    }
  },

  /**
   * Step 2 — Execute a validated recipe and return metrics + equity curve.
   * Falls back to mock when the backend is unreachable.
   */
  runRecipe: async (recipe: BacktestRecipe): Promise<BacktestRunResult> => {
    try {
      return await apiClient.post<BacktestRunResult>('/backtest/run', { recipe });
    } catch {
      await delay(900);
      return MOCK_RESULT;
    }
  },

  /** List saved BL thesis names available for portfolio backtest. */
  listTheses: async (): Promise<string[]> => {
    try {
      return await apiClient.get<string[]>('/backtest/theses');
    } catch {
      return [];
    }
  },

  /** Run a multi-asset portfolio backtest driven by a saved thesis. */
  runPortfolio: async (req: PortfolioRunRequest): Promise<PortfolioRunResult> => {
    return apiClient.post<PortfolioRunResult>('/backtest/run-portfolio', req);
  },
};
