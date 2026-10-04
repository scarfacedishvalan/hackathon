export interface MarketAssumptions {
  all_assets: string[];
  factor_names: string[];
  market_caps: Record<string, number>;
  factor_exposures: Record<string, number[]>;
}

export interface MarketAssumptionsUpdate {
  market_caps?: Record<string, number>;
  factor_exposures?: Record<string, number[]>;
}

export interface CorrelationMatrix {
  assets: string[];
  frequency: number;
  horizon: string;
  correlation: number[][];
  annualized_volatility: Record<string, number>;
}
