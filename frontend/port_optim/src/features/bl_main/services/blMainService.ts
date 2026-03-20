import type { BLMainData, ParsedView, Portfolio, BottomUpView, TopDownView, AnalystNews } from '../types/blMainTypes';
import { apiClient } from '../../../services/apiClient';
import mockData from '../mock/mockBlMainData.json';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Call POST /bl/run and merge the chart fields into the mock skeleton so that
 * non-chart fields (analystSuggestions, analystNews, assets) are always
 * populated even when the backend hasn't computed them yet.
 */
async function _runAndMerge(): Promise<BLMainData> {
  const result = await apiClient.post<Partial<BLMainData>>('/bl/run', {});
  return {
    ...(mockData as BLMainData),          // fallback / static fields
    ...result,                             // live chart data overwrites mock
  };
}

export const blMainService = {
  /**
   * Initial data load — tries POST /bl/run and falls back to mock if the
   * backend isn't reachable or no recipe exists yet.
   */
  getBlackLittermanData: async (): Promise<BLMainData> => {
    try {
      return await _runAndMerge();
    } catch {
      // No backend / no current recipe — serve the static mock so the UI
      // shows something useful on first launch.
      return mockData as BLMainData;
    }
  },

  /**
   * Parse a natural language investment view via the backend.
   * POST /views/parse  — backend parses text and saves to current.json.
   */
  parseView: async (text: string): Promise<ParsedView[]> => {
    const response = await apiClient.post<{ view: ParsedView[] }>('/views/parse', { text });
    return response.view;
  },

  /**
   * Fetch the adapted view tables from current.json.
   * GET /views/current
   */
  getCurrentViews: async (): Promise<{ bottom_up: BottomUpView[]; top_down: TopDownView[] }> => {
    return apiClient.get<{ bottom_up: BottomUpView[]; top_down: TopDownView[] }>('/views/current');
  },

  /** GET /views/model_parameters — reads tau, risk_aversion, risk_free_rate from current.json */
  getModelParameters: async (): Promise<{ tau: number; risk_aversion: number; risk_free_rate: number }> => {
    return apiClient.get('/views/model_parameters');
  },

  /** PUT /views/model_parameters — persists updated params to current.json */
  updateModelParameters: async (params: { tau?: number; risk_aversion?: number; risk_free_rate?: number }): Promise<void> => {
    await apiClient.put('/views/model_parameters', params);
  },

  /** GET /views/constraints — reads long_only and weight_bounds from current.json */
  getConstraints: async (): Promise<{ long_only: boolean; weight_bounds: [number, number] }> => {
    return apiClient.get('/views/constraints');
  },

  /** PUT /views/constraints — persists updated constraints to current.json */
  updateConstraints: async (constraints: { long_only: boolean; weight_bounds: [number, number] }): Promise<void> => {
    await apiClient.put('/views/constraints', constraints);
  },

  /** DELETE /views/bottom_up/{index} — splices the row from current.json */
  deleteBottomUpView: async (index: number): Promise<void> => {
    await apiClient.delete(`/views/bottom_up/${index}`);
  },

  /** DELETE /views/top_down/{index} — splices the row from current.json */
  deleteTopDownView: async (index: number): Promise<void> => {
    await apiClient.delete(`/views/top_down/${index}`);
  },

  /**
   * Re-run BL optimisation and return fresh chart data merged with mock.
   * Called by the "Run" / "Refresh" button in the UI.
   */
  runOptimization: async (_params?: {
    views?: unknown[];
    controls?: unknown;
  }): Promise<BLMainData> => {
    return _runAndMerge();
  },
  /** POST /views/thesis — save a named copy of current.json */
  saveThesis: async (name: string): Promise<string> => {
    const res = await apiClient.post<{ name: string }>('/views/thesis', { name });
    return res.name;
  },
};

export const portfolioService = {
  getAll: async (): Promise<Portfolio[]> => {
    try {
      return await apiClient.get<Portfolio[]>('/portfolios');
    } catch {
      return (mockData as BLMainData).portfolios ?? [];
    }
  },

  create: async (portfolio: Omit<Portfolio, 'id'> & { id?: string }): Promise<Portfolio> => {
    return apiClient.post<Portfolio>('/portfolios', portfolio);
  },

  getById: async (id: string): Promise<Portfolio> => {
    return apiClient.get<Portfolio>(`/portfolios/${id}`);
  },

  remove: async (id: string): Promise<void> => {
    return apiClient.delete(`/portfolios/${id}`);
  },
};

export interface PriceHistory {
  dates: string[];
  prices: Record<string, number[]>;
}

export const priceHistoryService = {
  /** GET /bl/price-history — full historical close prices for all assets */
  get: async (): Promise<PriceHistory> => {
    return apiClient.get<PriceHistory>('/bl/price-history');
  },
};

export const universeService = {
  /** GET /views/universe — active asset tickers in current.json */
  getUniverse: async (): Promise<string[]> => {
    try {
      const res = await apiClient.get<{ assets: string[] }>('/views/universe');
      return res.assets;
    } catch {
      return [];
    }
  },

  /** PUT /views/universe — overwrite the universe asset list */
  setUniverse: async (assets: string[]): Promise<string[]> => {
    const res = await apiClient.put<{ assets: string[] }>('/views/universe', { assets });
    return res.assets;
  },
};

export const newsService = {
  /** GET /news — return cached items from news.json */
  getNews: async (keyword?: string, limit: number = 5): Promise<AnalystNews[]> => {
    try {
      const params = new URLSearchParams();
      if (keyword) params.append('keyword', keyword);
      params.append('limit', limit.toString());
      
      const response = await apiClient.get<{ items: AnalystNews[] }>(
        `/news?${params.toString()}`
      );
      return response.items;
    } catch {
      return [];
    }
  },

  /** POST /news/fetch — fetch fresh articles and generate translatedViews */
  fetchNews: async (): Promise<AnalystNews[]> => {
    const response = await apiClient.post<{ count: number; items: AnalystNews[] }>('/news/fetch', {});
    return response.items;
  },

  /** POST /news/{id}/add-view — parse translatedView and append to current.json */
  addNewsView: async (id: string): Promise<void> => {
    await apiClient.post(`/news/${id}/add-view`, {});
  },
};
