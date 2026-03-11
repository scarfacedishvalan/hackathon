import type { SectorContribution } from '../types/blMainTypes';

/**
 * Aggregate asset-level data to sector/top-down view
 * Groups individual assets by sector and sums contributions
 */
export const computeTopDownAggregation = (
  assetContributions: Array<{
    asset: string;
    sector: string;
    returnContribution: number;
    riskContribution: number;
  }>
): SectorContribution[] => {
  const sectorMap = new Map<string, SectorContribution>();

  assetContributions.forEach((item) => {
    const existing = sectorMap.get(item.sector);
    if (existing) {
      existing.returnContribution += item.returnContribution;
      existing.riskContribution += item.riskContribution;
    } else {
      sectorMap.set(item.sector, {
        sector: item.sector,
        returnContribution: item.returnContribution,
        riskContribution: item.riskContribution,
      });
    }
  });

  return Array.from(sectorMap.values()).sort(
    (a, b) => b.returnContribution - a.returnContribution
  );
};
