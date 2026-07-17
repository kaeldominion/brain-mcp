import { NextRequest, NextResponse } from "next/server";
import { BRAIN_BASE } from "@/lib/brain";

/** Relative redirects only: behind a reverse proxy the request URL can
 *  reflect the container's bind address (0.0.0.0:3000), so absolute
 *  redirects built from it point nowhere. Browsers resolve a relative
 *  Location against the public origin, which is always right. */
function redirect(path: string) {
  return new NextResponse(null, { status: 303, headers: { Location: path } });
}

export async function POST(request: NextRequest) {
  // logout path (HTML forms can't send DELETE)
  if (request.nextUrl.searchParams.get("_method") === "DELETE") {
    const res = redirect("/login");
    res.cookies.delete("bt");
    return res;
  }

  const form = await request.formData();
  const token = String(form.get("token") ?? "").trim();
  if (!token) return redirect("/login?error=missing");

  const check = await fetch(`${BRAIN_BASE}/api/stats`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  }).catch(() => null);

  if (!check || check.status === 401) return redirect("/login?error=invalid");
  if (check.status === 403) return redirect("/login?error=role");

  const res = redirect("/");
  res.cookies.set("bt", token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.CONSOLE_INSECURE_COOKIE !== "1",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return res;
}
