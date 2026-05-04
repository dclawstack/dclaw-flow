"use client";

import type { FlowNode } from "@/types";

const paletteItems: { type: FlowNode["type"]; label: string }[] = [
  { type: "trigger", label: "Trigger" },
  { type: "action", label: "Action" },
  { type: "conditional", label: "Conditional" },
  { type: "loop", label: "Loop" },
  { type: "delay", label: "Delay" },
  { type: "merge", label: "Merge" },
  { type: "transform", label: "Transform" },
];

interface NodePaletteProps {
  onAddNode: (type: FlowNode["type"]) => void;
}

export function NodePalette({ onAddNode }: NodePaletteProps) {
  return (
    <div className="w-48 border-r bg-gray-50 p-3">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Nodes
      </h3>
      <div className="space-y-2">
        {paletteItems.map((item) => (
          <button
            key={item.type}
            onClick={() => onAddNode(item.type)}
            className="w-full rounded-lg border bg-white px-3 py-2 text-left text-sm font-medium text-gray-700 shadow-sm transition hover:bg-flow-50 hover:text-flow-700"
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
