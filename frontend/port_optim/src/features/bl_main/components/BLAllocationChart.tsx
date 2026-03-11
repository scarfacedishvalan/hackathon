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
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="ticker"
            tick={{ fontSize: 13 }}
          />
          <YAxis
            tickFormatter={(value) => `${value.toFixed(0)}%`}
            label={{
              value: 'Weight (%)',
              angle: -90,
              position: 'insideLeft',
            }}
          />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(2)}%`}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
            }}
          />
          <Legend
            verticalAlign="top"
            height={36}
          />
          <Bar
            dataKey="Prior Weight"
            fill="#f59e0b"
            radius={[4, 4, 0, 0]}
          />
          <Bar
            dataKey="BL Weight"
            fill="#2563eb"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
};
