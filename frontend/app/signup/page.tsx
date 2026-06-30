"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-context";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signup(email, password);
      router.replace("/workflows");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(
        msg.includes("already registered")
          ? "That email is already registered."
          : "Could not create the account.",
      );
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto mt-10 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Create your account</h1>
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
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded-lg border px-3 py-2 text-sm focus:border-flow-500 focus:outline-none focus:ring-1 focus:ring-flow-500"
          />
          <p className="mt-1 text-xs text-gray-400">At least 8 characters.</p>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-flow-600 px-4 py-2 text-sm font-medium text-white hover:bg-flow-700 disabled:opacity-50"
        >
          {busy ? "Creating…" : "Sign up"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-500">
        Already have an account?{" "}
        <a href="/login" className="font-medium text-flow-600 hover:underline">
          Log in
        </a>
      </p>
    </div>
  );
}
