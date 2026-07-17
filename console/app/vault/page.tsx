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

  let body: React.ReactNode;
  if (q) {
    const { results } = await brain(`/search?q=${encodeURIComponent(q)}`);
    body = (
      <>
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
    body = (
      <article className="note-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(note.content) }} />
    );
  } else {
    const { entries } = await brain(`/list?path=${encodeURIComponent(path)}`);
    body = (
      <div className="folder-grid">
        {entries.map((e: any) => (
          <Link key={e.path} href={`/vault?path=${encodeURIComponent(e.path)}`} className="folder-item">
            {e.type === "dir" ? "▸ " : ""}
            {e.name}
          </Link>
        ))}
        {entries.length === 0 && <p className="empty">Empty folder.</p>}
      </div>
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
