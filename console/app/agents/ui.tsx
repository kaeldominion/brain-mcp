"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function TokenModal({ name, token, onClose }: { name: string; token: string; onClose: () => void }) {
  return (
    <div className="token-panel">
      <div className="dim" style={{ textAlign: "center" }}>onboarding token for <b style={{ color: "var(--text)" }}>{name}</b></div>
      <div className="token">{token}</div>
      <div className="dim" style={{ textAlign: "center", fontSize: 12 }}>
        Shown once. Paste it into the agent's config now.
      </div>
      <div className="row" style={{ justifyContent: "center", marginTop: 14 }}>
        <button className="btn" onClick={() => navigator.clipboard.writeText(token)}>Copy</button>
        <button className="btn btn-primary" onClick={onClose}>Done — clear it</button>
      </div>
    </div>
  );
}

export function AddAgent({ roles }: { roles: string[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [role, setRole] = useState(roles[0] ?? "contributor");
  const [reveal, setReveal] = useState<{ name: string; token: string } | null>(null);
  const [error, setError] = useState("");

  async function add() {
    setError("");
    const res = await fetch("/api/brain/clients", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, role }),
    });
    const data = await res.json();
    if (!res.ok) return setError(data.message ?? "failed");
    setReveal({ name, token: data.token });
    setName("");
    router.refresh();
  }

  if (reveal) return <TokenModal {...reveal} onClose={() => setReveal(null)} />;

  return (
    <div className="row" style={{ margin: "14px 0" }}>
      <input placeholder="agent name (e.g. finance)" value={name} onChange={(e) => setName(e.target.value)} />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        {roles.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>
      <button className="btn btn-primary" onClick={add} disabled={!name.trim()}>
        Add agent
      </button>
      {error && <span style={{ color: "var(--red)", fontSize: 13 }}>{error}</span>}
    </div>
  );
}

export function AgentRowActions({ name, source }: { name: string; source: string }) {
  const router = useRouter();
  const [reveal, setReveal] = useState<string | null>(null);

  if (source !== "dynamic")
    return <span className="dim" style={{ fontSize: 12 }}>env-managed</span>;

  async function rotate() {
    if (!confirm(`Rotate the token for '${name}'? The old token stops working immediately.`)) return;
    const res = await fetch(`/api/brain/clients/${encodeURIComponent(name)}/rotate`, { method: "POST" });
    const data = await res.json();
    if (res.ok) setReveal(data.token);
    router.refresh();
  }

  async function revoke() {
    if (!confirm(`Revoke '${name}'? Its token stops authenticating immediately.`)) return;
    await fetch(`/api/brain/clients/${encodeURIComponent(name)}`, { method: "DELETE" });
    router.refresh();
  }

  return (
    <>
      <span className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
        <button className="btn btn-teal" onClick={rotate}>Rotate</button>
        <button className="btn btn-danger" onClick={revoke}>Revoke</button>
      </span>
      {reveal && <TokenModal name={name} token={reveal} onClose={() => setReveal(null)} />}
    </>
  );
}
