import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { ChartWrapper } from '@shared/components';
import type { AllocationData } from '../types/blMainTypes';

interface BLAllocationChartProps {
  data: AllocationData[];
}

export const BLAllocationChart: React.FC<BLAllocationChartProps> = ({
  data,
}) => {
  // Transform data for grouped bar chart
  const chartData = data.map((item) => ({
    ticker: item.ticker,
    'Prior Weight': item.priorWeight * 100,
    'BL Weight': item.blWeight * 100,
  }));

  return (
    <ChartWrapper title="Portfolio Allocation: Prior vs Black-Litterman">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="ticker"
            tick={{ fontSize: 13, fill: '#94a3b8' }}
          />
          <YAxis
            tickFormatter={(value) => `${value.toFixed(0)}%`}
            tick={{ fill: '#94a3b8' }}
            label={{
              value: 'Weight (%)',
              angle: -90,
              position: 'insideLeft',
              fill: '#e0e6ed',
            }}
          />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(2)}%`}
            contentStyle={{
              backgroundColor: '#1e2530',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#e0e6ed',
            }}
          />
          <Legend
            verticalAlign="top"
            height={36}
            wrapperStyle={{ color: '#94a3b8' }}
          />
          <Bar
            dataKey="Prior Weight"
            fill="#f59e0b"
            radius={[4, 4, 0, 0]}
          />
          <Bar
            dataKey="BL Weight"
            fill="#60a5fa"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
};
