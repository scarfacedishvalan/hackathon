import { apiClient } from '../../../services/apiClient';
import type { MarketAssumptions, MarketAssumptionsUpdate, CorrelationMatrix } from '../types/modelAssumptionsTypes';

export const modelAssumptionsService = {
  /** GET /market-data/assumptions — all_assets, factor_names, market_caps, factor_exposures. */
  getAssumptions: (): Promise<MarketAssumptions> =>
    apiClient.get<MarketAssumptions>('/market-data/assumptions'),

  /** PUT /market-data/assumptions — persists partial edits to market_data.json. */
  updateAssumptions: (payload: MarketAssumptionsUpdate): Promise<MarketAssumptions> =>
    apiClient.put<MarketAssumptions>('/market-data/assumptions', payload),

  /** GET /market-data/correlations — annualized correlation matrix + per-asset volatility. */
  getCorrelations: (frequency: number, horizon: string): Promise<CorrelationMatrix> =>
    apiClient.get<CorrelationMatrix>(`/market-data/correlations?frequency=${frequency}&horizon=${horizon}`),

  /** POST /market-data/refresh-caps — stub; currently a no-op, returns assumptions unchanged. */
  refreshMarketCaps: (): Promise<MarketAssumptions> =>
    apiClient.post<MarketAssumptions>('/market-data/refresh-caps', {}),
};
