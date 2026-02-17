// Core BL Types

export interface Asset {
  ticker: string;
  name: string;
  weight: number;
  selected?: boolean;
}

export interface ActiveView {
  id?: string;
  type: 'relative' | 'absolute';
  asset: string;
  value?: number;
  direction: 'positive' | 'negative' | 'neutral';
  confidence: number;
  expectedReturn?: number;
}

export interface AnalystSuggestion {
  ticker: string;
  text: string;
  sentiment?: 'bullish' | 'bearish' | 'neutral';
}

export interface AnalystNews {
  id: number;
  heading: string;
  translatedView: string;
  link: string;
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
  activeViews: ActiveView[];
  analystSuggestions: AnalystSuggestion[];
  analystNews?: AnalystNews[];
  efficientFrontier: EfficientFrontier;
  allocation: AllocationData[];
  topDownContribution: SectorContribution[];
  portfolios?: Portfolio[];
}

export interface ModelControlsConfig {
  riskAversion: number;
  confidenceScaling: 'low' | 'medium' | 'high';
}
