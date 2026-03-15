// Core BL Types

export interface Asset {
  ticker: string;
  name: string;
  weight: number;
  selected?: boolean;
}

/** @deprecated Use BottomUpView / TopDownView instead */
export interface ActiveView {
  id?: string;
  type: 'relative' | 'absolute';
  asset: string;
  value?: number;
  direction: 'positive' | 'negative' | 'neutral';
  confidence: number;
  expectedReturn?: number;
}

/** A bottom-up analyst view (absolute or relative). */
export interface BottomUpView {
  id: string;
  type: 'absolute' | 'relative';
  /** Absolute view: single ticker */
  asset?: string;
  /** Relative view: long leg */
  asset_long?: string;
  /** Relative view: short leg */
  asset_short?: string;
  /** Signed value: expected_return (absolute) or expected_outperformance (relative) */
  value: number;
  confidence: number;
  label?: string;
}

/** A top-down macro/factor view. */
export interface TopDownView {
  id: string;
  factor: string;
  shock: number;
  confidence: number;
  label?: string;
}

export interface AnalystSuggestion {
  ticker: string;
  text: string;
  sentiment?: 'bullish' | 'bearish' | 'neutral';
}

export interface AnalystNews {
  id: string;
  heading: string;
  translatedView: string;
  link: string;
  source?: string;
  ticker?: string;
  fetched_at?: string;
}

export interface EfficientFrontierPoint {
  vol: number;
  ret: number;
}

export interface EfficientFrontier {
  curve: EfficientFrontierPoint[];
  prior: EfficientFrontierPoint;
  posterior: EfficientFrontierPoint;
}

export interface AllocationData {
  ticker: string;
  priorWeight: number;
  blWeight: number;
}

export interface SectorContribution {
  sector: string;
  returnContribution: number;
  riskContribution: number;
}

export interface PortfolioSnapshot {
  ret: number;
  vol: number;
  sharpe: number;
  var95: number;
}

export interface PortfolioStats {
  prior: PortfolioSnapshot;
  posterior: PortfolioSnapshot;
}

export interface CalculationStep {
  title: string;
  latex: string;
}

export interface PortfolioHolding {
  ticker: string;
  weight: number;
}

export interface Portfolio {
  id: string;
  name: string;
  holdings: PortfolioHolding[];
}

export interface BLMainData {
  assets: Asset[];
  analystSuggestions: AnalystSuggestion[];
  analystNews?: AnalystNews[];
  efficientFrontier: EfficientFrontier;
  allocation: AllocationData[];
  topDownContribution: SectorContribution[];
  portfolioStats?: PortfolioStats;
  calculationSteps?: CalculationStep[];
  portfolios?: Portfolio[];
}

export interface ModelControlsConfig {
  riskAversion: number;
  confidenceScaling: 'low' | 'medium' | 'high';
}

export interface ParsedView {
  type: 'relative' | 'absolute' | 'factor';
  asset_long?: string;
  asset_short?: string;
  asset?: string;
  factor?: string;
  alpha?: number;
  confidence?: number;
  label?: string;
}
