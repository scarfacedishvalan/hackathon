import React, { useEffect, useState, useCallback } from 'react';
import { adminService } from '../services/adminService';
import type { AdminConsoleData } from '../types/adminTypes';
import './AdminPage.css';

//  helpers 

const fmt$ = (v: number) => `$${v.toFixed(6)}`;
const fmtK = (v: number) =>
  v >= 1_000_000 ? `${(v / 1_000_000).toFixed(2)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(1)}K` : String(v);
const fmtPct = (v: number) => `${(v * 100).toFixed(1)}%`;
const fmtMs  = (v: number) => `${Math.round(v)} ms`;
const fmtTs  = (ts: string) => ts ? ts.replace('T', ' ').slice(0, 19) + ' UTC' : '—';
const shortId = (id: string) => id.slice(0, 8) + '';

interface StatCardProps { label: string; value: string; sub?: string; accent?: boolean }
const StatCard: React.FC<StatCardProps> = ({ label, value, sub, accent }) => (
  <div className={`admin-stat-card${accent ? ' admin-stat-card--accent' : ''}`}>
    <span className="admin-stat-label">{label}</span>
    <span className="admin-stat-value">{value}</span>
    {sub && <span className="admin-stat-sub">{sub}</span>}
  </div>
);

//  Main Component 

