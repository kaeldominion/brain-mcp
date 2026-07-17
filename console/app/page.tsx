import Link from "next/link";
import Shell from "@/components/shell";
import { brain } from "@/lib/brain";

export default async function Dashboard() {
  const [stats, health, clients, audit] = await Promise.all([
    brain("/stats"),
    brain("/health"),
    brain("/clients"),
    brain("/audit?limit=8"),
  ]);
  const folders = Object.entries(stats.by_folder ?? {}) as [string, number][];
  const max = Math.max(1, ...folders.map(([, n]) => n));
  return (
    <Shell active="/">
      <h1>Dashboard</h1>
      <p className="dim">
        brain-mcp v{health.version} · vault {health.vault_mounted ? "mounted" : "MISSING"}
      </p>
      <hr className="hairline" />
      <div className="cards">
        <div className="card"><div className="num">{stats.notes_total}</div><div className="label">notes</div></div>
        <Link href="/review" className="card"><div className="num" style={{ color: stats.unverified ? "var(--amber)" : "var(--teal)" }}>{stats.unverified}</div><div className="label">unverified</div></Link>
        <Link href="/review" className="card"><div className="num">{stats.inbox_items}</div><div className="label">inbox items</div></Link>
        <Link href="/agents" className="card"><div className="num">{clients.clients.length}</div><div className="label">agents</div></Link>
      </div>

      <h2>Vault</h2>
      {folders.map(([name, n]) => (
        <div key={name} className="row" style={{ marginBottom: 6 }}>
          <Link href={`/vault?path=${encodeURIComponent(name)}`} style={{ width: 180 }} className="dim">{name}</Link>
          <div className="bar-track" style={{ flex: 1 }}>
            <div className="bar" style={{ width: `${(n / max) * 100}%`, opacity: 0.75 }} />
          </div>
          <span className="dim" style={{ width: 40, textAlign: "right" }}>{n}</span>
        </div>
      ))}

      <h2>Recent activity</h2>
      {audit.events.length === 0 ? (
        <p className="empty">No writes yet.</p>
      ) : (
        <table>
          <thead><tr><th>time</th><th>agent</th><th>tool</th><th>path</th><th></th></tr></thead>
          <tbody>
            {audit.events.map((e: any, i: number) => (
              <tr key={i}>
                <td className="dim mono">{e.ts}</td>
                <td>{e.client}</td>
                <td className="mono">{e.tool}</td>
                <td className="mono">{e.path}</td>
                <td>{e.ok ? <span className="badge ok">ok</span> : <span className="badge denied">denied</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
