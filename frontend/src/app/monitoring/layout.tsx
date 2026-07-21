import Link from "next/link";
import { dashboards } from "./config";

export default function MonitoringLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
      <nav style={{ width: "220px", padding: "1rem", flexShrink: 0, borderRight: "1px solid #333" }}>
        <h1 style={{ fontSize: "1.2rem" }}>Monitoring</h1>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {dashboards.map((d) => (
            <li key={d.slug} style={{ marginBottom: "1rem" }}>
              <Link href={`/monitoring/${d.slug}`}>{d.title}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <div style={{ flex: 1, overflow: "hidden" }}>{children}</div>
    </div>
  );
}