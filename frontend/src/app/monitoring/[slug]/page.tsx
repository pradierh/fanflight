import { notFound } from "next/navigation";
import { dashboards } from "../config";

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const dashboard = dashboards.find((d) => d.slug === slug);

  if (!dashboard) {
    notFound();
  }

  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL;

  if (!grafanaUrl) {
    throw new Error("NEXT_PUBLIC_GRAFANA_URL is not defined");
  }

  const iframeSrc = `${grafanaUrl}/d/${dashboard.uid}/${dashboard.grafanaSlug}?orgId=1&kiosk&theme=light&refresh=10s`;

  return (
  <iframe
    src={iframeSrc}
    title={dashboard.title}
    className="w-full h-screen border-0"
  />
);
}