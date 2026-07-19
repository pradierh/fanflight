import Link from "next/link";
import { dashboards } from "./config";

export default function MonitoringLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div style={{ padding: "2rem", maxWidth: "900px", margin: "0 auto" }}>
      <h1>Monitoring</h1>

      <ul style={{ listStyle: "none", padding: 0 }}>
        {dashboards.map((d) => (
          <li key={d.slug} style={{ marginBottom: "1rem" }}>
            <Link href={`/monitoring/${d.slug}`}>
              {d.title}
            </Link>
          </li>
        ))}
      </ul>

      {children}
    </div>
  );
}