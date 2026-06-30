"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, ConnectorCatalog } from "@/types";

export default function ConnectionsPage() {
  const [catalog, setCatalog] = useState<ConnectorCatalog>({});
  const [connections, setConnections] = useState<Connection[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [secret, setSecret] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    api.listConnections().then(setConnections).catch(() => setConnections([]));

  useEffect(() => {
    api
      .connectorCatalog()
      .then((c) => {
        setCatalog(c);
        const first = Object.keys(c)[0] ?? "";
        setType(first);
      })
      .catch(() => setCatalog({}));
    refresh();
  }, []);

  const fields = catalog[type]?.secret_fields ?? [];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createConnection({ name, connector_type: type, secret });
      setName("");
      setSecret({});
      await refresh();
    } catch {
      setError("Could not create the connection.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteConnection(id);
    await refresh();
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Connections</h1>
      <p className="mb-6 text-sm text-gray-500">
        Store a credential once, then use it from a workflow&rsquo;s Connector
        action. Secrets are encrypted and never shown again.
      </p>

      <form
        onSubmit={handleCreate}
        className="mb-8 space-y-3 rounded-xl border border-gray-200 bg-white p-5"
      >
        <h2 className="text-sm font-semibold text-gray-700">Add a connection</h2>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded border px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Type</label>
          <select
            value={type}
            onChange={(e) => {
              setType(e.target.value);
              setSecret({});
            }}
            className="w-full rounded border px-2 py-1 text-sm"
          >
            {Object.entries(catalog).map(([key, meta]) => (
              <option key={key} value={key}>
                {meta.label}
              </option>
            ))}
          </select>
        </div>
        {fields.map((field) => (
          <div key={field}>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              {field}
            </label>
            {field === "auth_type" ? (
              <select
                value={secret[field] ?? "bearer"}
                onChange={(e) => setSecret({ ...secret, [field]: e.target.value })}
                className="w-full rounded border px-2 py-1 text-sm"
              >
                <option value="bearer">bearer</option>
                <option value="api_key">api_key</option>
              </select>
            ) : (
              <input
                type="password"
                value={secret[field] ?? ""}
                onChange={(e) => setSecret({ ...secret, [field]: e.target.value })}
                className="w-full rounded border px-2 py-1 text-sm"
              />
            )}
          </div>
        ))}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy || !type}
          className="rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Add connection"}
        </button>
      </form>

      <h2 className="mb-2 text-sm font-semibold text-gray-700">
        Your connections
      </h2>
      {connections.length === 0 ? (
        <p className="text-sm text-gray-400">No connections yet.</p>
      ) : (
        <ul className="divide-y rounded-xl border border-gray-200 bg-white">
          {connections.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <span className="text-sm font-medium text-gray-900">{c.name}</span>
                <span className="ml-2 text-xs text-gray-400">
                  {catalog[c.connector_type]?.label ?? c.connector_type}
                </span>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(c.id)}
                aria-label={`Delete ${c.name}`}
                className="text-gray-400 hover:text-red-600"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
