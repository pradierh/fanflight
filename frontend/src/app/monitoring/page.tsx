import Link from "next/link";
import { dashboards } from "./config";

export default function MonitoringPage() {
  return (
    <main className="mx-auto max-w-5xl p-8 text-white">
      <h1 className="mb-8 text-3xl font-bold text-white">Monitoring</h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {dashboards.map((dashboard) => (
          <Link
            key={dashboard.slug}
            href={`/monitoring/${dashboard.slug}`}
            className="rounded-xl border p-6 shadow transition hover:shadow-lg"
          >
            <h2 className="text-xl font-semibold text-white">{dashboard.title}</h2>
            <p className="mt-2 text-gray-300">
              Ouvrir le dashboard Grafana
            </p>
          </Link>
        ))}
      </div>
    </main>
  );
}