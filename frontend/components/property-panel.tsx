"use client";

import { useEffect, useState } from "react";
import { Copy, Check } from "lucide-react";
import { api, webhookUrl } from "@/lib/api";
import type {
  Connection,
  FlowEdge,
  FlowNode,
  RetryPolicy,
  TriggerConfig,
} from "@/types";

interface PropertyPanelProps {
  node: FlowNode | null;
  edge: FlowEdge | null;
  onUpdate: (node: FlowNode) => void;
  onUpdateEdge: (
    id: string,
    patch: { condition?: string; kind?: FlowEdge["kind"] },
  ) => void;
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
  const isError = edge.kind === "error";
  return (
    <div className="w-64 border-l bg-gray-50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Connection
      </h3>
      <p className="mb-3 break-all text-xs text-gray-500">
        {edge.source} → {edge.target}
      </p>

      <label className="mb-1 block text-xs font-medium text-gray-600">
        Path type
      </label>
      <select
        value={isError ? "error" : "normal"}
        onChange={(e) =>
          onUpdateEdge(edge.id, { kind: e.target.value as FlowEdge["kind"] })
        }
        className="mb-3 w-full rounded border px-2 py-1 text-sm"
      >
        <option value="normal">Normal — on success</option>
        <option value="error">Error / fallback — on failure</option>
      </select>

      <label className="mb-1 block text-xs font-medium text-gray-600">
        Condition
      </label>
      <input
        value={condition}
        onChange={(e) => onUpdateEdge(edge.id, { condition: e.target.value })}
        placeholder="e.g. {{node-1.result}}"
        className="w-full rounded border px-2 py-1 text-sm font-mono"
      />
      <p className="mt-2 text-[10px] leading-relaxed text-gray-400">
        {isError ? (
          <>
            Taken when the source node <strong>fails</strong> (after retries).
            The failure is available as <code>{"{{src.error}}"}</code> /{" "}
            <code>{"{{src.failed}}"}</code>. Leave the condition empty to always
            catch.
          </>
        ) : (
          <>
            Empty = always taken. Otherwise taken only when the condition
            resolves truthy. For if/else from a conditional, use{" "}
            <code>{"{{id.result}}"}</code> and <code>{"{{id.else}}"}</code>.
          </>
        )}
      </p>
      <SaveButton onSave={onSave} dirty={dirty} errorCount={errorCount} />
    </div>
  );
}

function RetryEditor({
  node,
  onUpdate,
}: Pick<PropertyPanelProps, "node" | "onUpdate">) {
  if (!node) return null;
  const retry = node.retry ?? null;
  const set = (patch: Partial<RetryPolicy>) => {
    const base: RetryPolicy = retry ?? {
      max_attempts: 1,
      backoff_strategy: "none",
      backoff_seconds: 1,
    };
    const next = { ...base, ...patch };
    onUpdate({ ...node, retry: next.max_attempts > 1 ? next : null });
  };
  return (
    <div className="mb-3 border-t pt-3">
      <label className="mb-1 block text-xs font-medium text-gray-600">
        Retries (max attempts)
      </label>
      <input
        type="number"
        min={1}
        max={10}
        value={retry?.max_attempts ?? 1}
        onChange={(e) =>
          set({ max_attempts: Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 1)) })
        }
        className="w-full rounded border px-2 py-1 text-sm"
      />
      {retry && retry.max_attempts > 1 && (
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div>
            <label className="mb-1 block text-[10px] text-gray-500">Backoff</label>
            <select
              value={retry.backoff_strategy}
              onChange={(e) =>
                set({ backoff_strategy: e.target.value as RetryPolicy["backoff_strategy"] })
              }
              className="w-full rounded border px-1 py-1 text-xs"
            >
              <option value="none">none</option>
              <option value="fixed">fixed</option>
              <option value="exponential">exponential</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[10px] text-gray-500">Seconds</label>
            <input
              type="number"
              min={0}
              step="0.5"
              value={retry.backoff_seconds}
              onChange={(e) =>
                set({ backoff_seconds: parseFloat(e.target.value) || 0 })
              }
              className="w-full rounded border px-1 py-1 text-xs"
            />
          </div>
        </div>
      )}
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

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border px-2 py-1 text-sm"
      />
    </div>
  );
}

function ActionEditor({
  node,
  updateConfig,
}: {
  node: FlowNode;
  updateConfig: (key: string, value: unknown) => void;
}) {
  const actionType = (node.config.action_type as string) || "http";
  const [connections, setConnections] = useState<Connection[]>([]);

  useEffect(() => {
    if (actionType === "connector") {
      api.listConnections().then(setConnections).catch(() => setConnections([]));
    }
  }, [actionType]);

  const selected = connections.find((c) => c.id === node.config.connection_id);

  return (
    <>
      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Action type
        </label>
        <select
          value={actionType}
          onChange={(e) => updateConfig("action_type", e.target.value)}
          className="w-full rounded border px-2 py-1 text-sm"
        >
          <option value="http">HTTP request</option>
          <option value="connector">Connector</option>
        </select>
      </div>

      {actionType === "http" && (
        <>
          <Field
            label="URL"
            value={(node.config.url as string) || ""}
            onChange={(v) => updateConfig("url", v)}
          />
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

      {actionType === "connector" && (
        <>
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Connection
            </label>
            <select
              value={(node.config.connection_id as string) || ""}
              onChange={(e) => updateConfig("connection_id", e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
            >
              <option value="">Select…</option>
              {connections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.connector_type})
                </option>
              ))}
            </select>
            {connections.length === 0 && (
              <p className="mt-1 text-xs text-gray-400">
                No connections yet — add one on the Connections page.
              </p>
            )}
          </div>
          {selected?.connector_type === "slack_webhook" && (
            <Field
              label="Message text"
              value={(node.config.text as string) || ""}
              onChange={(v) => updateConfig("text", v)}
            />
          )}
          {selected?.connector_type === "authenticated_http" && (
            <>
              <Field
                label="URL"
                value={(node.config.url as string) || ""}
                onChange={(v) => updateConfig("url", v)}
              />
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
        </>
      )}
    </>
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
        <ActionEditor node={node} updateConfig={updateConfig} />
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

      {node.type !== "trigger" && (
        <RetryEditor node={node} onUpdate={onUpdate} />
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
