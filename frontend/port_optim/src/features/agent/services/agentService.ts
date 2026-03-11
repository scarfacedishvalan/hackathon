import { apiClient } from '../../../services/apiClient';
import type { AgentAudit, AgentRunResponse, AuditSummary } from '../types/agentTypes';

export const agentService = {
  listRecipes: (): Promise<string[]> =>
    apiClient.get<string[]>('/agent/recipes'),

  listAudits: (limit = 50): Promise<AuditSummary[]> =>
    apiClient.get<AuditSummary[]>(`/agent/audits?limit=${limit}`),

  getAudit: (auditId: string): Promise<AgentAudit> =>
    apiClient.get<AgentAudit>(`/agent/audits/${auditId}`),

  startRun: (thesisName: string, goal: string, maxSteps = 8): Promise<AgentRunResponse> =>
    apiClient.post<AgentRunResponse>('/agent/run', {
      thesis_name: thesisName,
      goal,
      max_steps: maxSteps,
    }),

  /** Poll until the audit file is ready (status === 'done') or error. */
  pollUntilDone: async (
    auditId: string,
    onStep: (status: string) => void,
    intervalMs = 3000,
    timeoutMs = 300_000,
  ): Promise<AgentAudit> => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const data = await agentService.getAudit(auditId);
      if (data.status === 'done') return data;
      if (data.status === 'error') throw new Error((data as any).detail ?? 'Agent run failed');
      onStep(data.status);
      await new Promise(r => setTimeout(r, intervalMs));
    }
    throw new Error('Agent run timed out after 5 minutes');
  },
};
