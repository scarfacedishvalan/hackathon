import type { BLMainData, ParsedView } from '../types/blMainTypes';
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
