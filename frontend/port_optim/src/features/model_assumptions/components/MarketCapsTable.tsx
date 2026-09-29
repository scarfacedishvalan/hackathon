import React from 'react';
import { Table, Column } from '@shared/components/Table';
import type { MarketAssumptions } from '../types/modelAssumptionsTypes';
import './MarketCapsTable.css';

interface MarketCapsTableProps {
  data: MarketAssumptions;
  onChange: (asset: string, value: number) => void;
}

interface Row {
  asset: string;
  cap: number;
}

export const MarketCapsTable: React.FC<MarketCapsTableProps> = ({ data, onChange }) => {
  const rows: Row[] = data.all_assets.map((asset) => ({ asset, cap: data.market_caps[asset] ?? 0 }));

  const columns: Column<Row>[] = [
    { key: 'asset', header: 'Asset' },
    {
      key: 'cap',
      header: 'Market Cap ($B)',
      render: (row) => (
        <input
          type="number"
          min="0"
          step="1"
          value={row.cap}
          onChange={(e) => onChange(row.asset, Number(e.target.value))}
          className="assumptions-input"
        />
      ),
    },
  ];

  return <Table data={rows} columns={columns} className="market-caps-table" />;
};
