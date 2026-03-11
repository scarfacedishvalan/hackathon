import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { ChartWrapper } from '@shared/components';
import type { SectorContribution } from '../types/blMainTypes';
import './TopDownContribution.css';

interface TopDownContributionProps {
  data: SectorContribution[];
}

export const TopDownContribution: React.FC<TopDownContributionProps> = ({
  data,
}) => {
  const [mode, setMode] = useState<'return' | 'risk'>('return');

  const chartData = data.map((item) => ({
    sector: item.sector,
    value: mode === 'return' 
      ? item.returnContribution * 100 
      : item.riskContribution * 100,
  }));

  // Color scale
  const getColor = (index: number) => {
    const colors = ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'];
    return colors[index % colors.length];
  };

  return (
    <ChartWrapper title="Top-Down Contribution Analysis">
      <div className="contribution-controls">
        <div className="toggle-group">
          <button
            className={`toggle-btn ${mode === 'return' ? 'active' : ''}`}
            onClick={() => setMode('return')}
          >
            Return
          </button>
          <button
            className={`toggle-btn ${mode === 'risk' ? 'active' : ''}`}
            onClick={() => setMode('risk')}
          >
            Risk
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 20, right: 30, bottom: 20, left: 100 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            type="number"
            tickFormatter={(value) => `${value.toFixed(1)}%`}
            label={{
              value: mode === 'return' ? 'Return Contribution (%)' : 'Risk Contribution (%)',
              position: 'insideBottom',
              offset: -10,
            }}
          />
          <YAxis
            type="category"
            dataKey="sector"
            width={90}
          />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(2)}%`}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
};
