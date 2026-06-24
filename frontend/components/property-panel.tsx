"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { api, webhookUrl } from "@/lib/api";
import type { FlowEdge, FlowNode, TriggerConfig } from "@/types";

interface PropertyPanelProps {
  node: FlowNode | null;
  edge: FlowEdge | null;
  onUpdate: (node: FlowNode) => void;
  onUpdateEdge: (id: string, condition: string) => void;
  onDelete: (id: string) => void;
  onSave: () => void;
  dirty: boolean;
  errorCount: number;
  trigger: TriggerConfig;
  onTriggerChange: (trigger: TriggerConfig) => void;
}

function EdgeEditor({
  edge,
  onUpdateEdge,
  onSave,
  dirty,
  errorCount,
}: Pick<
  PropertyPanelProps,
  "edge" | "onUpdateEdge" | "onSave" | "dirty" | "errorCount"
>) {
  if (!edge) return null;
  const condition = edge.condition || "";
  return (
    <div className="w-64 border-l bg-gray-50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Connection
      </h3>
      <p className="mb-3 break-all text-xs text-gray-500">
        {edge.source} → {edge.target}
      </p>
      <label className="mb-1 block text-xs font-medium text-gray-600">
        Condition
      </label>
      <input
        value={condition}
        onChange={(e) => onUpdateEdge(edge.id, e.target.value)}
        placeholder="e.g. {{node-1.result}}"
        className="w-full rounded border px-2 py-1 text-sm font-mono"
      />
      <p className="mt-2 text-[10px] leading-relaxed text-gray-400">
        Empty = always taken. Otherwise this edge is taken only when the
        condition resolves truthy. For an if/else from a conditional node, use{" "}
        <code>{"{{id.result}}"}</code> on one edge and <code>{"{{id.else}}"}</code>{" "}
        on the other.
      </p>
      <SaveButton onSave={onSave} dirty={dirty} errorCount={errorCount} />
    </div>
  );
}

function TriggerEditor({
  trigger,
  onTriggerChange,
}: Pick<PropertyPanelProps, "trigger" | "onTriggerChange">) {
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null);
  const [copied, setCopied] = useState(false);
  const config = trigger.config || {};
  const path = (config.path as string) || "";

  const setType = (trigger_type: TriggerConfig["trigger_type"]) => {
    let next = config;
    if (trigger_type === "webhook" && !next.path) {
      next = { ...next, path: `webhook-${Math.random().toString(36).slice(2, 8)}` };
    }
    onTriggerChange({ trigger_type, config: next });
  };
  const setConfig = (key: string, value: unknown) =>
    onTriggerChange({ ...trigger, config: { ...config, [key]: value } });

  const url = webhookUrl(path);

  return (
    <div className="mb-3 space-y-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Trigger Type
        </label>
        <select
          value={trigger.trigger_type}
          onChange={(e) =>
            setType(e.target.value as TriggerConfig["trigger_type"])
          }
          className="w-full rounded border px-2 py-1 text-sm"
        >
          <option value="manual">Manual</option>
          <option value="webhook">Webhook</option>
          <option value="schedule">Schedule</option>
        </select>
      </div>

      {trigger.trigger_type === "webhook" && (
        <>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Webhook Path
            </label>
            <input
              value={path}
              onChange={(e) => setConfig("path", e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm font-mono"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Signing Secret (optional)
            </label>
            <input
              value={(config.secret as string) || ""}
              onChange={(e) => setConfig("secret", e.target.value)}
              placeholder="HMAC-SHA256 secret"
              className="w-full rounded border px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Webhook URL
            </label>
            <div className="flex items-center gap-1">
              <code className="flex-1 truncate rounded bg-gray-100 px-2 py-1 text-[11px] text-gray-700">
                {url}
              </code>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(url);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
                aria-label="Copy webhook URL"
                className="rounded border bg-white p-1 hover:bg-gray-50"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-flow-600" />
                ) : (
                  <Copy className="h-3.5 w-3.5 text-gray-500" />
                )}
              </button>
            </div>
            <p className="mt-1 text-[10px] text-gray-400">
              Active workflows only. POST raw JSON here.
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              api
                .getWebhookSchema(path)
                .then((r) => setSchema(r.schema))
                .catch(() => setSchema(null))
            }
            className="w-full rounded border bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            View inferred schema
          </button>
          {schema && (
            <pre className="max-h-40 overflow-auto rounded bg-gray-900 p-2 text-[10px] text-gray-100">
              {JSON.stringify(schema, null, 2)}
            </pre>
          )}
        </>
      )}
    </div>
  );
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
  edge,
  onUpdate,
  onUpdateEdge,
  onDelete,
  onSave,
  dirty,
  errorCount,
  trigger,
  onTriggerChange,
}: PropertyPanelProps) {
  if (edge) {
    return (
      <EdgeEditor
        edge={edge}
        onUpdateEdge={onUpdateEdge}
        onSave={onSave}
        dirty={dirty}
        errorCount={errorCount}
      />
    );
  }
  if (!node) {
    return (
      <div className="w-64 border-l bg-gray-50 p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Properties
        </h3>
        <p className="text-sm text-gray-400">
          Select a node, or a connection to set its condition
        </p>
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
        <TriggerEditor trigger={trigger} onTriggerChange={onTriggerChange} />
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
