import Link from "next/link";
import { brain } from "@/lib/brain";

const NAV = [
  ["/", "Dashboard"],
  ["/review", "Review queue"],
  ["/graph", "Graph"],
  ["/agents", "Agents"],
  ["/vault", "Vault"],
  ["/audit", "Audit"],
  ["/help", "How it works"],
] as const;

export default async function Shell({
  active,
  children,
}: {
  active: string;
  children: React.ReactNode;
}) {
  const identity = await brain("/identity").catch(() => ({ name: null }));
  return (
    <div className="shell">
      <aside className="side">
        <div className="wordmark" style={{ marginBottom: 4 }}>
          2nd <span className="grad-text">Brain</span>
        </div>
        <div className="dim" style={{ fontSize: 12.5, marginBottom: 20, lineHeight: 1.4 }}>
          {identity.name ?? "Company 2nd Brain"}
        </div>
        {NAV.map(([href, label]) => (
          <Link key={href} href={href} className={`nav-item ${active === href ? "active" : ""}`}>
            {label}
          </Link>
        ))}
        <form action="/api/session?_method=DELETE" method="post" style={{ marginTop: 12 }}>
          <button className="nav-item" style={{ width: "100%", textAlign: "left", background: "none", border: 0, cursor: "pointer", fontSize: 14 }}>
            Sign out
          </button>
        </form>
        <div className="side-footer">2nd Brain MCP · by Sentient Labs</div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
