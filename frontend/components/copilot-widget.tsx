"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { CopilotChatMessage, CopilotChatResponse } from "@/types";

const GREETING: CopilotChatMessage = {
  role: "assistant",
  content:
    "Hi! I'm the Flow Copilot. Describe an automation and I'll build it — " +
    "e.g. \"When a webhook fires, call an API and post to Slack.\"",
};

export function CopilotWidget() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<CopilotChatResponse["suggested_workflow"]>(null);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const history = messages.filter((m) => m !== GREETING);
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setDraft(null);
    setBusy(true);
    try {
      const res = await api.chatCopilot(text, history);
      setMessages([...next, { role: "assistant", content: res.reply }]);
      setDraft(res.suggested_workflow ?? null);
    } catch (err) {
      setMessages([
        ...next,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Something went wrong.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const createDraft = async () => {
    if (!draft) return;
    setBusy(true);
    try {
      const workflow = await api.createWorkflow(draft);
      setDraft(null);
      setOpen(false);
      router.push(`/workflows/${workflow.id}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Open Flow Copilot"
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-flow-600 text-2xl text-white shadow-lg transition hover:bg-flow-700"
      >
        {open ? "×" : "✨"}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[28rem] w-80 flex-col overflow-hidden rounded-xl border bg-white shadow-2xl">
          <div className="border-b bg-flow-600 px-4 py-3 text-sm font-semibold text-white">
            Flow Copilot
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={m.role === "user" ? "text-right" : "text-left"}
              >
                <span
                  className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-flow-600 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {m.content}
                </span>
              </div>
            ))}
            {draft && (
              <button
                type="button"
                onClick={createDraft}
                disabled={busy}
                className="w-full rounded-lg border border-flow-300 bg-flow-50 px-3 py-2 text-sm font-medium text-flow-700 hover:bg-flow-100 disabled:opacity-50"
              >
                Create “{draft.name}” ({draft.nodes.length} steps)
              </button>
            )}
            {busy && <div className="text-xs text-gray-400">Thinking…</div>}
          </div>

          <div className="flex gap-2 border-t p-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask or describe an automation…"
              className="flex-1 rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
            />
            <button
              type="button"
              onClick={send}
              disabled={busy || !input.trim()}
              className="rounded-lg bg-flow-600 px-3 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
