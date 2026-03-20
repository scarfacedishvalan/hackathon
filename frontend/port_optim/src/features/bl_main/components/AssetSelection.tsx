import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { universeService, priceHistoryService, type PriceHistory } from '../services/blMainService';
import './AssetSelection.css';

/** Full asset universe sourced from backend/data/market_data.json */
const FULL_UNIVERSE = [
  { ticker: 'AAPL',  name: 'Apple Inc.' },
  { ticker: 'AMZN',  name: 'Amazon.com Inc.' },
  { ticker: 'BAC',   name: 'Bank of America' },
  { ticker: 'BND',   name: 'Vanguard Total Bond' },
  { ticker: 'GLD',   name: 'SPDR Gold Shares' },
  { ticker: 'GOOGL', name: 'Alphabet Inc.' },
  { ticker: 'JNJ',   name: 'Johnson & Johnson' },
  { ticker: 'JPM',   name: 'JPMorgan Chase' },
  { ticker: 'MSFT',  name: 'Microsoft Corp.' },
  { ticker: 'PG',    name: 'Procter & Gamble' },
  { ticker: 'TSLA',  name: 'Tesla Inc.' },
  { ticker: 'VNQ',   name: 'Vanguard Real Estate' },
  { ticker: 'WMT',   name: 'Walmart Inc.' },
];

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

const COL_SIZE = 7;
const col1 = FULL_UNIVERSE.slice(0, COL_SIZE);
const col2 = FULL_UNIVERSE.slice(COL_SIZE);

// Build recharts-compatible data points from raw PriceHistory for selected tickers
function buildChartData(
  history: PriceHistory,
  tickers: string[],
  normalize: boolean,
): { date: string; [ticker: string]: number | string }[] {
  if (!history.dates.length || !tickers.length) return [];

  const activeTickers = tickers.filter(t => t in history.prices);

  // Find the common start index (first index where ALL selected tickers have data)
  const startIdx = 0;

  // Gather base values for normalisation (first available price per ticker)
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

// Format X-axis tick: show year only, avoid repeats
function formatDateTick(value: string): string {
  return value ? value.slice(0, 4) : '';
}

export const AssetSelection: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeUniverse, setActiveUniverse] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [normalize, setNormalize] = useState(false);
  const [priceHistory, setPriceHistory] = useState<PriceHistory | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const fetchedRef = useRef(false);

  const loadUniverse = useCallback(async () => {
    const tickers = await universeService.getUniverse();
    setActiveUniverse(
      new Set(tickers.length > 0 ? tickers : FULL_UNIVERSE.map(a => a.ticker))
    );
  }, []);

  useEffect(() => { loadUniverse(); }, [loadUniverse]);

  // Fetch price history once when the panel is first expanded
  useEffect(() => {
    if (!isExpanded || fetchedRef.current) return;
    fetchedRef.current = true;
    setChartLoading(true);
    priceHistoryService.get()
      .then(data => setPriceHistory(data))
      .catch(() => setPriceHistory(null))
      .finally(() => setChartLoading(false));
  }, [isExpanded]);

  const handleToggle = async (ticker: string) => {
    const next = new Set(activeUniverse);
    if (next.has(ticker)) next.delete(ticker);
    else next.add(ticker);
    setActiveUniverse(next);
    setSaving(true);
    try {
      await universeService.setUniverse([...next]);
    } finally {
      setSaving(false);
    }
  };

  const selected = FULL_UNIVERSE.filter(a => activeUniverse.has(a.ticker));
  const selectedTickers = selected.map(a => a.ticker);

  const chartData = priceHistory
    ? buildChartData(priceHistory, selectedTickers, normalize)
    : [];

  const renderSummary = () => {
    if (selected.length === 0) {
      return <span className="asset-badge">No assets selected</span>;
    }
    return (
      <>
        {selected.map(a => (
          <span key={a.ticker} className="asset-badge">{a.ticker}</span>
        ))}
        <span className="asset-count">({selected.length})</span>
      </>
    );
  };

  const renderColumn = (items: typeof FULL_UNIVERSE) => (
    <div className="universe-column">
      {items.map(asset => (
        <label key={asset.ticker} className="universe-row">
          <input
            type="checkbox"
            className="universe-checkbox"
            checked={activeUniverse.has(asset.ticker)}
            onChange={() => handleToggle(asset.ticker)}
          />
          <span
            className="universe-ticker-dot"
            style={{ background: TICKER_COLORS[asset.ticker] ?? '#94a3b8' }}
          />
          <span className="universe-ticker">{asset.ticker}</span>
          <span className="universe-name">{asset.name}</span>
        </label>
      ))}
    </div>
  );

  return (
    <div className="asset-selection-card">
      <div
        className="asset-card-header collapsible-header"
        onClick={() => setIsExpanded(p => !p)}
      >
        <h3 className="asset-card-title">
          Asset Universe
          {saving && <span className="universe-saving">saving…</span>}
          <span className={`chevron ${isExpanded ? 'expanded' : ''}`}>▼</span>
        </h3>
      </div>

      {!isExpanded ? (
        <div className="universe-collapsed">
          <div className="universe-summary">{renderSummary()}</div>
          <button
            className="change-btn"
            onClick={e => { e.stopPropagation(); setIsExpanded(true); }}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="universe-expanded-body">
          {/* Left: asset checkboxes */}
          <div className="universe-checkboxes">
            <div className="universe-grid">
              {renderColumn(col1)}
              {renderColumn(col2)}
            </div>
          </div>

          {/* Right: price history chart */}
          <div className="universe-chart-panel">
            <div className="universe-chart-header">
              <span className="universe-chart-title">Price History</span>
              <label className="normalize-toggle">
                <input
                  type="checkbox"
                  checked={normalize}
                  onChange={e => setNormalize(e.target.checked)}
                />
                <span>Normalise to 100</span>
              </label>
            </div>

            {chartLoading ? (
              <div className="universe-chart-loading">Loading price data…</div>
            ) : !priceHistory ? (
              <div className="universe-chart-loading">Price data unavailable</div>
            ) : selectedTickers.length === 0 ? (
              <div className="universe-chart-loading">Select assets to see history</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
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
                    tickFormatter={(v: number) => normalize ? `${v}` : v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`}
                  />
                  <Tooltip
                    contentStyle={{ background: '#1e2530', border: '1px solid #334155', borderRadius: 6, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                    itemStyle={{ color: '#e0e6ed' }}
                    formatter={(value: number, name: string) => [
                      normalize ? value.toFixed(2) : `$${value.toFixed(2)}`,
                      name,
                    ]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 4 }}
                  />
                  {selectedTickers
                    .filter(t => t in (priceHistory?.prices ?? {}))
                    .map(ticker => (
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
        </div>
      )}
    </div>
  );
};

