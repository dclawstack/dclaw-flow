"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { FlowCanvas } from "@/components/flow-canvas";
import type { Workflow } from "@/types";

export default function WorkflowEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getWorkflow(id).then((wf) => {
      setWorkflow(wf);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return <div className="text-gray-500">Loading editor...</div>;
  }

  if (!workflow) {
    return <div className="text-red-500">Workflow not found</div>;
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{workflow.name}</h1>
          <p className="text-sm text-gray-500">
            {workflow.description || "No description"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={async () => {
              const ex = await api.executeWorkflow(workflow.id);
              alert(`Execution started: ${ex.id}`);
            }}
            className="rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700"
          >
            Run
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden rounded-xl border bg-white shadow-sm">
        <FlowCanvas workflow={workflow} onChange={setWorkflow} />
      </div>
    </div>
  );
}
