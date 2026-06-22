import type { FlowEdge, FlowNode } from "@/types";

export interface GraphValidation {
  valid: boolean;
  errors: string[];
  invalidNodeIds: Set<string>;
}

/**
 * Cheap, client-side structural checks that mirror the backend engine's
 * non-topological rules (exactly one trigger; edges reference known nodes).
 * Cycle detection is intentionally left to the server `/validate` call on save.
 */
export function validateGraph(
  nodes: FlowNode[],
  edges: FlowEdge[],
): GraphValidation {
  const errors: string[] = [];
  const invalidNodeIds = new Set<string>();
  const nodeIds = new Set(nodes.map((n) => n.id));

  for (const e of edges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) {
      errors.push(`Edge references an unknown node: ${e.source} → ${e.target}`);
    }
  }

  const triggers = nodes.filter((n) => n.type === "trigger");
  if (triggers.length === 0) {
    errors.push("Workflow must have a trigger node");
  } else if (triggers.length > 1) {
    errors.push("Workflow must have only one trigger node");
    triggers.forEach((t) => invalidNodeIds.add(t.id));
  }

  return { valid: errors.length === 0, errors, invalidNodeIds };
}

/**
 * Node IDs not reachable from the single trigger via directed edges.
 * Mirrors backend engine.find_unreachable_nodes — used for non-destructive
 * cleanup hints. Returns [] when there is not exactly one trigger.
 */
export function findUnreachableNodes(
  nodes: FlowNode[],
  edges: FlowEdge[],
): string[] {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const triggers = nodes.filter((n) => n.type === "trigger");
  if (triggers.length !== 1) return [];

  const graph = new Map<string, string[]>();
  for (const e of edges) {
    if (nodeIds.has(e.source) && nodeIds.has(e.target)) {
      const list = graph.get(e.source) ?? [];
      list.push(e.target);
      graph.set(e.source, list);
    }
  }

  const seen = new Set<string>();
  const queue = [triggers[0].id];
  while (queue.length) {
    const current = queue.pop() as string;
    if (seen.has(current)) continue;
    seen.add(current);
    queue.push(...(graph.get(current) ?? []));
  }

  return Array.from(nodeIds).filter((id) => !seen.has(id));
}
