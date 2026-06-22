const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface WorkflowList {
  items: import("@/types").Workflow[];
  total: number;
}

export interface ExecutionList {
  items: import("@/types").Execution[];
  total: number;
}

export const api = {
  listWorkflows: () => fetchJson<WorkflowList>("/api/v1/flows/workflows"),
  getWorkflow: (id: string) =>
    fetchJson<import("@/types").Workflow>(`/api/v1/flows/workflows/${id}`),
  createWorkflow: (body: unknown) =>
    fetchJson<import("@/types").Workflow>("/api/v1/flows/workflows", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateWorkflow: (id: string, body: unknown) =>
    fetchJson<import("@/types").Workflow>(`/api/v1/flows/workflows/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteWorkflow: (id: string) =>
    fetch(`/api/v1/flows/workflows/${id}`, { method: "DELETE" }),
  validateWorkflow: (id: string) =>
    fetchJson<{ valid: boolean; errors: string[] }>(
      `/api/v1/flows/workflows/${id}/validate`,
      { method: "POST" },
    ),
  executeWorkflow: (id: string, payload?: unknown) =>
    fetchJson<import("@/types").Execution>(
      `/api/v1/flows/workflows/${id}/execute`,
      {
        method: "POST",
        body: JSON.stringify({ payload, wait_for_completion: false }),
      },
    ),
  listExecutions: (workflowId?: string) =>
    fetchJson<ExecutionList>(
      `/api/v1/flows/executions?${workflowId ? `workflow_id=${workflowId}&` : ""}`,
    ),
  getExecution: (id: string) =>
    fetchJson<import("@/types").Execution>(`/api/v1/flows/executions/${id}`),
  cancelExecution: (id: string) =>
    fetchJson<import("@/types").Execution>(
      `/api/v1/flows/executions/${id}/cancel`,
      { method: "POST" },
    ),
  generateWorkflow: (description: string, persist = true) =>
    fetchJson<import("@/types").CopilotGenerateResponse>(
      "/api/v1/flows/copilot/generate",
      {
        method: "POST",
        body: JSON.stringify({ description, persist }),
      },
    ),
  suggestNodes: (workflowId: string) =>
    fetchJson<{ suggestions: import("@/types").NodeSuggestion[] }>(
      `/api/v1/flows/copilot/suggest/${workflowId}`,
      { method: "POST" },
    ),
  chatCopilot: (
    message: string,
    history: import("@/types").CopilotChatMessage[] = [],
  ) =>
    fetchJson<import("@/types").CopilotChatResponse>(
      "/api/v1/flows/copilot/chat",
      {
        method: "POST",
        body: JSON.stringify({ message, history }),
      },
    ),
};
