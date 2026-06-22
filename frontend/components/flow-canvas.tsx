"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { LayoutGrid, X } from "lucide-react";
import { api } from "@/lib/api";
import { findUnreachableNodes, validateGraph } from "@/lib/validation";
import { layoutNodes } from "@/lib/layout";
import { NodePalette } from "./node-palette";
import { PropertyPanel } from "./property-panel";
import { FlowNodeCard, NodeHighlightContext } from "./flow-node";
import type { FlowEdge, FlowNode, TriggerConfig, Workflow } from "@/types";

interface FlowCanvasProps {
  workflow: Workflow;
  onChange: (wf: Workflow) => void;
}

const nodeTypes = { flow: FlowNodeCard };

const DEFAULT_LABELS: Record<FlowNode["type"], string> = {
  trigger: "Trigger",
  action: "Action",
  conditional: "Conditional",
  loop: "Loop",
  delay: "Delay",
  merge: "Merge",
  transform: "Transform",
};

// --- mapping between the canonical FlowNode/FlowEdge model and React Flow ---

function toRfNodes(nodes: FlowNode[]): Node[] {
  return nodes.map((n) => ({
    id: n.id,
    type: "flow",
    position: n.position,
    data: { node: n },
  }));
}

function toRfEdges(edges: FlowEdge[]): Edge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
  }));
}

function fromRfNodes(rf: Node[]): FlowNode[] {
  return rf.map((n) => ({
    ...(n.data as { node: FlowNode }).node,
    id: n.id,
    position: { x: n.position.x, y: n.position.y },
  }));
}

function fromRfEdges(rf: Edge[]): FlowEdge[] {
  return rf.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: typeof e.label === "string" ? e.label : undefined,
  }));
}

