import Link from "next/link";
import Shell from "@/components/shell";
import { brain } from "@/lib/brain";
import { renderMarkdown } from "@/components/markdown";

function Crumbs({ path }: { path: string }) {
  const parts = path.split("/").filter(Boolean);
  return (
    <p className="dim mono" style={{ marginBottom: 12 }}>
      <Link href="/vault">vault</Link>
      {parts.map((p, i) => (
        <span key={i}>
          {" / "}
          <Link href={`/vault?path=${encodeURIComponent(parts.slice(0, i + 1).join("/"))}`}>{p}</Link>
        </span>
      ))}
    </p>
  );
}

export default async function Vault({
  searchParams,
}: {
  searchParams: Promise<{ path?: string; q?: string }>;
}) {
  const { path = "/", q } = await searchParams;
  const isNote = path.endsWith(".md");

  const parent = path.includes("/") ? path.split("/").slice(0, -1).join("/") : "";
  const backHref = isNote || path !== "/" ? `/vault${parent ? `?path=${encodeURIComponent(parent)}` : ""}` : null;

  let body: React.ReactNode;
  if (q) {
    const { results } = await brain(`/search?q=${encodeURIComponent(q)}`);
    body = (
      <>
        <p><Link href="/vault" className="dim">← back to vault</Link></p>
        <h2>Search: “{q}”</h2>
        {results.length === 0 ? (
          <p className="empty">No matches.</p>
        ) : (
          results.map((r: any) => (
            <div key={r.path} className="card" style={{ marginBottom: 8 }}>
              <Link href={`/vault?path=${encodeURIComponent(r.path)}`}><b>{r.title ?? r.path}</b></Link>
              <div className="dim mono" style={{ fontSize: 11.5 }}>{r.path}</div>
              <div style={{ marginTop: 4 }}>{r.excerpt}</div>
            </div>
          ))
        )}
      </>
    );
  } else if (isNote) {
    const note = await brain(`/note?path=${encodeURIComponent(path)}`);
    const status = note.content.match(/^---\n[\s\S]*?status:\s*(\w+)[\s\S]*?\n---/)?.[1];
    body = (
      <>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <span className="row">
            {backHref && <Link href={backHref} className="btn">← back</Link>}
            {status && <span className={`badge ${status === "unverified" ? "unverified" : "ok"}`}>{status}</span>}
          </span>
          <span className="dim mono" style={{ fontSize: 11.5 }}>modified {note.modified}</span>
        </div>
        <article className="note-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(note.content) }} />
      </>
    );
  } else {
    const { entries } = await brain(`/list?path=${encodeURIComponent(path)}`);
    body = (
      <>
        {backHref && (
          <p style={{ marginBottom: 10 }}>
            <Link href={backHref} className="btn">← back</Link>
          </p>
        )}
        <div className="folder-grid">
          {entries.map((e: any) => (
            <Link key={e.path} href={`/vault?path=${encodeURIComponent(e.path)}`} className="folder-item">
              {e.type === "dir" ? "▸ " : ""}
              {e.name}
            </Link>
          ))}
          {entries.length === 0 && <p className="empty">Empty folder.</p>}
        </div>
      </>
    );
  }

  return (
    <Shell active="/vault">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Vault</h1>
        <form method="get" action="/vault" className="row">
          <input name="q" placeholder="search the brain…" defaultValue={q ?? ""} style={{ width: 260 }} />
          <button className="btn">Search</button>
        </form>
      </div>
      <p className="dim">Read-only. All writes go through agents — that's the point.</p>
      <hr className="hairline" />
      {!q && <Crumbs path={path === "/" ? "" : path} />}
      {body}
    </Shell>
  );
}
