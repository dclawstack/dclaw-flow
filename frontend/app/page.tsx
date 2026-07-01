"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

export default function HomePage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => setStats(null));
  }, []);

  const maxDay = Math.max(1, ...(stats?.per_day.map((d) => d.count) ?? [0]));
  const successPct =
    stats?.success_rate == null ? "—" : `${Math.round(stats.success_rate * 100)}%`;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-8 rounded-xl bg-gradient-to-r from-flow-500 to-flow-700 p-8 text-white">
        <h1 className="mb-2 text-3xl font-bold">DClaw Flow</h1>
        <p className="text-lg opacity-90">Connect anything, automate everything</p>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Workflows" value={stats?.totals.workflows ?? "—"} />
        <StatCard label="Executions" value={stats?.totals.executions ?? "—"} />
        <StatCard label="Connections" value={stats?.totals.connections ?? "—"} />
        <StatCard label="Success rate" value={successPct} />
      </div>

      {stats && stats.totals.executions > 0 && (
        <div className="mb-8 rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            Executions — last 14 days
          </h2>
          <div className="flex h-24 items-end gap-1">
            {stats.per_day.map((d) => (
              <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-flow-500"
                  style={{ height: `${(d.count / maxDay) * 100}%` }}
                  title={`${d.date}: ${d.count}`}
                />
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-4 text-xs text-gray-400">
            {Object.entries(stats.by_status).map(([s, n]) => (
              <span key={s}>
                {s}: {n}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <Link
          href="/workflows"
          className="rounded-xl border bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Workflows</h2>
          <p className="text-sm text-gray-600">Build and manage automations.</p>
        </Link>
        <Link
          href="/executions"
          className="rounded-xl border bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Executions</h2>
          <p className="text-sm text-gray-600">Run history and status.</p>
        </Link>
        <Link
          href="/connections"
          className="rounded-xl border bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Connections</h2>
          <p className="text-sm text-gray-600">Credentials for connectors.</p>
        </Link>
      </div>
    </div>
  );
}
