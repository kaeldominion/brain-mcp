import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const BRAIN_BASE = process.env.BRAIN_API_URL ?? "http://brain-mcp:8000";

/** Server-side fetch against the brain-mcp admin API using the session token. */
export async function brain(path: string, init?: RequestInit): Promise<any> {
  const token = (await cookies()).get("bt")?.value;
  if (!token) redirect("/login");
  const res = await fetch(`${BRAIN_BASE}/api${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    cache: "no-store",
  });
  if (res.status === 401 || res.status === 403) redirect("/login");
  return res.json();
}
