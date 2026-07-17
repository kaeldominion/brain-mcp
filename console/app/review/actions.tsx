"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ReviewActions({ path }: { path: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function act(action: "promote" | "archive") {
    setBusy(true);
    await fetch(`/api/brain/notes/${action}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ path }),
    });
    router.refresh();
  }

  return (
    <span className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
      <button className="btn btn-teal" disabled={busy} onClick={() => act("promote")}>
        Promote
      </button>
      <button className="btn btn-danger" disabled={busy} onClick={() => act("archive")}>
        Archive
      </button>
    </span>
  );
}
