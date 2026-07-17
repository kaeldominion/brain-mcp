import { NextRequest, NextResponse } from "next/server";
import { BRAIN_BASE } from "@/lib/brain";

/** Authenticated pass-through for client components. brain-mcp enforces
 *  authorization on every route, so this only attaches the session token. */
async function forward(request: NextRequest, params: Promise<{ path: string[] }>) {
  const token = request.cookies.get("bt")?.value;
  if (!token) return NextResponse.json({ error: "UNAUTHORIZED" }, { status: 401 });
  const { path } = await params;
  const url = `${BRAIN_BASE}/api/${path.join("/")}${request.nextUrl.search}`;
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
  const res = await fetch(url, {
    method: request.method,
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body,
    cache: "no-store",
  });
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, ctx.params);
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, ctx.params);
}
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, ctx.params);
}
