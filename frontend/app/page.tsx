import Link from "next/link";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-8 rounded-xl bg-gradient-to-r from-flow-500 to-flow-700 p-8 text-white">
        <h1 className="mb-2 text-3xl font-bold">DClaw Flow</h1>
        <p className="text-lg opacity-90">Connect anything, automate everything</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Link
          href="/workflows"
          className="rounded-xl border bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h2 className="mb-2 text-xl font-semibold text-gray-900">
            Workflows
          </h2>
          <p className="text-gray-600">
            Build and manage visual automation workflows.
          </p>
        </Link>

        <Link
          href="/executions"
          className="rounded-xl border bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h2 className="mb-2 text-xl font-semibold text-gray-900">
            Executions
          </h2>
          <p className="text-gray-600">
            View run history and monitor execution status.
          </p>
        </Link>
      </div>
    </div>
  );
}
