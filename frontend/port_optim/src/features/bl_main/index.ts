export { BLMainPage } from './pages/BLMainPage';
export * from './components';
export { useBLMain, BLMainProvider } from './context/BLMainContext';

// Export types explicitly to avoid naming conflict with PortfolioStats component
export type {
  Asset,
  ActiveView,
  BottomUpView,
  TopDownView,
  AnalystSuggestion,
  AnalystNews,
  EfficientFrontierPoint,
  EfficientFrontier,
  AllocationData,
  SectorContribution,
  PortfolioSnapshot,
  PortfolioStats,
  CalculationStep,
  PortfolioHolding,
  Portfolio,
  BLMainData,
  ModelControlsConfig,
  ParsedView,
} from './types/blMainTypes';