export function FlowCanvas({ workflow, onChange }: FlowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<FlowNode | null>(null);
  const [savedJson, setSavedJson] = useState("");
  const [toast, setToast] = useState<{ msg: string; kind: string } | null>(null);
  const [diag, setDiag] = useState<{
    errors: string[];
    invalid: Set<string>;
    unreachable: string[];
  }>({ errors: [], invalid: new Set(), unreachable: [] });

  const rfRef = useRef<ReactFlowInstance<Node, Edge> | null>(null);
  const loadedId = useRef<string | null>(null);
  const metaRef = useRef(workflow);
  metaRef.current = workflow;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load graph into React Flow once per workflow id (the editing session owns
  // node positions thereafter; we don't re-sync from the prop on every change).
  useEffect(() => {
    if (loadedId.current === workflow.id) return;
    loadedId.current = workflow.id;
    setNodes(toRfNodes(workflow.nodes));
    setEdges(toRfEdges(workflow.edges));
    setSavedJson(
      JSON.stringify({
        nodes: workflow.nodes,
        edges: workflow.edges,
        trigger: workflow.trigger,
      }),
    );
  }, [workflow.id, workflow.nodes, workflow.edges, workflow.trigger, setNodes, setEdges]);

  // Bubble the canonical graph up to the parent whenever the canvas changes.
  useEffect(() => {
    onChangeRef.current({
      ...metaRef.current,
      nodes: fromRfNodes(nodes),
      edges: fromRfEdges(edges),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  // Debounced real-time diagnostics (structure only; cheap O(N)).
  useEffect(() => {
    const t = setTimeout(() => {
      const g = { nodes: fromRfNodes(nodes), edges: fromRfEdges(edges) };
      const v = validateGraph(g.nodes, g.edges);
      setDiag({
        errors: v.errors,
        invalid: v.invalidNodeIds,
        unreachable: findUnreachableNodes(g.nodes, g.edges),
      });
    }, 400);
    return () => clearTimeout(t);
  }, [nodes, edges]);

  const highlight = useMemo(
    () => ({ invalid: diag.invalid, unreachable: new Set(diag.unreachable) }),
    [diag],
  );

  const currentJson = JSON.stringify({
    nodes: fromRfNodes(nodes),
    edges: fromRfEdges(edges),
    trigger: workflow.trigger,
  });
  const dirty = savedJson !== "" && currentJson !== savedJson;

  const handleTriggerChange = (trigger: TriggerConfig) => {
    onChange({
      ...metaRef.current,
      trigger,
      nodes: fromRfNodes(nodes),
      edges: fromRfEdges(edges),
    });
  };

  const showToast = (msg: string, kind = "success") => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ msg, kind });
    toastTimer.current = setTimeout(() => setToast(null), 2500);
  };

  const onConnect = useCallback(
    (connection: Connection) => {
      const id = `e-${connection.source}-${connection.target}-${Date.now()}`;
      setEdges((eds) => addEdge({ ...connection, id }, eds));
    },
    [setEdges],
  );

  const onNodeClick = useCallback((_e: React.MouseEvent, node: Node) => {
    setSelectedNode((node.data as { node: FlowNode }).node);
  }, []);

  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const handleAddNode = (type: FlowNode["type"]) => {
    const id = `${type}-${Date.now()}`;
    const newNode: FlowNode = {
      id,
      type,
      position: { x: 120 + Math.random() * 80, y: 120 + Math.random() * 80 },
      config: type === "trigger" ? { trigger_type: "manual" } : {},
      label: DEFAULT_LABELS[type],
      timeout_seconds: 30,
    };
    setNodes((nds) => [...nds, ...toRfNodes([newNode])]);
  };

  const handleUpdateNode = (updated: FlowNode) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === updated.id ? { ...n, data: { node: updated } } : n)),
    );
    setSelectedNode(updated);
  };

  const handleDeleteNode = (id: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelectedNode((sn) => (sn?.id === id ? null : sn));
  };

  const handleAutoLayout = () => {
    const laid = layoutNodes(fromRfNodes(nodes), fromRfEdges(edges));
    setNodes(toRfNodes(laid));
    setTimeout(() => rfRef.current?.fitView({ padding: 0.2 }), 50);
  };

  const handleSave = async () => {
    const graph = {
      nodes: fromRfNodes(nodes),
      edges: fromRfEdges(edges),
      trigger: workflow.trigger,
    };
    try {
      await api.updateWorkflow(workflow.id, graph);
      setSavedJson(JSON.stringify(graph));
      const v = await api.validateWorkflow(workflow.id);
      showToast(
        v.valid ? "Workflow saved" : `Saved — ${v.errors.length} validation issue(s)`,
        v.valid ? "success" : "warn",
      );
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Save failed", "error");
    }
  };

  const unreachableNodes = fromRfNodes(nodes).filter((n) =>
    diag.unreachable.includes(n.id),
  );
  const toastColor =
    toast?.kind === "error"
      ? "bg-red-600"
      : toast?.kind === "warn"
        ? "bg-amber-500"
        : "bg-flow-600";

  return (
    <div className="flex h-full">
      <NodePalette onAddNode={handleAddNode} />
      <div className="relative flex-1">
        <div className="absolute left-3 top-3 z-10">
          {diag.errors.length === 0 ? (
            <span className="rounded-full bg-flow-100 px-3 py-1 text-xs font-medium text-flow-700">
              ✓ Valid
            </span>
          ) : (
            <span
              title={diag.errors.join("\n")}
              className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700"
            >
              {diag.errors.length} issue{diag.errors.length > 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="absolute right-3 top-3 z-10">
          <button
            type="button"
            onClick={handleAutoLayout}
            className="flex items-center gap-1.5 rounded-lg border bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Auto-layout
          </button>
        </div>

        {unreachableNodes.length > 0 && (
          <div className="absolute bottom-3 left-3 z-10 w-64 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs shadow-sm">
            <p className="mb-2 font-medium text-amber-800">
              {unreachableNodes.length} unreachable node
              {unreachableNodes.length > 1 ? "s" : ""} (not connected to the
              trigger)
            </p>
            <ul className="space-y-1">
              {unreachableNodes.map((n) => (
                <li key={n.id} className="flex items-center justify-between">
                  <span className="truncate text-amber-900">
                    {n.label || n.type}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteNode(n.id)}
                    aria-label={`Delete ${n.label || n.type}`}
                    className="ml-2 rounded p-0.5 text-amber-700 hover:bg-amber-100"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <NodeHighlightContext.Provider value={highlight}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={(inst) => (rfRef.current = inst)}
            deleteKeyCode={["Backspace", "Delete"]}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </NodeHighlightContext.Provider>

        {toast && (
          <div
            className={`absolute bottom-3 right-3 z-20 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-lg ${toastColor}`}
          >
            {toast.msg}
          </div>
        )}
      </div>

      <PropertyPanel
        node={selectedNode}
        onUpdate={handleUpdateNode}
        onDelete={handleDeleteNode}
        onSave={handleSave}
        dirty={dirty}
        errorCount={diag.errors.length}
        trigger={workflow.trigger}
        onTriggerChange={handleTriggerChange}
      />
    </div>
  );
}
