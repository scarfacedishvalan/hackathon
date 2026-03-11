// ── Stepper ──────────────────────────────────────────────────────────────
export type BacktestStep = 'input' | 'review' | 'results';

// ── Recipe (mirrors BacktestingRecipe Pydantic schema) ────────────────────
export interface BacktestRecipeData {
  symbol: string | null;
  source: string | null;
  path:   string | null;
  start:  string | null;
  end:    string | null;
}

export interface BacktestRecipeBacktest {
  cash:             number | null;
  commission:       string | number | null;
  margin:           number | null;
  trade_on_close:   boolean | null;
  hedging:          boolean | null;
  exclusive_orders: boolean | null;
}

export interface BacktestRecipeRules {
  entry: string | null;
  exit:  string | null;
}

export interface BacktestRecipeRisk {
  stop_loss:      number | string | null;
  take_profit:    number | string | null;
  trailing_stop:  number | string | null;
}

export interface BacktestRecipeOptimize {
  metric:     string | null;
  maximize:   boolean | null;
  constraint: string | null;
  params:     Record<string, number[]> | null;
}

export interface BacktestRecipe {
  strategy_name:   string | null;
  timeframe:       string | null;
  data:            BacktestRecipeData;
  backtest:        BacktestRecipeBacktest;
  strategy_params: Record<string, number> | null;
  rules:           BacktestRecipeRules;
  risk:            BacktestRecipeRisk;
  optimize:        BacktestRecipeOptimize;
}

// ── Run result (mirrors backtest_orchestrator serialised output) ───────────
export interface BacktestMetrics {
  start:               string | null;
  end:                 string | null;
  duration:            string | null;
  equityFinal:         number | null;
  equityPeak:          number | null;
  returnPct:           number | null;
  buyHoldReturnPct:    number | null;
  annualReturnPct:     number | null;
  annualVolatilityPct: number | null;
  sharpeRatio:         number | null;
  sortinoRatio:        number | null;
  calmarRatio:         number | null;
  maxDrawdownPct:      number | null;
  avgDrawdownPct:      number | null;
  numTrades:           number | null;
  winRatePct:          number | null;
  bestTradePct:        number | null;
  worstTradePct:       number | null;
  avgTradePct:         number | null;
  profitFactor:        number | null;
  sqn:                 number | null;
}

export interface EquityCurvePoint {
  date:   string;
  equity: number;
}

export interface BacktestTrade {
  entryTime:  string;
  exitTime:   string;
  entryPrice: number | null;
  exitPrice:  number | null;
  pnl:        number | null;
  returnPct:  number | null;
  size:       number | null;
}

export interface BacktestRunResult {
  recipe:     BacktestRecipe;
  metrics:    BacktestMetrics;
  equityCurve: EquityCurvePoint[];
  trades:     BacktestTrade[];
}

