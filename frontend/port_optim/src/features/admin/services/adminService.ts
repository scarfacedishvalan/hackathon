import { apiClient } from '../../../services/apiClient';
import type {
  AdminConsoleData,
  LLMUsageData,
  AgentUsageData,
  TareResult,
  TareResetResult,
} from '../types/adminTypes';

export const adminService = {
  getConsole: (
    llmRecentLimit = 50,
    agentRecentLimit = 100,
  ): Promise<AdminConsoleData> =>
    apiClient.get<AdminConsoleData>(
      `/admin/console?llm_recent_limit=${llmRecentLimit}&agent_recent_limit=${agentRecentLimit}`,
    ),

  getLlmUsage: (recentLimit = 50): Promise<LLMUsageData> =>
    apiClient.get<LLMUsageData>(`/admin/llm-usage?recent_limit=${recentLimit}`),

  getAgentUsage: (recentLimit = 100): Promise<AgentUsageData> =>
    apiClient.get<AgentUsageData>(`/admin/agent-usage?recent_limit=${recentLimit}`),

  /** Set a new tare point. Subsequent dashboard reads only count costs from now. */
  tare: (note = ""): Promise<TareResult> =>
    apiClient.post<TareResult>('/admin/tare', { note }),

  /** Remove the active tare and show all historical data again. */
  resetTare: (): Promise<TareResetResult> =>
    apiClient.post<TareResetResult>('/admin/tare/reset', {}),
};