export const AdminPage: React.FC = () => {
  const [data, setData]             = useState<AdminConsoleData | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [section, setSection]       = useState<'llm' | 'agent'>('llm');

  // tare state
  const [tarePending, setTarePending] = useState(false);
  const [taring, setTaring]           = useState(false);
  const [tareError, setTareError]     = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const d = await adminService.getConsole();
      setData(d);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleTareClick = () => {
    setTarePending(true);
    setTareError('');
  };

  const handleTareConfirm = async () => {
    setTaring(true);
    setTareError('');
    try {
      await adminService.tare('Manual tare from Admin Console');
      setTarePending(false);
      await load();
    } catch (e: any) {
      setTareError(e?.message ?? 'Tare failed');
    } finally {
      setTaring(false);
    }
  };

  const handleTareCancel = () => {
    setTarePending(false);
    setTareError('');
  };

  const handleResetTare = async () => {
    setTaring(true);
    setTareError('');
    try {
      await adminService.resetTare();
      await load();
    } catch (e: any) {
      setTareError(e?.message ?? 'Reset tare failed');
    } finally {
      setTaring(false);
    }
  };

  const activeTareTs = data?.tare_info?.active_tare_ts ?? null;

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div>
          <h2 className="admin-title">Admin Console</h2>
          <p className="admin-subtitle">Token usage and API cost tracker</p>
        </div>
        <div className="admin-header-right">
          {data && (
            <div className="grand-total-badge">
              {activeTareTs ? 'Since tare: ' : 'Total spend: '}
              <strong>{fmt$(data.grand_total_cost_usd)}</strong>
            </div>
          )}

          {/* Tare since badge */}
          {activeTareTs && (
            <div className="tare-active-badge" title="Data shown from this point onwards">
              Tared: {fmtTs(activeTareTs)}
              <button
                className="tare-reset-link"
                onClick={handleResetTare}
                disabled={taring}
                title="Show all historical data"
              >
                ✕ remove
              </button>
            </div>
          )}

          {/* Tare button / confirm row */}
          {!tarePending ? (
            <button
              className="admin-tare-btn"
              onClick={handleTareClick}
              disabled={loading || taring}
              title="Reset cost counter (history preserved in database)"
            >
              Tare
            </button>
          ) : (
            <div className="tare-confirm-row">
              <span className="tare-confirm-label">Zero display costs? History kept.</span>
              <button
                className="admin-tare-btn admin-tare-btn--confirm"
                onClick={handleTareConfirm}
                disabled={taring}
              >
                {taring ? 'Applying…' : 'Confirm Tare'}
              </button>
              <button
                className="admin-btn-secondary"
                onClick={handleTareCancel}
                disabled={taring}
              >
                Cancel
              </button>
            </div>
          )}

          {tareError && <span className="tare-error">{tareError}</span>}

          <button className="admin-refresh-btn" onClick={load} disabled={loading}>
            {loading ? 'Refreshing' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <div className="admin-error">{error}</div>}

      {/* Section toggle */}
      <div className="admin-section-tabs">
        <button
          className={`admin-section-tab${section === 'llm' ? ' active' : ''}`}
          onClick={() => setSection('llm')}
        >
          LLM Calls
          {data && (
            <span className="badge">{fmtK(data.llm_usage.summary.total_calls)}</span>
          )}
        </button>
        <button
          className={`admin-section-tab${section === 'agent' ? ' active' : ''}`}
          onClick={() => setSection('agent')}
        >
          Agent Runs
          {data && (
            <span className="badge">{data.agent_usage.summary.total_runs}</span>
          )}
        </button>
      </div>

      {loading && !data && <div className="admin-loading">Loading…</div>}

      {data && section === 'llm' && (
        <div className="admin-content">
          {/* LLM Summary cards */}
          <div className="admin-cards">
            <StatCard label="Total Calls" value={String(data.llm_usage.summary.total_calls)}
              sub={`${data.llm_usage.summary.failed_calls} failed`} />
            <StatCard label="Total Tokens" value={fmtK(data.llm_usage.summary.total_tokens)}
              sub={`${fmtK(data.llm_usage.summary.total_prompt_tokens)} in / ${fmtK(data.llm_usage.summary.total_completion_tokens)} out`} />
            <StatCard label="Total Cost" value={fmt$(data.llm_usage.summary.total_cost_usd)} accent />
            <StatCard label="Avg Latency" value={fmtMs(data.llm_usage.summary.avg_latency_ms)} />
            <StatCard label="Success Rate"
              value={fmtPct(
                data.llm_usage.summary.total_calls > 0
                  ? data.llm_usage.summary.successful_calls / data.llm_usage.summary.total_calls
                  : 0,
              )} />
          </div>

          {/* By Service */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">By Service / Operation</h3>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Service</th><th>Operation</th><th>Calls</th>
                    <th>Prompt Tokens</th><th>Completion Tokens</th>
                    <th>Cost (USD)</th><th>Avg Latency</th><th>Success</th>
                  </tr>
                </thead>
                <tbody>
                  {data.llm_usage.by_service.map((row, i) => (
                    <tr key={i}>
                      <td><span className="pill pill--service">{row.service}</span></td>
                      <td>{row.operation}</td>
                      <td className="num">{row.calls}</td>
                      <td className="num">{fmtK(row.prompt_tokens)}</td>
                      <td className="num">{fmtK(row.completion_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="num">{fmtMs(row.avg_latency_ms)}</td>
                      <td className="num">
                        <span className={`pill ${row.success_rate >= 0.95 ? 'pill--ok' : 'pill--warn'}`}>
                          {fmtPct(row.success_rate)}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {data.llm_usage.by_service.length === 0 && (
                    <tr><td colSpan={8} className="empty">No data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* By Model */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">By Model</h3>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Model</th><th>Calls</th><th>Prompt Tokens</th>
                    <th>Completion Tokens</th><th>Cost (USD)</th><th>Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {data.llm_usage.by_model.map((row, i) => (
                    <tr key={i}>
                      <td><span className="pill pill--model">{row.model}</span></td>
                      <td className="num">{row.calls}</td>
                      <td className="num">{fmtK(row.prompt_tokens)}</td>
                      <td className="num">{fmtK(row.completion_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="num">{fmtMs(row.avg_latency_ms)}</td>
                    </tr>
                  ))}
                  {data.llm_usage.by_model.length === 0 && (
                    <tr><td colSpan={6} className="empty">No data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Calls */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">Recent Calls (last {data.llm_usage.recent_calls.length})</h3>
            <div className="admin-table-wrap">
              <table className="admin-table admin-table--compact">
                <thead>
                  <tr>
                    <th>Timestamp</th><th>Service</th><th>Operation</th><th>Model</th>
                    <th>Tokens</th><th>Cost</th><th>Latency</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.llm_usage.recent_calls.map((row) => (
                    <tr key={row.call_id} className={row.success ? '' : 'row--error'}>
                      <td className="mono">{fmtTs(row.timestamp)}</td>
                      <td><span className="pill pill--service">{row.service}</span></td>
                      <td>{row.operation}</td>
                      <td><span className="pill pill--model">{row.model}</span></td>
                      <td className="num">{fmtK(row.total_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="num">{fmtMs(row.latency_ms)}</td>
                      <td>{row.success
                        ? <span className="pill pill--ok">OK</span>
                        : <span className="pill pill--err" title={row.error_message ?? ''}>ERR</span>}
                      </td>
                    </tr>
                  ))}
                  {data.llm_usage.recent_calls.length === 0 && (
                    <tr><td colSpan={8} className="empty">No calls recorded yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {data && section === 'agent' && (
        <div className="admin-content">
          {/* Agent Summary cards */}
          <div className="admin-cards">
            <StatCard label="Total Runs"  value={String(data.agent_usage.summary.total_runs)} />
            <StatCard label="Total Steps" value={String(data.agent_usage.summary.total_steps)}
              sub={`avg ${data.agent_usage.summary.avg_steps_per_run.toFixed(1)} / run`} />
            <StatCard label="Total Tokens" value={fmtK(data.agent_usage.summary.total_tokens)} />
            <StatCard label="Total Cost"  value={fmt$(data.agent_usage.summary.total_cost_usd)} accent />
            <StatCard label="Avg Cost / Run" value={fmt$(data.agent_usage.summary.avg_cost_per_run)} />
          </div>

          {/* By Run */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">By Agent Run</h3>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Audit ID</th><th>Thesis</th><th>Goal</th><th>Model</th>
                    <th>Steps</th><th>Tokens</th><th>Cost (USD)</th><th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.agent_usage.by_run.map((row, i) => (
                    <tr key={i}>
                      <td className="mono">{shortId(row.audit_id)}</td>
                      <td><span className="pill pill--thesis">{row.thesis_name}</span></td>
                      <td className="goal-cell" title={row.goal}>{row.goal.slice(0, 60)}{row.goal.length > 60 ? '…' : ''}</td>
                      <td><span className="pill pill--model">{row.model}</span></td>
                      <td className="num">{row.steps}</td>
                      <td className="num">{fmtK(row.total_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="mono">{fmtTs(row.run_timestamp)}</td>
                    </tr>
                  ))}
                  {data.agent_usage.by_run.length === 0 && (
                    <tr><td colSpan={8} className="empty">No agent runs recorded yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* By Tool */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">By Tool Called</h3>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr><th>Tool</th><th>Calls</th><th>Tokens</th><th>Cost (USD)</th><th>Avg Latency</th></tr>
                </thead>
                <tbody>
                  {data.agent_usage.by_tool.map((row, i) => (
                    <tr key={i}>
                      <td><span className="pill pill--tool">{row.tool_called}</span></td>
                      <td className="num">{row.calls}</td>
                      <td className="num">{fmtK(row.total_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="num">{fmtMs(row.avg_latency_ms)}</td>
                    </tr>
                  ))}
                  {data.agent_usage.by_tool.length === 0 && (
                    <tr><td colSpan={5} className="empty">No data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* By Thesis */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">By Thesis / Recipe</h3>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr><th>Thesis</th><th>Runs</th><th>Steps</th><th>Tokens</th><th>Cost (USD)</th></tr>
                </thead>
                <tbody>
                  {data.agent_usage.by_thesis.map((row, i) => (
                    <tr key={i}>
                      <td><span className="pill pill--thesis">{row.thesis_name}</span></td>
                      <td className="num">{row.runs}</td>
                      <td className="num">{row.steps}</td>
                      <td className="num">{fmtK(row.total_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                    </tr>
                  ))}
                  {data.agent_usage.by_thesis.length === 0 && (
                    <tr><td colSpan={5} className="empty">No data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Steps */}
          <div className="admin-table-section">
            <h3 className="admin-table-title">Recent Steps (last {data.agent_usage.recent_steps.length})</h3>
            <div className="admin-table-wrap">
              <table className="admin-table admin-table--compact">
                <thead>
                  <tr>
                    <th>Audit</th><th>Thesis</th><th>Step</th><th>Tool</th><th>Model</th>
                    <th>Tokens</th><th>Cost</th><th>Latency</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.agent_usage.recent_steps.map((row, i) => (
                    <tr key={i} className={row.success ? '' : 'row--error'}>
                      <td className="mono">{shortId(row.audit_id)}</td>
                      <td><span className="pill pill--thesis">{row.thesis_name}</span></td>
                      <td className="num">{row.step}</td>
                      <td><span className="pill pill--tool">{row.tool_called ?? 'plan'}</span></td>
                      <td><span className="pill pill--model">{row.model}</span></td>
                      <td className="num">{fmtK(row.total_tokens)}</td>
                      <td className="num cost">{fmt$(row.cost_usd)}</td>
                      <td className="num">{fmtMs(row.latency_ms)}</td>
                      <td>{row.success
                        ? <span className="pill pill--ok">OK</span>
                        : <span className="pill pill--err">ERR</span>}
                      </td>
                    </tr>
                  ))}
                  {data.agent_usage.recent_steps.length === 0 && (
                    <tr><td colSpan={9} className="empty">No steps recorded yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
