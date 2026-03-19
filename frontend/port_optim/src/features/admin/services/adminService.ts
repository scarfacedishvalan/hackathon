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
  ): Promise<AdminConsoleData> => {
    // Add timestamp cache buster AND noCache option for admin console
    const cacheBuster = Date.now();
    return apiClient.get<AdminConsoleData>(
      `/admin/console?llm_recent_limit=${llmRecentLimit}&agent_recent_limit=${agentRecentLimit}&_t=${cacheBuster}`,
      { noCache: true }
    );
  },

  getLlmUsage: (recentLimit = 50): Promise<LLMUsageData> => {
    const cacheBuster = Date.now();
    return apiClient.get<LLMUsageData>(
      `/admin/llm-usage?recent_limit=${recentLimit}&_t=${cacheBuster}`,
      { noCache: true }
    );
  },

  getAgentUsage: (recentLimit = 100): Promise<AgentUsageData> => {
    const cacheBuster = Date.now();
    return apiClient.get<AgentUsageData>(
      `/admin/agent-usage?recent_limit=${recentLimit}&_t=${cacheBuster}`,
      { noCache: true }
    );
  },

  /** Set a new tare point. Subsequent dashboard reads only count costs from now. */
  tare: (note = ""): Promise<TareResult> =>
    apiClient.post<TareResult>('/admin/tare', { note }),

  /** Remove the active tare and show all historical data again. */
  resetTare: (): Promise<TareResetResult> =>
    apiClient.post<TareResetResult>('/admin/tare/reset', {}),
};

