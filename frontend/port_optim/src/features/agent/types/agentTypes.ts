export interface AuditSummary {
  audit_id: string;
  thesis_name: string;
  first_timestamp: string;
  steps: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface StepCost {
  audit_id: string;
  timestamp: string;
  thesis_name: string;
  step: number;
  tool_called: string | null;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  success: number;
}

export interface AgentStep {
  step: number;
  tool?: string;
  type?: string;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  content?: string;
}

export interface Synthesis {
  done: boolean;
  narrative: string;
  recommended_weights?: Record<string, number> | null;
  risk_flags?: string[];
}

export interface CostBreakdown {
  steps: number;
  total_tokens: number;
  total_cost_usd: number;
  success_steps: number;
}

export interface AgentAudit {
  status: 'done' | 'running' | 'error';
  audit_id: string;
  thesis_name: string;
  goal: string;
  run_timestamp: string;
  model: string;
  base_result_summary: {
    portfolio_return: number;
    portfolio_vol: number;
    sharpe: number;
    weights: Record<string, number>;
  };
  steps: AgentStep[];
  synthesis: Synthesis;
  final_weights: Record<string, number> | null;
  weight_delta_vs_base: Record<string, number> | null;
  cost_breakdown: CostBreakdown;
  step_costs: StepCost[];
  // allow extra fields
  [key: string]: unknown;
}

export interface AgentRunResponse {
  audit_id: string;
  status: string;
}
