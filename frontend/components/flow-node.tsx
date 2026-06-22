"use client";

import { createContext, useContext } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Clock,
  GitBranch,
  Globe,
  Merge,
  Repeat,
  Shuffle,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { FlowNode } from "@/types";

/**
 * Lets the canvas mark nodes as invalid (hard error) or unreachable (cleanup
 * hint) without mutating node data — the custom node reads it from context.
 */
export const NodeHighlightContext = createContext<{
  invalid: Set<string>;
  unreachable: Set<string>;
}>({ invalid: new Set(), unreachable: new Set() });

const TYPE_META: Record<FlowNode["type"], { icon: LucideIcon; color: string }> = {
  trigger: { icon: Zap, color: "border-flow-500 bg-flow-50 text-flow-800" },
  action: { icon: Globe, color: "border-blue-500 bg-blue-50 text-blue-800" },
  conditional: { icon: GitBranch, color: "border-orange-500 bg-orange-50 text-orange-800" },
  loop: { icon: Repeat, color: "border-purple-500 bg-purple-50 text-purple-800" },
  delay: { icon: Clock, color: "border-yellow-500 bg-yellow-50 text-yellow-800" },
  merge: { icon: Merge, color: "border-teal-500 bg-teal-50 text-teal-800" },
  transform: { icon: Shuffle, color: "border-pink-500 bg-pink-50 text-pink-800" },
};

export function FlowNodeCard({ id, data }: NodeProps) {
  const node = (data as { node: FlowNode }).node;
  const { invalid, unreachable } = useContext(NodeHighlightContext);
  const meta = TYPE_META[node.type] ?? TYPE_META.action;
  const Icon = meta.icon;
  const isInvalid = invalid.has(id);
  const isUnreachable = !isInvalid && unreachable.has(id);

  return (
    <div
      className={cn(
        "min-w-[150px] rounded-lg border-2 px-3 py-2 shadow-sm",
        meta.color,
        isInvalid && "border-red-500 ring-2 ring-red-300",
        isUnreachable && "border-amber-400 ring-2 ring-amber-200",
      )}
    >
      {node.type !== "trigger" && (
        <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      )}
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" />
        <span className="truncate text-sm font-medium">
          {node.label || node.type}
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-wide opacity-60">
        {node.type}
      </span>
      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
    </div>
  );
}
