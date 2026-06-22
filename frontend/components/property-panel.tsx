"use client";

import type { FlowNode } from "@/types";

interface PropertyPanelProps {
  node: FlowNode | null;
  onUpdate: (node: FlowNode) => void;
  onDelete: (id: string) => void;
  onSave: () => void;
  dirty: boolean;
  errorCount: number;
}

function SaveButton({
  onSave,
  dirty,
  errorCount,
}: Pick<PropertyPanelProps, "onSave" | "dirty" | "errorCount">) {
  return (
    <button
      onClick={onSave}
      disabled={!dirty}
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-flow-600 px-3 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
    >
      {dirty && <span className="h-2 w-2 rounded-full bg-white" aria-hidden />}
      {dirty ? "Save Workflow" : "Saved"}
      {errorCount > 0 && (
        <span className="rounded-full bg-red-500 px-1.5 text-[10px]">
          {errorCount}
        </span>
      )}
    </button>
  );
}

export function PropertyPanel({
  node,
  onUpdate,
  onDelete,
  onSave,
  dirty,
  errorCount,
}: PropertyPanelProps) {
  if (!node) {
    return (
      <div className="w-64 border-l bg-gray-50 p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Properties
        </h3>
        <p className="text-sm text-gray-400">Select a node to edit</p>
        <SaveButton onSave={onSave} dirty={dirty} errorCount={errorCount} />
      </div>
    );
  }

  const updateConfig = (key: string, value: unknown) => {
    onUpdate({
      ...node,
      config: { ...node.config, [key]: value },
    });
  };

  return (
    <div className="w-64 border-l bg-gray-50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Properties
      </h3>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Label
        </label>
        <input
          value={node.label || ""}
          onChange={(e) => onUpdate({ ...node, label: e.target.value })}
          className="w-full rounded border px-2 py-1 text-sm"
        />
      </div>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Type
        </label>
        <div className="rounded border bg-white px-2 py-1 text-sm text-gray-500">
          {node.type}
        </div>
      </div>

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Timeout (seconds)
        </label>
        <input
          type="number"
          value={node.timeout_seconds || 30}
          onChange={(e) =>
            onUpdate({ ...node, timeout_seconds: parseInt(e.target.value, 10) })
          }
          className="w-full rounded border px-2 py-1 text-sm"
        />
      </div>

      {node.type === "trigger" && (
        <div className="mb-3">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Trigger Type
          </label>
          <select
            value={(node.config.trigger_type as string) || "manual"}
            onChange={(e) => updateConfig("trigger_type", e.target.value)}
            className="w-full rounded border px-2 py-1 text-sm"
          >
            <option value="manual">Manual</option>
            <option value="webhook">Webhook</option>
            <option value="schedule">Schedule</option>
          </select>
        </div>
      )}

      {node.type === "action" && (
        <>
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-gray-600">
              URL
            </label>
            <input
              value={(node.config.url as string) || ""}
              onChange={(e) => updateConfig("url", e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
            />
          </div>
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Method
            </label>
            <select
              value={(node.config.method as string) || "GET"}
              onChange={(e) => updateConfig("method", e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
            </select>
          </div>
        </>
      )}

      {node.type === "delay" && (
        <div className="mb-3">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Duration (seconds)
          </label>
          <input
            type="number"
            value={(node.config.duration_seconds as number) || 1}
            onChange={(e) =>
              updateConfig("duration_seconds", parseInt(e.target.value, 10))
            }
            className="w-full rounded border px-2 py-1 text-sm"
          />
        </div>
      )}

      {node.type === "conditional" && (
        <div className="mb-3">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Expression
          </label>
          <input
            value={(node.config.expression as string) || "true"}
            onChange={(e) => updateConfig("expression", e.target.value)}
            className="w-full rounded border px-2 py-1 text-sm"
          />
        </div>
      )}

      {node.type === "transform" && (
        <div className="mb-3">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Mapping (JSON)
          </label>
          <textarea
            rows={4}
            value={JSON.stringify(node.config.mapping || {}, null, 2)}
            onChange={(e) => {
              try {
                updateConfig("mapping", JSON.parse(e.target.value));
              } catch {
                // ignore invalid JSON while typing
              }
            }}
            className="w-full rounded border px-2 py-1 text-sm font-mono"
          />
        </div>
      )}

      <button
        onClick={() => onDelete(node.id)}
        className="mt-4 w-full rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
      >
        Delete Node
      </button>

      <SaveButton onSave={onSave} dirty={dirty} errorCount={errorCount} />
    </div>
  );
}
