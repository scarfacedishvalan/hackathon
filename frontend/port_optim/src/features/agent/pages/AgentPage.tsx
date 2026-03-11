import React, { useEffect, useState, useCallback } from 'react';
import { agentService } from '../services/agentService';
import type { AgentAudit, AuditSummary } from '../types/agentTypes';
import AuditDisplay from '../components/AuditDisplay';
import './AgentPage.css';

const DEFAULT_GOAL =
  'Stress-test all views by varying confidence and find an allocation ' +
  'for a moderate-risk investor with max 25% per position.';

const GOAL_EXAMPLES = [
  'Stress-test all views by varying confidence and find an allocation for a moderate-risk investor with max 25% per position.',
  'Maximise Sharpe ratio with sector diversification. No single asset above 20%. Run stress sweep on expected return assumptions.',
  'Minimise portfolio volatility for a conservative investor. Penalise concentration in correlated assets. Max drawdown constraint of 10%.',
];

export const AgentPage: React.FC = () => {
  const [recipes, setRecipes]             = useState<string[]>([]);
  const [selectedThesis, setSelected]     = useState<string>('');
  const [goal, setGoal]                   = useState(DEFAULT_GOAL);
  const [running, setRunning]             = useState(false);
  const [runStatus, setRunStatus]         = useState('');
  const [audits, setAudits]               = useState<AuditSummary[]>([]);
  const [activeAudit, setActiveAudit]     = useState<AgentAudit | null>(null);
  const [error, setError]                 = useState('');
  const [pastRunsOpen, setPastRunsOpen]   = useState(false);

  // Load recipe names + past audits on mount
  useEffect(() => {
    agentService.listRecipes()
      .then(r => {
        setRecipes(r);
        if (r.length) setSelected(r[0]);
      })
      .catch(() => setRecipes([]));

    loadAudits();
  }, []);

  const loadAudits = useCallback(() => {
    agentService.listAudits()
      .then(setAudits)
      .catch(() => {});
  }, []);

  const handleRun = useCallback(async () => {
    if (!selectedThesis || running) return;
    setRunning(true);
    setError('');
    setActiveAudit(null);
    setRunStatus('Starting...');
    try {
      const { audit_id } = await agentService.startRun(selectedThesis, goal);
      setRunStatus('Running...');
      const audit = await agentService.pollUntilDone(
        audit_id,
        status => setRunStatus(`Running (${status})...`),
      );
      setActiveAudit(audit);
      loadAudits();
    } catch (e: any) {
      setError(e?.message ?? 'Unknown error');
    } finally {
      setRunning(false);
      setRunStatus('');
    }
  }, [selectedThesis, goal, running, loadAudits]);

  const handleLoadAudit = useCallback(async (auditId: string) => {
    try {
      const audit = await agentService.getAudit(auditId);
      setActiveAudit(audit);
    } catch {
      setError(`Could not load audit ${auditId}`);
    }
  }, []);

  return (
    <div className="agent-page">
      {/* Left panel */}
      <aside className="agent-sidebar">
        <div className="sidebar-section">
          <p className="sidebar-label">Saved thesis</p>
          <div className="thesis-list">
            {recipes.length === 0 && (
              <span className="sidebar-empty">No recipes found</span>
            )}
            {recipes.map(r => (
              <button
                key={r}
                className={`thesis-item ${selectedThesis === r ? 'thesis-item--active' : ''}`}
                onClick={() => setSelected(r)}
              >
                <span className="thesis-dot">{selectedThesis === r ? '●' : '○'}</span>
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-label">Goal</p>
          <textarea
            className="goal-input"
            value={goal}
            onChange={e => setGoal(e.target.value)}
            rows={4}
            disabled={running}
          />
          <div className="goal-examples">
            {GOAL_EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="goal-example-btn"
                onClick={() => setGoal(ex)}
                disabled={running}
                title="Paste into goal"
              >
                <span className="goal-example-icon">⎘</span>
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          className={`run-btn ${running ? 'run-btn--running' : ''}`}
          onClick={handleRun}
          disabled={running || !selectedThesis}
        >
          {running ? runStatus || 'Running...' : 'Run Agent'}
        </button>

        {error && <p className="run-error">{error}</p>}

        {audits.length > 0 && (
          <div className="sidebar-section sidebar-section--audits">
            <button className="past-runs-toggle" onClick={() => setPastRunsOpen(o => !o)}>
              <span className="sidebar-label" style={{ margin: 0 }}>Past runs</span>
              <span className="past-runs-count">{audits.length}</span>
              <span className="past-runs-chevron">{pastRunsOpen ? '▲' : '▼'}</span>
            </button>
            {pastRunsOpen && (
              <div className="audit-list">
                {audits.map(a => (
                  <button
                    key={a.audit_id}
                    className={`audit-list-item ${activeAudit?.audit_id === a.audit_id ? 'audit-list-item--active' : ''}`}
                    onClick={() => handleLoadAudit(a.audit_id)}
                  >
                    <span className="audit-list-thesis">{a.thesis_name}</span>
                    <span className="audit-list-meta">
                      {new Date(a.first_timestamp).toLocaleString()}
                    </span>
                    <span className="audit-list-id">{a.audit_id.slice(0, 8)}…</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </aside>

      {/* Right panel */}
      <main className="agent-main">
        {!activeAudit && !running && (
          <div className="agent-empty">
            <p>Select a thesis and press <strong>Run Agent</strong> to start the analysis,</p>
            <p>or click a past run to review it.</p>
          </div>
        )}
        {running && (
          <div className="agent-empty">
            <div className="agent-spinner" />
            <p className="agent-spinner-label">{runStatus}</p>
          </div>
        )}
        {activeAudit && !running && (
          <AuditDisplay audit={activeAudit} />
        )}
      </main>
    </div>
  );
};
