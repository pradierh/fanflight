export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main
      style={{
        width: "100%",
        height: "100%",
        margin: 0,
        padding: 0,
        overflow: "hidden",
      }}
    >
      {children}
    </main>
  );
}