import React from 'react';
import { Table, Column } from '@shared/components/Table';
import type { MarketAssumptions } from '../types/modelAssumptionsTypes';
import './MarketCapsTable.css';

interface MarketCapsTableProps {
  data: MarketAssumptions;
}

interface Row {
  asset: string;
  cap: number;
}

export const MarketCapsTable: React.FC<MarketCapsTableProps> = ({ data }) => {
  const rows: Row[] = data.all_assets.map((asset) => ({ asset, cap: data.market_caps[asset] ?? 0 }));

  const columns: Column<Row>[] = [
    { key: 'asset', header: 'Asset' },
    {
      key: 'cap',
      header: 'Market Cap ($B)',
      render: (row) => row.cap.toLocaleString(),
    },
  ];

  return <Table data={rows} columns={columns} className="market-caps-table" />;
};
