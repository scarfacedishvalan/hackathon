import { useCallback, useEffect, useRef, useState } from 'react';
import { modelAssumptionsService } from '../services/modelAssumptionsService';
import type { MarketAssumptions, MarketAssumptionsUpdate } from '../types/modelAssumptionsTypes';

const DEBOUNCE_MS = 500;

export function useModelAssumptions() {
  const [data, setData] = useState<MarketAssumptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Accumulates edits between debounce fires so only the changed keys are sent.
  const pending = useRef<MarketAssumptionsUpdate>({});
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    modelAssumptionsService
      .getAssumptions()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const scheduleSave = useCallback(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(async () => {
      const payload = pending.current;
      pending.current = {};
      setSaving(true);
      try {
        const updated = await modelAssumptionsService.updateAssumptions(payload);
        setData(updated);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  const updateMarketCap = useCallback(
    (asset: string, value: number) => {
      setData((prev) => (prev ? { ...prev, market_caps: { ...prev.market_caps, [asset]: value } } : prev));
      pending.current.market_caps = { ...pending.current.market_caps, [asset]: value };
      scheduleSave();
    },
    [scheduleSave],
  );

  const updateFactorExposure = useCallback(
    (asset: string, factorIndex: number, value: number) => {
      setData((prev) => {
        if (!prev) return prev;
        const row = [...(prev.factor_exposures[asset] ?? [])];
        row[factorIndex] = value;
        pending.current.factor_exposures = { ...pending.current.factor_exposures, [asset]: row };
        return { ...prev, factor_exposures: { ...prev.factor_exposures, [asset]: row } };
      });
      scheduleSave();
    },
    [scheduleSave],
  );

  const refreshMarketCaps = useCallback(async () => {
    setRefreshing(true);
    try {
      const updated = await modelAssumptionsService.refreshMarketCaps();
      setData(updated);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRefreshing(false);
    }
  }, []);

  return { data, loading, error, saving, refreshing, updateMarketCap, updateFactorExposure, refreshMarketCaps };
}
