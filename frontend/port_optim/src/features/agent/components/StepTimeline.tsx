import React, { useState } from 'react';
import type { AgentStep } from '../types/agentTypes';
import './StepTimeline.css';

const TOOL_ICONS: Record<string, string> = {
  get_recipe_summary: '📋',
  run_bl_scenario:    '▶',
  run_stress_sweep:   '⟳',
  compare_scenarios:  '⇌',
  synthesise:         '★',
  text_termination:   '★',
};

const TOOL_LABELS: Record<string, string> = {
  get_recipe_summary: 'Parse thesis',
  run_bl_scenario:    'Run BL model',
  run_stress_sweep:   'Stress sweep',
  compare_scenarios:  'Compare scenarios',
  synthesise:         'Synthesise findings',
  text_termination:   'Finish analysis',
};

function toolLabel(step: AgentStep): string {
  const tool = step.tool ?? step.type ?? '??';
  const nice  = TOOL_LABELS[tool];
  const label = (step.args as any)?.label;
  const sweep = (step.args as any)?.sweep_parameter;
  if (nice)  return sweep ? `${nice} — ${sweep}` : nice;
  if (label) return `${tool} — ${label}`;
  return tool;
}

interface Props { steps: AgentStep[] }

const StepTimeline: React.FC<Props> = ({ steps }) => {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  return (
    <div className="step-timeline">
      {steps.map((s, i) => {
        const tool       = s.tool ?? s.type ?? '??';
        const icon       = TOOL_ICONS[tool] ?? '○';
        const isTerminal = tool === 'synthesise' || tool === 'text_termination';
        const isOpen     = expanded.has(i);
        const hasDetail  = !!(s.result || s.content);

        return (
          <div key={i} className={`tl-item${isTerminal ? ' tl-item--terminal' : ''}`}>
            {/* vertical connector to next step */}
            {i < steps.length - 1 && <div className="tl-connector" />}

            {/* node circle */}
            <div className={`tl-node${isTerminal ? ' tl-node--terminal' : ''}`}>
              {isTerminal ? '★' : s.step}
            </div>

            {/* card */}
            <div className="tl-content">
              <button
                className="tl-header"
                onClick={() => hasDetail && toggle(i)}
                disabled={!hasDetail}
                style={{ cursor: hasDetail ? 'pointer' : 'default' }}
              >
                <span className="tl-icon">{icon}</span>
                <span className="tl-label">{toolLabel(s)}</span>
                {hasDetail && (
                  <span className="tl-chevron">{isOpen ? '▲' : '▼'}</span>
                )}
              </button>
              {isOpen && hasDetail && (
                <pre className="tl-detail">
                  {JSON.stringify(s.result ?? s.content, null, 2)}
                </pre>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default StepTimeline;
