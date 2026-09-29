import React, { useState, useEffect, useRef } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { priceHistoryService, type PriceHistory } from '@features/bl_main/services/blMainService';
import './PriceHistoryPanel.css';

const TICKER_COLORS: Record<string, string> = {
  AAPL:  '#60a5fa',
  AMZN:  '#34d399',
  BAC:   '#f59e0b',
  BND:   '#a78bfa',
  GLD:   '#fbbf24',
  GOOGL: '#fb7185',
  JNJ:   '#2dd4bf',
  JPM:   '#f97316',
  MSFT:  '#818cf8',
  PG:    '#86efac',
  TSLA:  '#f43f5e',
  VNQ:   '#e879f9',
  WMT:   '#38bdf8',
};

// Copied from AssetSelection.tsx's buildChartData — rebases all tickers to 100 at the start date.
function buildChartData(
  history: PriceHistory,
  tickers: string[],
  normalize: boolean,
): { date: string; [ticker: string]: number | string }[] {
  if (!history.dates.length || !tickers.length) return [];

  const activeTickers = tickers.filter((t) => t in history.prices);
  const startIdx = 0;

  const base: Record<string, number> = {};
  if (normalize) {
    for (const t of activeTickers) {
      base[t] = history.prices[t][startIdx] || 1;
    }
  }

  // Sample every Nth point to keep the chart responsive (~300 points max)
  const total = history.dates.length - startIdx;
  const step = Math.max(1, Math.floor(total / 300));

  const result: { date: string; [ticker: string]: number | string }[] = [];
  for (let i = startIdx; i < history.dates.length; i += step) {
    const point: { date: string; [ticker: string]: number | string } = {
      date: history.dates[i],
    };
    for (const t of activeTickers) {
      const raw = history.prices[t][i];
      point[t] = normalize ? parseFloat(((raw / base[t]) * 100).toFixed(2)) : parseFloat(raw.toFixed(2));
    }
    result.push(point);
  }
  return result;
}

function formatDateTick(value: string): string {
  return value ? value.slice(0, 4) : '';
}

interface PriceHistoryPanelProps {
  tickers: string[];
}

export const PriceHistoryPanel: React.FC<PriceHistoryPanelProps> = ({ tickers }) => {
  const [normalize, setNormalize] = useState(true);
  const [priceHistory, setPriceHistory] = useState<PriceHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    priceHistoryService
      .get()
      .then(setPriceHistory)
      .catch(() => setPriceHistory(null))
      .finally(() => setLoading(false));
  }, []);

  const chartData = priceHistory ? buildChartData(priceHistory, tickers, normalize) : [];

  return (
    <div className="price-history-panel">
      <div className="price-history-header">
        <span className="price-history-title">Price History</span>
        <label className="normalize-toggle">
          <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} />
          <span>Normalise to 100</span>
        </label>
      </div>

      {loading ? (
        <div className="price-history-loading">Loading price data…</div>
      ) : !priceHistory ? (
        <div className="price-history-loading">Price data unavailable</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3540" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateTick}
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={52}
              tickFormatter={(v: number) => (normalize ? `${v}` : v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`)}
            />
            <Tooltip
              contentStyle={{ background: '#1e2530', border: '1px solid #334155', borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
              itemStyle={{ color: '#e0e6ed' }}
              formatter={(value: number, name: string) => [normalize ? value.toFixed(2) : `$${value.toFixed(2)}`, name]}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 4 }} />
            {tickers
              .filter((t) => t in (priceHistory?.prices ?? {}))
              .map((ticker) => (
                <Line
                  key={ticker}
                  type="monotone"
                  dataKey={ticker}
                  stroke={TICKER_COLORS[ticker] ?? '#94a3b8'}
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
              ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
