"use client";

import { useCallback, useEffect, useState } from "react";
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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "@/lib/api";
import { NodePalette } from "./node-palette";
import { PropertyPanel } from "./property-panel";
import type { FlowEdge, FlowNode, Workflow } from "@/types";

interface FlowCanvasProps {
  workflow: Workflow;
  onChange: (wf: Workflow) => void;
}

const nodeTypes: Record<string, string> = {
  trigger: "Trigger",
  action: "Action",
  conditional: "Conditional",
  loop: "Loop",
  delay: "Delay",
  merge: "Merge",
  transform: "Transform",
};

function toReactFlowNodes(nodes: FlowNode[]): Node[] {
  return nodes.map((n) => ({
    id: n.id,
    type: "default",
    position: n.position,
    data: { label: n.label || nodeTypes[n.type] || n.type, node: n },
  }));
}

function toReactFlowEdges(edges: FlowEdge[]): Edge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
  }));
}

export function FlowCanvas({ workflow, onChange }: FlowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    toReactFlowNodes(workflow.nodes),
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    toReactFlowEdges(workflow.edges),
  );
  const [selectedNode, setSelectedNode] = useState<FlowNode | null>(null);

  useEffect(() => {
    setNodes(toReactFlowNodes(workflow.nodes));
    setEdges(toReactFlowEdges(workflow.edges));
  }, [workflow, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: FlowEdge = {
        id: `e-${connection.source}-${connection.target}`,
        source: connection.source || "",
        target: connection.target || "",
      };
      const updatedEdges = [...workflow.edges, newEdge];
      onChange({ ...workflow, edges: updatedEdges });
      setEdges((eds) => addEdge(connection, eds));
    },
    [workflow, onChange, setEdges],
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const found = workflow.nodes.find((n) => n.id === node.id);
      setSelectedNode(found || null);
    },
    [workflow.nodes],
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleAddNode = (type: FlowNode["type"]) => {
    const id = `${type}-${Date.now()}`;
    const newNode: FlowNode = {
      id,
      type,
      position: { x: 200 + Math.random() * 100, y: 200 + Math.random() * 100 },
      config: {},
      label: nodeTypes[type],
      timeout_seconds: 30,
    };
    const updated = { ...workflow, nodes: [...workflow.nodes, newNode] };
    onChange(updated);
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "default",
        position: newNode.position,
        data: { label: newNode.label, node: newNode },
      },
    ]);
  };

  const handleUpdateNode = (updatedNode: FlowNode) => {
    const updatedNodes = workflow.nodes.map((n) =>
      n.id === updatedNode.id ? updatedNode : n,
    );
    onChange({ ...workflow, nodes: updatedNodes });
    setNodes((nds) =>
      nds.map((n) =>
        n.id === updatedNode.id
          ? {
              ...n,
              data: { label: updatedNode.label || nodeTypes[updatedNode.type], node: updatedNode },
            }
          : n,
      ),
    );
  };

  const handleSave = async () => {
    await api.updateWorkflow(workflow.id, {
      nodes: workflow.nodes,
      edges: workflow.edges,
    });
    alert("Workflow saved");
  };

  return (
    <div className="flex h-full">
      <NodePalette onAddNode={handleAddNode} />
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
      <PropertyPanel
        node={selectedNode}
        onUpdate={handleUpdateNode}
        onSave={handleSave}
      />
    </div>
  );
}
