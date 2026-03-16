import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { ChartWrapper } from '@shared/components';
import type { EfficientFrontier } from '../types/blMainTypes';

interface EfficientFrontierChartProps {
  data: EfficientFrontier;
}

export const EfficientFrontierChart: React.FC<EfficientFrontierChartProps> = ({
  data,
}) => {
  return (
    <ChartWrapper title="Efficient Frontier">
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart
          margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            dataKey="vol"
            name="Volatility"
            domain={[0, 'auto']}
            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
            tick={{ fill: '#94a3b8' }}
            label={{
              value: 'Volatility (σ)',
              position: 'insideBottom',
              offset: -10,
              fill: '#e0e6ed',
            }}
          />
          <YAxis
            type="number"
            dataKey="ret"
            name="Return"
            domain={[0, 'auto']}
            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
            tick={{ fill: '#94a3b8' }}
            label={{
              value: 'Expected Return',
              angle: -90,
              position: 'insideLeft',
              fill: '#e0e6ed',
            }}
          />
          <Tooltip
            formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
            labelFormatter={() => ''}
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
            iconType="circle"
          />
          
          {/* Efficient Frontier Curve */}
          <Scatter
            name="Efficient Frontier"
            data={data.curve}
            fill="#94a3b8"
            line={{ stroke: '#64748b', strokeWidth: 2 }}
            shape="circle"
          />
          
          {/* Prior Portfolio */}
          <ReferenceDot
            x={data.prior.vol}
            y={data.prior.ret}
            r={8}
            fill="#f59e0b"
            stroke="#d97706"
            strokeWidth={2}
            label={{
              value: 'Prior',
              position: 'top',
              fill: '#fbbf24',
              fontSize: 12,
              fontWeight: 600,
            }}
          />
          
          {/* Posterior (BL) Portfolio */}
          <ReferenceDot
            x={data.posterior.vol}
            y={data.posterior.ret}
            r={8}
            fill="#60a5fa"
            stroke="#3b82f6"
            strokeWidth={2}
            label={{
              value: 'BL Posterior',
              position: 'top',
              fill: '#93c5fd',
              fontSize: 12,
              fontWeight: 600,
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
};
