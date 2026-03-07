import { useState, useCallback, useEffect, useMemo } from 'react';
import { blMainService, portfolioService } from '../services/blMainService';
import type { ActiveView, BLMainData, ParsedView, Portfolio } from '../types/blMainTypes';

const STORAGE_KEY = 'bl_active_views';

interface UseBLMainReturn {
  data: BLMainData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  activeViews: ActiveView[];
  parseView: (text: string) => Promise<void>;
  parseViewLoading: boolean;
  parseViewError: Error | null;
  deleteView: (id: string) => void;
  portfolios: Portfolio[];
  portfoliosLoading: boolean;
  createPortfolio: (portfolio: Omit<Portfolio, 'id'> & { id?: string }) => Promise<void>;
  deletePortfolio: (id: string) => Promise<void>;
  selectedPortfolioId: string | null;
  setSelectedPortfolioId: (id: string | null) => void;
  selectedPortfolio: Portfolio | null;
}

/** Map a ParsedView from the backend into the local ActiveView shape. */
function toActiveView(parsed: ParsedView): ActiveView {
  const alpha = parsed.alpha ?? 0;
  const direction: ActiveView['direction'] =
    alpha > 0 ? 'positive' : alpha < 0 ? 'negative' : 'neutral';

  const viewType: ActiveView['type'] =
    parsed.type === 'relative' ? 'relative' : 'absolute';

  const asset =
    parsed.type === 'relative' && parsed.asset_long && parsed.asset_short
      ? `${parsed.asset_long} vs ${parsed.asset_short}`
      : parsed.asset_long ?? parsed.asset ?? parsed.factor ?? '';

  return {
    id: `parsed-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    type: viewType,
    asset,
    value: Math.abs(alpha),
    direction,
    confidence: parsed.confidence ?? 0,
    expectedReturn: alpha,
  };
}

/**
 * Custom hook for managing Black-Litterman data
 * Handles loading state and provides refetch capability
 */
export const useBLMain = (): UseBLMainReturn => {
  const [data, setData] = useState<BLMainData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const [activeViews, setActiveViews] = useState<ActiveView[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const [parseViewLoading, setParseViewLoading] = useState<boolean>(false);
  const [parseViewError, setParseViewError] = useState<Error | null>(null);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfoliosLoading, setPortfoliosLoading] = useState<boolean>(false);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(null);

  const selectedPortfolio = useMemo(
    () => portfolios.find(p => p.id === selectedPortfolioId) ?? null,
    [portfolios, selectedPortfolioId]
  );

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

  // Persist to localStorage whenever activeViews changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(activeViews));
  }, [activeViews]);

  // Only seed from fetched data if localStorage is empty
  useEffect(() => {
    if (data?.activeViews && activeViews.length === 0) {
      setActiveViews(data.activeViews);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  useEffect(() => {
    fetchData();
    loadPortfolios();
  }, [fetchData, loadPortfolios]);

  const parseView = useCallback(async (text: string) => {
    try {
      setParseViewLoading(true);
      setParseViewError(null);
      const parsedViews = await blMainService.parseView(text);
      const newViews = parsedViews.map(toActiveView);
      setActiveViews(prev => [...prev, ...newViews]);
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Failed to parse view');
      setParseViewError(e);
      console.error('Error parsing view:', err);
    } finally {
      setParseViewLoading(false);
    }
  }, []);

  const deleteView = useCallback((id: string) => {
    setActiveViews(prev => prev.filter(v => v.id !== id));
  }, []);

  return { data, loading, error, refetch, activeViews, parseView, parseViewLoading, parseViewError, deleteView, portfolios, portfoliosLoading, createPortfolio, deletePortfolio, selectedPortfolioId, setSelectedPortfolioId, selectedPortfolio };
};
