"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "./auth-context";

export function SiteNav() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <nav className="border-b bg-white px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <a href={user ? "/workflows" : "/"} className="text-lg font-bold text-flow-600">
            DClaw Flow
          </a>
          {user && (
            <div className="flex gap-4 text-sm text-gray-600">
              <a href="/workflows" className="hover:text-flow-600">
                Workflows
              </a>
              <a href="/executions" className="hover:text-flow-600">
                Executions
              </a>
              <a href="/connections" className="hover:text-flow-600">
                Connections
              </a>
            </div>
          )}
        </div>
        {user && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-500">{user.email}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-gray-200 px-3 py-1 text-gray-600 hover:border-flow-400 hover:text-flow-600"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
