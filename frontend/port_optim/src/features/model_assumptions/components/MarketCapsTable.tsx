import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { MarketAssumptions } from '../types/modelAssumptionsTypes';

const BAR_COLORS = [
  '#60a5fa', '#34d399', '#f59e0b', '#a78bfa', '#fbbf24', '#fb7185', '#2dd4bf',
  '#f97316', '#818cf8', '#86efac', '#f43f5e', '#e879f9', '#38bdf8',
];

interface MarketCapsTableProps {
  data: MarketAssumptions;
}

export const MarketCapsTable: React.FC<MarketCapsTableProps> = ({ data }) => {
  const chartData = data.all_assets
    .map((asset) => ({ asset, cap: data.market_caps[asset] ?? 0 }))
    .sort((a, b) => b.cap - a.cap);

  return (
    <ResponsiveContainer width="100%" height={Math.max(220, chartData.length * 28)}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          type="number"
          tickFormatter={(v: number) => `$${v.toLocaleString()}B`}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
        />
        <YAxis type="category" dataKey="asset" width={56} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <Tooltip
          formatter={(value: number) => [`$${value.toLocaleString()}B`, 'Market Cap']}
          contentStyle={{ background: '#1e2530', border: '1px solid #334155', borderRadius: 6, fontSize: 12 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Bar dataKey="cap" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={entry.asset} fill={BAR_COLORS[index % BAR_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
