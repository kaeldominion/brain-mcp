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
  const [owner, setOwner] = useState("");
  const [role, setRole] = useState(roles[0] ?? "");
  const [reveal, setReveal] = useState<{ name: string; token: string } | null>(null);
  const [error, setError] = useState("");

  async function add() {
    setError("");
    const res = await fetch("/api/brain/clients", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, role, owner }),
    });
    const data = await res.json();
    if (!res.ok) return setError(data.message ?? "failed");
    setReveal({ name, token: data.token });
    setName("");
    setOwner("");
    router.refresh();
  }

  if (reveal) return <TokenModal {...reveal} onClose={() => setReveal(null)} />;

  return (
    <div style={{ margin: "14px 0" }}>
      <div className="row" style={{ alignItems: "flex-end" }}>
        <label style={{ display: "block" }}>
          <span className="dim" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>agent name</span>
          <input placeholder="e.g. tia-gm" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label style={{ display: "block" }}>
          <span className="dim" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>assigned to (person)</span>
          <input placeholder="e.g. Tia, General Manager" value={owner} onChange={(e) => setOwner(e.target.value)} />
        </label>
        <label style={{ display: "block" }}>
          <span className="dim" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>role</span>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {roles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary" onClick={add} disabled={!name.trim() || !role}>
          Add agent
        </button>
      </div>
      {error && <span style={{ color: "var(--red)", fontSize: 13 }}>{error}</span>}
    </div>
  );
}

export function AgentRowActions({ name, source }: { name: string; source: string }) {
  const router = useRouter();
  const [reveal, setReveal] = useState<string | null>(null);

  if (source !== "dynamic")
    return <span className="dim" style={{ fontSize: 12 }}>server-managed (./brain)</span>;

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
