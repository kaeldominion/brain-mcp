import { NextRequest, NextResponse } from "next/server";
import { BRAIN_BASE } from "@/lib/brain";

export async function POST(request: NextRequest) {
  // logout path (HTML forms can't send DELETE)
  if (request.nextUrl.searchParams.get("_method") === "DELETE") {
    const res = NextResponse.redirect(new URL("/login", request.url), 303);
    res.cookies.delete("bt");
    return res;
  }

  const form = await request.formData();
  const token = String(form.get("token") ?? "").trim();
  if (!token) {
    return NextResponse.redirect(new URL("/login?error=missing", request.url), 303);
  }
  const check = await fetch(`${BRAIN_BASE}/api/stats`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  }).catch(() => null);

  if (!check || check.status === 401) {
    return NextResponse.redirect(new URL("/login?error=invalid", request.url), 303);
  }
  if (check.status === 403) {
    return NextResponse.redirect(new URL("/login?error=role", request.url), 303);
  }
  const res = NextResponse.redirect(new URL("/", request.url), 303);
  res.cookies.set("bt", token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.CONSOLE_INSECURE_COOKIE !== "1",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return res;
}
