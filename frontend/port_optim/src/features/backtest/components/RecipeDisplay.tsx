import React from 'react';
import type { BacktestRecipe } from '../types/backtestTypes';
import './RecipeDisplay.css';

interface Props { recipe: BacktestRecipe; }

const Val: React.FC<{ v: unknown; tag?: boolean; rule?: boolean }> = ({ v, tag, rule }) => {
  if (v === null || v === undefined || v === '')
    return <span className="recipe-value recipe-value--null">—</span>;
  if (tag)
    return <span className="recipe-value recipe-value--tag">{String(v)}</span>;
  if (rule)
    return <span className="recipe-value recipe-value--rule">{String(v)}</span>;
  return <span className="recipe-value">{String(v)}</span>;
};

const Row: React.FC<{ label: string; v: unknown; tag?: boolean; rule?: boolean }> = ({ label, v, tag, rule }) => (
  <div className="recipe-row">
    <span className="recipe-key">{label}</span>
    <Val v={v} tag={tag} rule={rule} />
  </div>
);

export const RecipeDisplay: React.FC<Props> = ({ recipe }) => {
  const { strategy_name, timeframe, data, backtest, strategy_params, rules, risk, optimize } = recipe;

  return (
    <div className="recipe-display">
      {/* Strategy */}
      <div className="recipe-section">
        <p className="recipe-section-title">Strategy</p>
        <div className="recipe-rows">
          <Row label="Name"      v={strategy_name} tag />
          <Row label="Timeframe" v={timeframe} />
          {strategy_params && Object.entries(strategy_params).map(([k, val]) => (
            <Row key={k} label={k} v={val} />
          ))}
        </div>
      </div>

      {/* Data */}
      <div className="recipe-section">
        <p className="recipe-section-title">Data</p>
        <div className="recipe-rows">
          <Row label="Symbol" v={data?.symbol} />
          <Row label="Source" v={data?.source} />
          <Row label="Start"  v={data?.start} />
          <Row label="End"    v={data?.end} />
          <Row label="Path"   v={data?.path} />
        </div>
      </div>

      {/* Backtest Config */}
      <div className="recipe-section">
        <p className="recipe-section-title">Backtest Config</p>
        <div className="recipe-rows">
          <Row label="Cash"             v={backtest?.cash != null ? `$${backtest.cash.toLocaleString()}` : null} />
          <Row label="Commission"       v={backtest?.commission} />
          <Row label="Margin"           v={backtest?.margin} />
          <Row label="Trade on Close"   v={backtest?.trade_on_close != null ? String(backtest.trade_on_close) : null} />
          <Row label="Hedging"          v={backtest?.hedging != null ? String(backtest.hedging) : null} />
          <Row label="Exclusive Orders" v={backtest?.exclusive_orders != null ? String(backtest.exclusive_orders) : null} />
        </div>
      </div>

      {/* Rules */}
      {(rules?.entry || rules?.exit) && (
        <div className="recipe-section">
          <p className="recipe-section-title">Rules</p>
          <div className="recipe-rows">
            <Row label="Entry" v={rules.entry} rule />
            <Row label="Exit"  v={rules.exit}  rule />
          </div>
        </div>
      )}

      {/* Risk */}
      {(risk?.stop_loss || risk?.take_profit || risk?.trailing_stop) && (
        <div className="recipe-section">
          <p className="recipe-section-title">Risk</p>
          <div className="recipe-rows">
            <Row label="Stop Loss"     v={risk.stop_loss} />
            <Row label="Take Profit"   v={risk.take_profit} />
            <Row label="Trailing Stop" v={risk.trailing_stop} />
          </div>
        </div>
      )}

      {/* Optimize */}
      {optimize?.params && (
        <div className="recipe-section">
          <p className="recipe-section-title">Optimization</p>
          <div className="recipe-rows">
            <Row label="Metric"     v={optimize.metric} />
            <Row label="Maximize"   v={optimize.maximize != null ? String(optimize.maximize) : null} />
            <Row label="Constraint" v={optimize.constraint} />
            {optimize.params && Object.entries(optimize.params).map(([k, vals]) => (
              <Row key={k} label={`${k} range`} v={`[${vals.join(', ')}]`} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
