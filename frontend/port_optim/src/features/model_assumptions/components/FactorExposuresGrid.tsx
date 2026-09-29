import React from 'react';
import { Table, Column } from '@shared/components/Table';
import type { MarketAssumptions } from '../types/modelAssumptionsTypes';
import './FactorExposuresGrid.css';

interface FactorExposuresGridProps {
  data: MarketAssumptions;
  onChange: (asset: string, factorIndex: number, value: number) => void;
}

interface Row {
  asset: string;
  exposures: number[];
}

export const FactorExposuresGrid: React.FC<FactorExposuresGridProps> = ({ data, onChange }) => {
  const rows: Row[] = data.all_assets.map((asset) => ({
    asset,
    exposures: data.factor_exposures[asset] ?? data.factor_names.map(() => 0),
  }));

  const columns: Column<Row>[] = [
    { key: 'asset', header: 'Asset' },
    ...data.factor_names.map((factorName, factorIndex) => ({
      key: `factor-${factorIndex}`,
      header: factorName,
      render: (row: Row) => (
        <input
          type="number"
          step="0.1"
          value={row.exposures[factorIndex] ?? 0}
          onChange={(e) => onChange(row.asset, factorIndex, Number(e.target.value))}
          className="assumptions-input"
        />
      ),
    })),
  ];

  return <Table data={rows} columns={columns} className="factor-exposures-grid" />;
};
