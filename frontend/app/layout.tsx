import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DClaw Flow",
  description: "Connect anything, automate everything",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <nav className="border-b bg-white px-6 py-3">
          <div className="flex items-center gap-6">
            <a href="/" className="text-lg font-bold text-flow-600">
              DClaw Flow
            </a>
            <div className="flex gap-4 text-sm text-gray-600">
              <a href="/workflows" className="hover:text-flow-600">
                Workflows
              </a>
              <a href="/executions" className="hover:text-flow-600">
                Executions
              </a>
            </div>
          </div>
        </nav>
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
