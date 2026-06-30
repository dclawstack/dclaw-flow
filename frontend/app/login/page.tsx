"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/workflows");
    } catch {
      setError("Invalid email or password.");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto mt-10 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Log in</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
        >
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-500">
        No account?{" "}
        <a href="/signup" className="font-medium text-flow-600 hover:underline">
          Sign up
        </a>
      </p>
    </div>
  );
}
