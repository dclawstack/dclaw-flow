"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./auth-context";

const PUBLIC_PATHS = ["/login", "/signup"];

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (loading) return;
    if (!user && !isPublic) router.replace("/login");
    if (user && isPublic) router.replace("/workflows");
  }, [loading, user, isPublic, router]);

  if (loading) {
    return <div className="p-8 text-sm text-gray-400">Loading…</div>;
  }
  // While the redirect effect runs, don't flash protected content.
  if (!user && !isPublic) return null;
  if (user && isPublic) return null;
  return <>{children}</>;
}
