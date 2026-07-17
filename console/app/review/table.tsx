"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

type Item = {
  path: string;
  title?: string;
  kind: string;
  author_agent?: string;
  modified: string;
};

export default function ReviewTable({ items }: { items: Item[] }) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");

  const allSelected = selected.size === items.length && items.length > 0;

  function toggle(path: string) {
    const next = new Set(selected);
    next.has(path) ? next.delete(path) : next.add(path);
    setSelected(next);
  }

  async function act(action: "promote" | "archive", paths: string[]) {
    if (paths.length > 1) {
      const verb = action === "promote" ? "Promote" : "Archive";
      if (!confirm(`${verb} ${paths.length} notes?`)) return;
    }
    setBusy(true);
    let done = 0;
    for (const path of paths) {
      await fetch(`/api/brain/notes/${action}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ path }),
      });
      done += 1;
      if (paths.length > 1) setProgress(`${done}/${paths.length}…`);
    }
    setSelected(new Set());
    setProgress("");
    setBusy(false);
    router.refresh();
  }

  if (items.length === 0) return <p className="empty">Nothing unverified. The brain is clean.</p>;

  return (
    <>
      <div className="row" style={{ marginBottom: 12, minHeight: 34 }}>
        <label className="row" style={{ gap: 6, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={allSelected}
            onChange={() => setSelected(allSelected ? new Set() : new Set(items.map((i) => i.path)))}
          />
          <span className="dim">select all ({items.length})</span>
        </label>
        {selected.size > 0 && (
          <>
            <button className="btn btn-primary" disabled={busy} onClick={() => act("promote", [...selected])}>
              Promote {selected.size} selected
            </button>
            <button className="btn btn-danger" disabled={busy} onClick={() => act("archive", [...selected])}>
              Archive {selected.size} selected
            </button>
            {progress && <span className="dim">{progress}</span>}
          </>
        )}
      </div>
      <table>
        <thead>
          <tr>
            <th style={{ width: 30 }}></th>
            <th>note</th><th>kind</th><th>agent</th><th>modified</th>
            <th style={{ textAlign: "right" }}>actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.path}>
              <td>
                <input type="checkbox" checked={selected.has(i.path)} onChange={() => toggle(i.path)} />
              </td>
              <td>
                <Link href={`/vault?path=${encodeURIComponent(i.path)}`}>{i.title ?? i.path}</Link>
                <div className="dim mono" style={{ fontSize: 11.5 }}>{i.path}</div>
              </td>
              <td><span className={`badge ${i.kind}`}>{i.kind}</span></td>
              <td>{i.author_agent ?? "—"}</td>
              <td className="dim mono">{i.modified}</td>
              <td style={{ textAlign: "right" }}>
                <span className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                  <button className="btn btn-teal" disabled={busy} onClick={() => act("promote", [i.path])}>
                    Promote
                  </button>
                  <button className="btn btn-danger" disabled={busy} onClick={() => act("archive", [i.path])}>
                    Archive
                  </button>
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
