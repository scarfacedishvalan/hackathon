import { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { StockSelector } from './components/StockSelector';
import { MetricCard } from './components/MetricCard';

function App() {
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [strategyInstruction, setStrategyInstruction] = useState('');
  const [isRecipeExpanded, setIsRecipeExpanded] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [recipeJSON, setRecipeJSON] = useState<any>(null);
  const [equityCurveData, setEquityCurveData] = useState<any[]>([]);
  const [summaryStats, setSummaryStats] = useState<any>(null);
  const [plotUrl, setPlotUrl] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const BACKEND_BASE_URL = 'http://localhost:8000';

  const formatPercent = (value: any) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number' && Number.isFinite(value)) return `${value.toFixed(2)}%`;
    const s = String(value);
    return s.includes('%') ? s : s;
  };

  const formatNumber = (value: any) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number' && Number.isFinite(value)) return value.toFixed(2);
    return String(value);
  };

  const pickStat = (stats: any, keys: string[], formatter: (v: any) => string) => {
    if (!stats) return '—';
    for (const k of keys) {
      const v = stats[k];
      if (v !== null && v !== undefined) return formatter(v);
    }
    return '—';
  };

  const exampleInstructions = [
    "Run SmaCross on SPY from 2019-01-01 to 2023-12-31 with cash 25000",
    "Run EmaCross on AAPL daily with cash 25000 and commission 0.1%",
    "Run RsiReversion on MSFT daily with cash 25000"
  ];

  const handleCopyExample = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setStrategyInstruction(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleGenerateRecipe = async () => {
    if (selectedStocks.length === 0) {
      alert('Please select at least one stock');
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_BASE_URL}/api/generate-recipe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stocks: selectedStocks,
          strategy_instruction: strategyInstruction || ''
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate recipe');
      }

      const data = await response.json();
      
      // Update state with backend response
      setRecipeJSON(data.recipe);
      const curve = Array.isArray(data.equity_curve) ? data.equity_curve : [];
      const normalizedCurve = curve
        .map((row: any) => {
          const date = row.date ?? row.Date ?? row.datetime ?? row.Datetime ?? row.time ?? row.Time;
          const value = row.value ?? row.Equity ?? row.equity ?? row.Portfolio ?? row.portfolio;
          return { date, value };
        })
        .filter((pt: any) => pt.date != null && pt.value != null);

      setEquityCurveData(normalizedCurve);
      setSummaryStats(data.summary_stats);
      setPlotUrl(typeof data.plot_url === 'string' ? `${BACKEND_BASE_URL}${data.plot_url}` : null);
      setShowResults(true);
      
    } catch (error) {
      console.error('Error generating recipe:', error);
      alert('Failed to generate recipe. Make sure the backend is running on http://localhost:8000');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl text-slate-900 mb-2">Portfolio Backtesting</h1>
          <p className="text-slate-600">Configure your strategy, generate a recipe, and analyze backtest results</p>
        </div>

        {/* Top Input Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex flex-col gap-4">
            {/* Stock Selector */}
            <div>
              <label className="block text-sm text-slate-700 mb-2">
                Select Stocks
              </label>
              <StockSelector
                selectedStocks={selectedStocks}
                onChange={setSelectedStocks}
              />
            </div>

            {/* Strategy Instruction */}
            <div>
              <label className="block text-sm text-slate-700 mb-2">
                Strategy Instruction
              </label>
              <textarea
                value={strategyInstruction}
                onChange={(e) => setStrategyInstruction(e.target.value)}
                placeholder="Run the strategy WeighMeanVar with lookbacks 3y, 2y and 1y with yearly rebalance"
                className="w-full h-24 px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Submit Button */}
            <div>
              <button
                onClick={handleGenerateRecipe}
                disabled={isLoading}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors disabled:bg-blue-400 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Running...' : 'Run Backtest'}
              </button>
            </div>

            {/* Example Instructions */}
            <div className="mt-4">
              <p className="text-xs text-slate-600 mb-2 font-medium">Example Instructions:</p>
              <div className="space-y-2">
                {exampleInstructions.map((instruction, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 group"
                  >
                    <span className="text-slate-400 text-xs mt-0.5">•</span>
                    <span className="text-xs text-slate-600 flex-1">{instruction}</span>
                    <button
                      onClick={() => handleCopyExample(instruction, index)}
                      className="p-1 hover:bg-slate-100 rounded transition-colors"
                      title="Copy to clipboard"
                    >
                      {copiedIndex === index ? (
                        <Check className="w-3.5 h-3.5 text-green-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Collapsible Recipe JSON Section */}
        {showResults && (
          <div className="bg-white rounded-lg shadow-sm mb-6">
            <button
              onClick={() => setIsRecipeExpanded(!isRecipeExpanded)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
            >
              <h2 className="text-lg text-slate-900 font-medium">Backtesting recipe</h2>
              {isRecipeExpanded ? (
                <ChevronDown className="w-5 h-5 text-slate-600" />
              ) : (
                <ChevronRight className="w-5 h-5 text-slate-600" />
              )}
            </button>
            
            {isRecipeExpanded && (
              <div className="px-6 pb-6">
                <pre className="bg-slate-800 text-slate-200 p-6 rounded-md overflow-x-auto text-xl font-mono leading-relaxed">
                  {JSON.stringify(recipeJSON, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Main Visualization Section */}
        {showResults && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between gap-4 mb-6">
              <h2 className="text-lg text-slate-900 font-medium">Backtest Equity Curve</h2>
              {plotUrl && (
                <a
                  href={plotUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-700 hover:underline"
                >
                  Open HTML plot
                </a>
              )}
            </div>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equityCurveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#64748b"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis 
                    stroke="#64748b"
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                    formatter={(value: number) => [`$${value.toLocaleString()}`, 'Portfolio Value']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#2563eb" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Summary Statistics Section */}
        {showResults && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg text-slate-900 font-medium mb-4">Summary Statistics</h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="CAGR"
                value={pickStat(summaryStats, ['CAGR [%]', 'CAGR', 'cagr'], formatPercent)}
              />
              <MetricCard
                label="Sharpe Ratio"
                value={pickStat(summaryStats, ['Sharpe Ratio', 'sharpe_ratio', 'Sharpe'], formatNumber)}
              />
              <MetricCard
                label="Max Drawdown"
                value={pickStat(summaryStats, ['Max. Drawdown [%]', 'Max Drawdown', 'max_drawdown'], formatPercent)}
              />
              <MetricCard
                label="Volatility"
                value={pickStat(summaryStats, ['Volatility (Ann.) [%]', 'Volatility', 'volatility'], formatPercent)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
