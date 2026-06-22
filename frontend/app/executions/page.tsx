"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Execution } from "@/types";

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .listExecutions({
        status: status || undefined,
        startedAfter: from ? `${from}T00:00:00Z` : undefined,
        startedBefore: to ? `${to}T23:59:59Z` : undefined,
      })
      .then((data) => {
        setExecutions(data.items);
        setLoading(false);
      });
  }, [status, from, to]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Execution History</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            aria-label="From date"
            className="rounded-lg border px-3 py-2"
          />
          <span className="text-gray-400">→</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            aria-label="To date"
            className="rounded-lg border px-3 py-2"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border px-3 py-2"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading executions...</div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Workflow</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {executions.map((ex) => (
                <tr key={ex.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link
                      href={`/executions/${ex.id}`}
                      className="text-flow-600 hover:underline"
                    >
                      {ex.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {ex.workflow_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={ex.status} />
                  </td>
                  <td className="px-4 py-3 capitalize text-gray-600">
                    {ex.trigger_source}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(ex.started_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {ex.completed_at
                      ? new Date(ex.completed_at).toLocaleString()
                      : "—"}
                  </td>
                </tr>
              ))}
              {executions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    No executions match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
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
