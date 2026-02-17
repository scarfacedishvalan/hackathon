import { useState, useCallback, useEffect } from 'react';
import { blMainService } from '../services/blMainService';
import type { BLMainData } from '../types/blMainTypes';

interface UseBLMainReturn {
  data: BLMainData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook for managing Black-Litterman data
 * Handles loading state and provides refetch capability
 */
export const useBLMain = (): UseBLMainReturn => {
  const [data, setData] = useState<BLMainData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await blMainService.getBlackLittermanData();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error fetching BL data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      // In production, this would include current views and controls
      const result = await blMainService.runOptimization();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error running BL optimization:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
};
