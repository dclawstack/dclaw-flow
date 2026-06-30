"use client";

import { CopilotWidget } from "@/components/copilot-widget";
import { useAuth } from "./auth-context";
import { AuthGate } from "./auth-gate";
import { SiteNav } from "./site-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  return (
    <>
      <SiteNav />
      <main className="p-6">
        <AuthGate>{children}</AuthGate>
      </main>
      {user && <CopilotWidget />}
    </>
  );
}
