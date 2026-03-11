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

function toolLabel(step: AgentStep): string {
  const tool = step.tool ?? step.type ?? '?';
  const label = (step.args as any)?.label;
  const sweep = (step.args as any)?.sweep_parameter;
  if (label) return `${tool}  — ${label}`;
  if (sweep) return `${tool}  — ${sweep}`;
  return tool;
}

interface Props {
  steps: AgentStep[];
}

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
        const tool = s.tool ?? s.type ?? '?';
        const icon = TOOL_ICONS[tool] ?? '○';
        const isTerminal = tool === 'synthesise' || tool === 'text_termination';
        const isOpen = expanded.has(i);

        return (
          <div key={i} className={`step-row ${isTerminal ? 'step-row--terminal' : ''}`}>
            <button className="step-row__header" onClick={() => toggle(i)}>
              <span className="step-icon">{icon}</span>
              <span className="step-num">step {s.step}</span>
              <span className="step-label">{toolLabel(s)}</span>
              <span className="step-chevron">{isOpen ? '▲' : '▼'}</span>
            </button>
            {isOpen && (
              <pre className="step-result">
                {JSON.stringify(s.result ?? s.content, null, 2)}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StepTimeline;
