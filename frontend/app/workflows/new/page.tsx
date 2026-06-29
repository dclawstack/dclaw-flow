"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { WorkflowTemplate } from "@/types";

export default function NewWorkflowPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  // AI Flow Copilot (P0.1)
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Starter templates
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [usingTemplate, setUsingTemplate] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  const handleUseTemplate = async (tpl: WorkflowTemplate) => {
    setUsingTemplate(tpl.id);
    try {
      const workflow = await api.createWorkflow({
        name: tpl.name,
        description: tpl.description,
        nodes: tpl.nodes,
        edges: tpl.edges,
        trigger: tpl.trigger,
      });
      router.push(`/workflows/${workflow.id}`);
    } catch {
      setUsingTemplate(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const workflow = await api.createWorkflow({
      name,
      description,
      nodes: [],
      edges: [],
      trigger: { trigger_type: "manual", config: {} },
    });
    router.push(`/workflows/${workflow.id}`);
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setGenError(null);
    try {
      const result = await api.generateWorkflow(prompt, true);
      if (result.workflow) {
        router.push(`/workflows/${result.workflow.id}`);
        return;
      }
      setGenError(
        result.errors.length
          ? result.errors.join("; ")
          : "Could not generate a valid workflow.",
      );
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">New Workflow</h1>

      <div className="mb-8 rounded-xl border border-flow-200 bg-flow-50 p-5">
        <div className="mb-1 flex items-center gap-2">
          <span aria-hidden>✨</span>
          <h2 className="text-sm font-semibold text-flow-800">
            Build with AI Copilot
          </h2>
        </div>
        <p className="mb-3 text-sm text-flow-700">
          Describe what you want to automate and the copilot will build the
          workflow for you.
        </p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder="e.g. When a webhook arrives, call an API, then send a Slack message"
          className="w-full rounded-lg border border-flow-300 bg-white px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
        />
        {genError && (
          <p className="mt-2 text-sm text-red-600">{genError}</p>
        )}
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating || !prompt.trim()}
          className="mt-3 rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Workflow"}
        </button>
      </div>

      {templates.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            Start from a template
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                onClick={() => handleUseTemplate(tpl)}
                disabled={usingTemplate !== null}
                className="flex flex-col rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-flow-400 hover:shadow-sm disabled:opacity-50"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-gray-900">
                    {tpl.name}
                  </span>
                  <span className="rounded-full bg-flow-50 px-2 py-0.5 text-[11px] font-medium text-flow-700">
                    {tpl.category}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{tpl.description}</p>
                <span className="mt-2 text-[11px] text-gray-400">
                  {usingTemplate === tpl.id
                    ? "Creating…"
                    : `${tpl.nodes.length} nodes`}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4 flex items-center gap-3 text-xs uppercase tracking-wide text-gray-400">
        <span className="h-px flex-1 bg-gray-200" />
        or create manually
        <span className="h-px flex-1 bg-gray-200" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Name
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
        >
          {saving ? "Creating..." : "Create Workflow"}
        </button>
      </form>
    </div>
  );
}
