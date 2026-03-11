// Admin Console Types

export interface LLMCallSummary {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
}

export interface LLMByService {
  service: string;
  operation: string;
  calls: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
}

export interface LLMByModel {
  model: string;
  calls: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface LLMRecentCall {
  call_id: string;
  timestamp: string;
  service: string;
  operation: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  success: boolean;
  error_message: string | null;
}

export interface LLMUsageData {
  summary: LLMCallSummary;
  by_service: LLMByService[];
  by_model: LLMByModel[];
  recent_calls: LLMRecentCall[];
}

//  Agent 

export interface AgentRunSummary {
  total_runs: number;
  total_steps: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_cost_per_run: number;
  avg_steps_per_run: number;
}

export interface AgentByRun {
  audit_id: string;
  thesis_name: string;
  goal: string;
  run_timestamp: string;
  steps: number;
  total_tokens: number;
  cost_usd: number;
  model: string;
}

export interface AgentByThesis {
  thesis_name: string;
  runs: number;
  steps: number;
  total_tokens: number;
  cost_usd: number;
}

export interface AgentByTool {
  tool_called: string;
  calls: number;
  total_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface AgentByModel {
  model: string;
  steps: number;
  total_tokens: number;
  cost_usd: number;
}

export interface AgentRecentStep {
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
  success: boolean;
}

export interface AgentUsageData {
  summary: AgentRunSummary;
  by_run: AgentByRun[];
  by_thesis: AgentByThesis[];
  by_tool: AgentByTool[];
  by_model: AgentByModel[];
  recent_steps: AgentRecentStep[];
}

//  Tare 

export interface TareLogEntry {
  id: number;
  tare_ts: string;
  note: string;
}

export interface TareInfo {
  active_tare_ts: string | null;
  tare_history: TareLogEntry[];
}

/** Returned by POST /admin/tare */
export interface TareResult {
  tare_ts: string;
  note: string;
  previous_tare_ts: string | null;
}

/** Returned by POST /admin/tare/reset */
export interface TareResetResult {
  removed_tare_ts: string | null;
}

//  Combined 

export interface AdminConsoleData {
  grand_total_cost_usd: number;
  tare_info: TareInfo;
  llm_usage: LLMUsageData;
  agent_usage: AgentUsageData;
}
