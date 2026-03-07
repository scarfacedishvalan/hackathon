import type { BLMainData, ParsedView, Portfolio, ActiveView } from '../types/blMainTypes';
import { apiClient } from '../../../services/apiClient';
import mockData from '../mock/mockBlMainData.json';

/**
 * Service layer for Black-Litterman data
 * Currently uses mock data but structured for easy backend integration
 */
export const blMainService = {
  /**
   * Fetch Black-Litterman data
   * Replace with apiClient.get('/bl') for real backend
   */
  getBlackLittermanData: async (): Promise<BLMainData> => {
    // Simulate network delay
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(mockData as BLMainData);
      }, 500);
    });
  },

  /**
   * Parse a natural language investment view via the backend.
   * POST /views/parse
   */
  parseView: async (text: string): Promise<ParsedView[]> => {
    const response = await apiClient.post<{ view: ParsedView[] }>('/views/parse', { text });
    return response.view;
  },

  /**
   * Sync the full active-views list to the server so current.json always
   * mirrors what the UI is showing.
   * PUT /views/current
   */
  syncCurrentViews: async (views: ActiveView[]): Promise<void> => {
    await apiClient.put('/views/current', { views });
  },

  /**
   * Run Black-Litterman optimization
   * This would send views and controls to backend
   */
  runOptimization: async (params?: {
    views?: unknown[];
    controls?: unknown;
  }): Promise<BLMainData> => {
    // Future implementation:
    // return apiClient.post('/bl/run', params);
    
    // For now, simulate optimization by returning mock data
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log('Running optimization with params:', params);
        resolve(mockData as BLMainData);
      }, 800);
    });
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
