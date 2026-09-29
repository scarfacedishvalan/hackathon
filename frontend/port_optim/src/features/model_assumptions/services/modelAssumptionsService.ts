import { apiClient } from '../../../services/apiClient';
import type { MarketAssumptions, MarketAssumptionsUpdate } from '../types/modelAssumptionsTypes';

export const modelAssumptionsService = {
  /** GET /market-data/assumptions — all_assets, factor_names, market_caps, factor_exposures. */
  getAssumptions: (): Promise<MarketAssumptions> =>
    apiClient.get<MarketAssumptions>('/market-data/assumptions'),

  /** PUT /market-data/assumptions — persists partial edits to market_data.json. */
  updateAssumptions: (payload: MarketAssumptionsUpdate): Promise<MarketAssumptions> =>
    apiClient.put<MarketAssumptions>('/market-data/assumptions', payload),
};
