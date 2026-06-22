import dagre from "dagre";
import type { FlowEdge, FlowNode } from "@/types";

const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;

/**
 * Deterministic left-to-right hierarchical layout via dagre. Returns the nodes
 * with recomputed positions; the graph structure is unchanged. (LLM-driven
 * layout is deferred to P1.)
 */
export function layoutNodes(nodes: FlowNode[], edges: FlowEdge[]): FlowNode[] {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 48, ranksep: 96 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => {
    if (e.source && e.target) g.setEdge(e.source, e.target);
  });

  dagre.layout(g);

  return nodes.map((n) => {
    const laid = g.node(n.id);
    if (!laid) return n;
    return {
      ...n,
      position: { x: laid.x - NODE_WIDTH / 2, y: laid.y - NODE_HEIGHT / 2 },
    };
  });
}
