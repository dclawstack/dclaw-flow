"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Workflow } from "@/types";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listWorkflows().then((data) => {
      setWorkflows(data.items);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="text-gray-500">Loading workflows...</div>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
        <Link
          href="/workflows/new"
          className="rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700"
        >
          New Workflow
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((wf) => (
          <Link
            key={wf.id}
            href={`/workflows/${wf.id}`}
            className="rounded-xl border bg-white p-5 shadow-sm transition hover:shadow-md"
          >
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">{wf.name}</h3>
              <StatusBadge status={wf.status} />
            </div>
            <p className="mb-3 text-sm text-gray-500">
              {wf.description || "No description"}
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span>v{wf.version}</span>
              <span>{wf.nodes.length} nodes</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    active: "bg-flow-100 text-flow-700",
    paused: "bg-yellow-100 text-yellow-700",
    archived: "bg-red-100 text-red-700",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.draft}`}>
      {status}
    </span>
  );
}
