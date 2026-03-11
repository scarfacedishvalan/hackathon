import { useState, useCallback, useEffect, useMemo } from 'react';
import { blMainService, portfolioService } from '../services/blMainService';
import type { BottomUpView, TopDownView, BLMainData, Portfolio } from '../types/blMainTypes';

interface UseBLMainReturn {
  data: BLMainData | null;
  loading: boolean;
  runLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  bottomUpViews: BottomUpView[];
  topDownViews: TopDownView[];
  parseView: (text: string) => Promise<void>;
  parseViewLoading: boolean;
  parseViewError: Error | null;
  loadViews: () => Promise<void>;
  deleteBottomUpView: (id: string) => Promise<void>;
  deleteTopDownView: (id: string) => Promise<void>;
  portfolios: Portfolio[];
  portfoliosLoading: boolean;
  createPortfolio: (portfolio: Omit<Portfolio, 'id'> & { id?: string }) => Promise<void>;
  deletePortfolio: (id: string) => Promise<void>;
  selectedPortfolioId: string | null;
  setSelectedPortfolioId: (id: string | null) => void;
  selectedPortfolio: Portfolio | null;
}

export const useBLMain = (): UseBLMainReturn => {
  const [data, setData] = useState<BLMainData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const [runLoading, setRunLoading] = useState<boolean>(false);

  const [bottomUpViews, setBottomUpViews] = useState<BottomUpView[]>([]);
  const [topDownViews, setTopDownViews] = useState<TopDownView[]>([]);
  const [parseViewLoading, setParseViewLoading] = useState<boolean>(false);
  const [parseViewError, setParseViewError] = useState<Error | null>(null);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfoliosLoading, setPortfoliosLoading] = useState<boolean>(false);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(null);

  const selectedPortfolio = useMemo(
    () => portfolios.find(p => p.id === selectedPortfolioId) ?? null,
    [portfolios, selectedPortfolioId]
  );

  // ── Load views from backend (adapts current.json) ──────────────────────────

  const loadViews = useCallback(async () => {
    try {
      const { bottom_up, top_down } = await blMainService.getCurrentViews();
      setBottomUpViews(bottom_up);
      setTopDownViews(top_down);
    } catch (err) {
      console.error('Error loading views from backend:', err);
    }
  }, []);

  // ── Portfolio helpers ───────────────────────────────────────────────────────

  const loadPortfolios = useCallback(async () => {
    setPortfoliosLoading(true);
    try {
      const result = await portfolioService.getAll();
      setPortfolios(result);
    } finally {
      setPortfoliosLoading(false);
    }
  }, []);

  const createPortfolio = useCallback(async (portfolio: Omit<Portfolio, 'id'> & { id?: string }) => {
    const created = await portfolioService.create(portfolio);
    setPortfolios(prev => [...prev, created]);
  }, []);

  const deletePortfolio = useCallback(async (id: string) => {
    await portfolioService.remove(id);
    setPortfolios(prev => prev.filter(p => p.id !== id));
  }, []);

  // ── BL data fetch ───────────────────────────────────────────────────────────

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
      setRunLoading(true);
      setError(null);
      const result = await blMainService.runOptimization();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error running BL optimization:', err);
    } finally {
      setRunLoading(false);
    }
  }, []);

  // ── Mount ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchData();
    loadPortfolios();
    loadViews();
  }, [fetchData, loadPortfolios, loadViews]);

  // ── Parse view ──────────────────────────────────────────────────────────────

  const parseView = useCallback(async (text: string) => {
    try {
      setParseViewLoading(true);
      setParseViewError(null);
      // Backend parses text and saves to current.json
      await blMainService.parseView(text);
      // Reload the adapted views from current.json
      await loadViews();
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Failed to parse view');
      setParseViewError(e);
      console.error('Error parsing view:', err);
    } finally {
      setParseViewLoading(false);
    }
  }, [loadViews]);

  // ── Delete views — persisted to current.json via backend ───────────────────

  const deleteBottomUpView = useCallback(async (id: string) => {
    // id format is "bu-{index}" — extract the array index
    const index = parseInt(id.split('-')[1], 10);
    try {
      await blMainService.deleteBottomUpView(index);
      await loadViews();
    } catch (err) {
      console.error('Error deleting bottom-up view:', err);
    }
  }, [loadViews]);

  const deleteTopDownView = useCallback(async (id: string) => {
    // id format is "td-{index}" — extract the array index
    const index = parseInt(id.split('-')[1], 10);
    try {
      await blMainService.deleteTopDownView(index);
      await loadViews();
    } catch (err) {
      console.error('Error deleting top-down view:', err);
    }
  }, [loadViews]);

  return {
    data,
    loading,
    runLoading,
    error,
    refetch,
    bottomUpViews,
    topDownViews,
    parseView,
    parseViewLoading,
    parseViewError,
    loadViews,
    deleteBottomUpView,
    deleteTopDownView,
    portfolios,
    portfoliosLoading,
    createPortfolio,
    deletePortfolio,
    selectedPortfolioId,
    setSelectedPortfolioId,
    selectedPortfolio,
  };
};
