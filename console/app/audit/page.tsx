import Shell from "@/components/shell";
import { brain } from "@/lib/brain";

export default async function Audit({
  searchParams,
}: {
  searchParams: Promise<{ client?: string; tool?: string; ok?: string }>;
}) {
  const filters = await searchParams;
  const qs = new URLSearchParams({ limit: "200" });
  for (const [k, v] of Object.entries(filters)) if (v) qs.set(k, v);
  const { events } = await brain(`/audit?${qs}`);

  return (
    <Shell active="/audit">
      <h1>Audit trail</h1>
      <p className="dim">Every write, allowed or denied. Append-only; agents can't touch it.</p>
      <hr className="hairline" />
      <form method="get" action="/audit" className="row" style={{ marginBottom: 14 }}>
        <input name="client" placeholder="agent" defaultValue={filters.client ?? ""} style={{ width: 140 }} />
        <input name="tool" placeholder="tool" defaultValue={filters.tool ?? ""} style={{ width: 180 }} />
        <select name="ok" defaultValue={filters.ok ?? ""}>
          <option value="">allowed + denied</option>
          <option value="true">allowed only</option>
          <option value="false">denied only</option>
        </select>
        <button className="btn">Filter</button>
      </form>
      {events.length === 0 ? (
        <p className="empty">No matching events.</p>
      ) : (
        <table>
          <thead>
            <tr><th>time</th><th>agent</th><th>role</th><th>tool</th><th>path</th><th></th></tr>
          </thead>
          <tbody>
            {events.map((e: any, i: number) => (
              <tr key={i} style={e.ok ? undefined : { background: "rgba(248,113,113,.06)" }}>
                <td className="dim mono">{e.ts}</td>
                <td>{e.client}{e.owner ? <div className="dim" style={{ fontSize: 11 }}>{e.owner}</div> : null}</td>
                <td className="dim">{e.role}</td>
                <td className="mono">{e.tool}</td>
                <td className="mono">{e.path}{e.error ? <div className="dim" style={{ fontSize: 11.5 }}>{e.error}</div> : null}</td>
                <td>{e.ok ? <span className="badge ok">ok</span> : <span className="badge denied">denied</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
