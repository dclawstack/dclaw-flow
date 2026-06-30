import { clearToken, getToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (res.status === 401) clearToken();
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
  signup: (email: string, password: string) =>
    fetchJson<import("@/types").TokenResponse>("/api/v1/flows/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    fetchJson<import("@/types").TokenResponse>("/api/v1/flows/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => fetchJson<import("@/types").AuthUser>("/api/v1/flows/auth/me"),
  connectorCatalog: () =>
    fetchJson<import("@/types").ConnectorCatalog>(
      "/api/v1/flows/connections/catalog",
    ),
  listConnections: () =>
    fetchJson<import("@/types").Connection[]>("/api/v1/flows/connections"),
  createConnection: (body: {
    name: string;
    connector_type: string;
    secret: Record<string, string>;
  }) =>
    fetchJson<import("@/types").Connection>("/api/v1/flows/connections", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteConnection: (id: string) =>
    fetch(`${API_BASE}/api/v1/flows/connections/${id}`, {
      method: "DELETE",
      headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
    }),
  listWorkflows: () => fetchJson<WorkflowList>("/api/v1/flows/workflows"),
  listTemplates: () =>
    fetchJson<import("@/types").WorkflowTemplate[]>(
      "/api/v1/flows/workflows/templates",
    ),
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
  listExecutions: (params?: {
    workflowId?: string;
    status?: string;
    nodeId?: string;
    startedAfter?: string;
    startedBefore?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.workflowId) q.set("workflow_id", params.workflowId);
    if (params?.status) q.set("status", params.status);
    if (params?.nodeId) q.set("node_id", params.nodeId);
    if (params?.startedAfter) q.set("started_after", params.startedAfter);
    if (params?.startedBefore) q.set("started_before", params.startedBefore);
    return fetchJson<ExecutionList>(`/api/v1/flows/executions?${q.toString()}`);
  },
  getExecutionAnomalies: (id: string) =>
    fetchJson<{ flags: string[] }>(
      `/api/v1/flows/executions/${id}/anomalies`,
    ),
  getExecutionRootCause: (id: string) =>
    fetchJson<{ explanation: string; source: string }>(
      `/api/v1/flows/executions/${id}/root-cause`,
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
  getWebhookSchema: (path: string) =>
    fetchJson<{
      webhook_id: string;
      workflow_id: string;
      schema: Record<string, unknown> | null;
    }>(`/api/v1/flows/webhooks/${path}/schema`),
};

export const webhookUrl = (path: string) => {
  const base =
    process.env.NEXT_PUBLIC_API_URL ||
    (typeof window !== "undefined" ? window.location.origin : "");
  return `${base}/api/v1/flows/webhooks/${path}`;
};
