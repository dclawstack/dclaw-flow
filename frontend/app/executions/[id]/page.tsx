"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, Lightbulb } from "lucide-react";
import { api } from "@/lib/api";
import type { Execution, NodeExecution } from "@/types";

export default function ExecutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [flags, setFlags] = useState<string[]>([]);
  const [rootCause, setRootCause] = useState<{
    explanation: string;
    source: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getExecution(id)
      .then(async (ex) => {
        setExecution(ex);
        const [anomalies, rc] = await Promise.all([
          api.getExecutionAnomalies(id).catch(() => ({ flags: [] })),
          ex.status === "failed"
            ? api.getExecutionRootCause(id).catch(() => null)
            : Promise.resolve(null),
        ]);
        setFlags(anomalies.flags);
        setRootCause(rc);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-gray-500">Loading execution...</div>;
  if (!execution)
    return <div className="text-red-500">Execution not found</div>;

  const duration = execution.completed_at
    ? (
        (new Date(execution.completed_at).getTime() -
          new Date(execution.started_at).getTime()) /
        1000
      ).toFixed(1) + "s"
    : "—";

  return (
    <div className="mx-auto max-w-4xl">
      <Link
        href="/executions"
        className="text-sm text-flow-600 hover:underline"
      >
        ← Execution History
      </Link>

      <div className="mt-3 mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-mono text-xl font-bold text-gray-900">
            {execution.id.slice(0, 8)}
          </h1>
          <p className="text-sm text-gray-500">
            Workflow {execution.workflow_id.slice(0, 8)} · {execution.trigger_source}
          </p>
        </div>
        <StatusBadge status={execution.status} />
      </div>

      <div className="mb-6 grid grid-cols-3 gap-4 rounded-xl border bg-white p-4 text-sm shadow-sm">
        <Meta label="Started" value={new Date(execution.started_at).toLocaleString()} />
        <Meta
          label="Completed"
          value={
            execution.completed_at
              ? new Date(execution.completed_at).toLocaleString()
              : "—"
          }
        />
        <Meta label="Duration" value={duration} />
      </div>

      {flags.length > 0 && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="mb-1 flex items-center gap-2 font-medium text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            Anomalies detected
          </div>
          <ul className="list-inside list-disc text-sm text-amber-900">
            {flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      {rootCause && (
        <div className="mb-6 rounded-xl border border-flow-200 bg-flow-50 p-4">
          <div className="mb-1 flex items-center gap-2 font-medium text-flow-800">
            <Lightbulb className="h-4 w-4" />
            Root cause
            <span className="rounded-full bg-flow-100 px-2 text-[10px] font-normal text-flow-700">
              via {rootCause.source}
            </span>
          </div>
          <p className="text-sm text-flow-900">{rootCause.explanation}</p>
        </div>
      )}

      {execution.error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm">
          <div className="mb-1 font-medium text-red-800">Error</div>
          <pre className="overflow-auto text-xs text-red-900">
            {JSON.stringify(execution.error, null, 2)}
          </pre>
        </div>
      )}

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
        Step Logs ({execution.node_executions.length})
      </h2>
      <div className="space-y-3">
        {execution.node_executions.map((node) => (
          <StepLog key={node.id} node={node} />
        ))}
        {execution.node_executions.length === 0 && (
          <p className="text-sm text-gray-400">No steps recorded.</p>
        )}
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-gray-800">{value}</div>
    </div>
  );
}

function StepLog({ node }: { node: NodeExecution }) {
  return (
    <div className="rounded-lg border bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-sm font-medium text-gray-800">
          {node.node_id}
        </span>
        <StatusBadge status={node.status} />
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <JsonBlock label="Input" value={node.input} />
        <JsonBlock label="Output" value={node.output} />
        {node.error && <JsonBlock label="Error" value={node.error} />}
      </div>
    </div>
  );
}

function JsonBlock({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown> | null | undefined;
}) {
  if (!value || Object.keys(value).length === 0) return null;
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-wide text-gray-400">
        {label}
      </div>
      <pre className="max-h-40 overflow-auto rounded bg-gray-900 p-2 text-[10px] text-gray-100">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-flow-100 text-flow-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-yellow-100 text-yellow-700",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.pending}`}
    >
      {status}
    </span>
  );
}
