export interface FlowNode {
  id: string;
  type: "trigger" | "action" | "conditional" | "loop" | "delay" | "merge" | "transform";
  position: { x: number; y: number };
  config: Record<string, unknown>;
  label?: string;
  timeout_seconds?: number;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface TriggerConfig {
  trigger_type: "manual" | "webhook" | "schedule";
  config: Record<string, unknown>;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  status: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  trigger: TriggerConfig;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface NodeExecution {
  id: string;
  execution_id: string;
  node_id: string;
  status: string;
  input?: Record<string, unknown> | null;
  output?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  created_at: string;
}

export interface Execution {
  id: string;
  workflow_id: string;
  status: string;
  trigger_source: string;
  trigger_payload?: Record<string, unknown> | null;
  started_at: string;
  completed_at?: string | null;
  error?: Record<string, unknown> | null;
  node_executions: NodeExecution[];
}

export interface CopilotGenerateResponse {
  source: "ollama" | "openrouter" | "heuristic";
  model?: string | null;
  valid: boolean;
  errors: string[];
  spec: Pick<Workflow, "name" | "description" | "nodes" | "edges" | "trigger">;
  workflow?: Workflow | null;
}

export interface NodeSuggestion {
  type: FlowNode["type"];
  label: string;
  reason: string;
}

export interface CopilotChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CopilotChatResponse {
  reply: string;
  intent: "build" | "chat";
  source: "ollama" | "openrouter" | "heuristic";
  model?: string | null;
  suggested_workflow?:
    | Pick<Workflow, "name" | "description" | "nodes" | "edges" | "trigger">
    | null;
}
